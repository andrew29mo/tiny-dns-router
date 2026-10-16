import argparse
import asyncio
import fcntl
import json
from pathlib import Path
import signal
from .service import Server,atomic,identity


async def run(args):
    state=args.state;state.mkdir(parents=True,exist_ok=True)
    with (state/'process.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        (state/'ready.json').unlink(missing_ok=True)
        server=Server(json.loads(args.config.read_text()))
        stop=asyncio.Event();loop=asyncio.get_running_loop()
        for sig in [signal.SIGTERM,signal.SIGINT]:loop.add_signal_handler(sig,stop.set)
        try:
            port=await server.start()
            atomic(state/'metrics.json',server.metrics())
            atomic(state/'ready.json',dict(host='127.0.0.1',port=port,config=server.cfg,source_files=identity()))
            while not stop.is_set():
                try:await asyncio.wait_for(stop.wait(),.05)
                except TimeoutError:pass
                atomic(state/'metrics.json',server.metrics())
        finally:
            await server.close();atomic(state/'metrics.json',server.metrics())
            (state/'ready.json').unlink(missing_ok=True)
        if server.stats['internal_errors']:raise RuntimeError('internal request errors recorded')


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--state',type=Path,required=True)
    asyncio.run(run(p.parse_args()))

if __name__=='__main__':main()
