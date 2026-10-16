import json
from pathlib import Path
import sys
import tempfile
import unittest
import psutil
from tools.validation_process import execute
from tools.validate_local import check_snapshot


class ValidationTests(unittest.TestCase):
    def test_nonzero_and_timeout_do_not_pass_and_descendants_are_cleaned(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)
            failed=execute([sys.executable,'-c','raise SystemExit(7)'],out/'failed.txt',timeout=2)
            self.assertEqual(failed['status'],'failed');self.assertEqual(failed['exit_code'],7)
            pidfile=out/'child.json'
            script="import subprocess,sys,time,json; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True); open(sys.argv[1],'w').write(json.dumps([p.pid])); time.sleep(30)"
            result=execute([sys.executable,'-c',script,str(pidfile)],out/'timeout.txt',timeout=.3)
            self.assertEqual(result['status'],'timeout');self.assertNotEqual(result['exit_code'],0)
            pid=json.loads(pidfile.read_text())[0]
            try:self.assertEqual(psutil.Process(pid).status(),psutil.STATUS_ZOMBIE)
            except psutil.NoSuchProcess:pass
    def test_snapshot_changes_are_rejected(self):
        from tools.validation_suite import sha
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'source.py').write_text('original')
            expected={'source.py':sha(root/'source.py')};check_snapshot(root,expected)
            (root/'source.py').write_text('changed')
            with self.assertRaises(RuntimeError):check_snapshot(root,expected)
    def test_normal_parent_exit_cannot_hide_new_session_child(self):
        for exit_code in [0,7]:
            with self.subTest(exit_code=exit_code),tempfile.TemporaryDirectory() as td:
                out=Path(td);pidfile=out/'pid'
                script="import subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True); open(sys.argv[1],'w').write(str(p.pid)); raise SystemExit(int(sys.argv[2]))"
                result=execute([sys.executable,'-c',script,str(pidfile),str(exit_code)],out/'log',timeout=2)
                pid=int(pidfile.read_text())
                try:
                    self.assertEqual(result['status'],'failed');self.assertGreaterEqual(result['reclaimed_orphans'],1)
                    try:self.assertEqual(psutil.Process(pid).status(),psutil.STATUS_ZOMBIE)
                    except psutil.NoSuchProcess:pass
                finally:
                    try:psutil.Process(pid).kill()
                    except psutil.NoSuchProcess:pass
    def test_timeout_is_not_passed_even_when_sigterm_handler_exits_zero(self):
        with tempfile.TemporaryDirectory() as td:
            result=execute([sys.executable,'-c',"import signal,time; signal.signal(signal.SIGTERM,lambda *a:exit(0)); time.sleep(30)"],Path(td)/'log',timeout=.3)
            self.assertEqual(result['exit_code'],0);self.assertEqual(result['status'],'timeout')
    def test_interrupted_command_is_recorded(self):
        from unittest.mock import patch
        from tools.validate_local import Commands
        with tempfile.TemporaryDirectory() as td:
            r={'operations':{}};c=Commands(Path(td),r)
            with patch('tools.validate_local.execute',side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):c.call('probe',['unused'])
            self.assertEqual(r['operations']['probe']['status'],'interrupted')
    def test_failed_evidence_export_retains_container(self):
        from unittest.mock import Mock
        from tools.validate_local import remove_owned_container
        commands=Mock();commands.capture.return_value='[{"State":{"Running":false}}]'
        commands.call.return_value={'status':'failed'}
        with self.assertRaisesRegex(RuntimeError,'retained'):
            remove_owned_container(commands,'docker','owned',Path('/unused'),False)
        self.assertEqual([c.args[0] for c in commands.call.call_args_list],['cleanup-export'])
    def test_manifest_failure_retains_failed_suite_receipt(self):
        from unittest.mock import patch
        from tools.validation_suite import run
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'suite'
            with patch('tools.validation_suite.manifest',side_effect=RuntimeError('injected')):
                with self.assertRaisesRegex(RuntimeError,'injected'):run(out,'native-macos')
            self.assertEqual(json.loads((out/'validation.json').read_text())['status'],'failed')
