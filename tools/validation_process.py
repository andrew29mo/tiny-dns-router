"""Bounded subprocesses, including descendants which open another session."""
from contextlib import contextmanager
import os
from pathlib import Path
import signal
import subprocess
import time

import psutil


@contextmanager
def cancellation_signals():
    def cancel(signum, frame):
        raise KeyboardInterrupt('Validation cancelled by signal')
    previous = {sig: signal.signal(sig, cancel) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


@contextmanager
def cleanup_signals():
    previous = {sig: signal.signal(sig, signal.SIG_IGN) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def stop_tree(child):
    # Capture descendants before the parent exits and they are reparented. psutil
    # retains process identity and checks PID reuse before sending a signal.
    try:
        parent = psutil.Process(child.pid)
        processes = parent.children(recursive=True) + [parent]
    except psutil.NoSuchProcess:
        processes = []
    except (psutil.AccessDenied, PermissionError):
        # Never leave even the original group alive when inspection is denied.
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait(timeout=3)
        raise RuntimeError('Cannot verify descendant cleanup') from None
    for process in processes:
        try:
            process.terminate()
        except psutil.NoSuchProcess:
            pass
    descendants = [process for process in processes if process.pid != child.pid]
    _, alive = psutil.wait_procs(descendants, timeout=1)
    try:
        child.wait(timeout=1)
    except subprocess.TimeoutExpired:
        try:
            psutil.Process(child.pid).kill()
        except psutil.NoSuchProcess:
            pass
    for process in alive:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(alive, timeout=2)
    # Also reclaim the original group if a descendant raced with enumeration.
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait(timeout=3)
    live = []
    for process in alive:
        try:
            if process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                live.append(process.pid)
        except psutil.NoSuchProcess:
            pass
    if live:
        raise RuntimeError('Owned subprocesses survived cancellation')


def execute(command, logfile, *, timeout=900, cwd=None, env=None):
    from tools.validation_suite import sha
    start = time.monotonic()
    status = 'passed'
    with Path(logfile).open('wb') as log:
        child = subprocess.Popen(command, cwd=cwd, env=env, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        try:
            child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            status = 'timeout'
            with cleanup_signals():
                stop_tree(child)
        except BaseException:
            with cleanup_signals():
                stop_tree(child)
            raise
        if child.returncode != 0 and status == 'passed':
            status = 'failed'
    return dict(status=status, exit_code=child.returncode, elapsed_s=time.monotonic()-start,
                log=Path(logfile).name, log_sha256=sha(logfile))
