import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch,AsyncMock
from tools import benchmark
from support import config,proxy_process


class HarnessTests(unittest.TestCase):
    def test_manifest_or_trial_failure_invalidates_old_json_and_html(self):
        for stage in ['manifest','trial']:
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp);(path/'report.json').write_text('{"status":"passed"}');(path/'report.html').write_text('old success')
                real=benchmark.manifest
                with patch.object(sys,'argv',['benchmark','--output',tmp,'--label','failure-fixture']),patch.object(benchmark,'manifest',side_effect=RuntimeError('injected') if stage=='manifest' else real),patch.object(benchmark,'trial',new=AsyncMock(side_effect=RuntimeError('injected'))):
                    with self.assertRaisesRegex(RuntimeError,'injected'):benchmark.main()
                self.assertEqual(json.loads((path/'report.json').read_text())['status'],'failed');self.assertFalse((path/'report.html').exists())
    def test_abnormal_process_exit_is_rejected(self):
        p=proxy_process(config(1));p.process.kill();p.process.wait(2)
        with self.assertRaises(AssertionError):p.close()
    def test_invalid_ledger_cannot_publish_passed_report(self):
        import copy
        r=json.loads((Path(os.environ.get('DNSROUTER_TEST_REPORT','results/native-macos'))/'report.json').read_text())
        rows=copy.deepcopy(r['trials'][:12]);rows[0]['proxy_metrics']['upstream_errors']=999
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sys,'argv',['benchmark','--output',tmp,'--blocks','1','--label','failure-fixture']),patch.object(benchmark,'trial',new=AsyncMock(side_effect=rows)):
                with self.assertRaises(ValueError):benchmark.main()
            self.assertEqual(json.loads((Path(tmp)/'report.json').read_text())['status'],'failed')
            self.assertFalse((Path(tmp)/'report.html').exists())
