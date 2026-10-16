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
