import copy
import json
from pathlib import Path
import unittest
import dns.exception
from tools.benchmark import render
from tools.check_report import verify


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=json.loads(Path('results/native-macos/report.json').read_text())
    def test_complete_production_report(self):
        self.assertEqual(verify(self.report),36)
        self.assertEqual(render(self.report),Path('results/native-macos/report.html').read_text())
    def test_missing_block_and_reordered_rows_rejected(self):
        for change in ['block','order']:
            r=copy.deepcopy(self.report)
            if change=='block':r['trials']=r['trials'][:12]
            else:r['trials'].reverse()
            with self.subTest(change=change),self.assertRaises(ValueError):verify(r)
    def test_bad_wire_answer_rss_and_counts_rejected(self):
        for change in ['wire','rss','count','sample','config','source','status']:
            r=copy.deepcopy(self.report);t=r['trials'][0]
            if change=='wire':t['flows'][0]['wire_hex']='0000'
            elif change=='rss':t['peak_rss']=0
            elif change=='count':t['proxy_metrics']['upstream_attempts']+=1
            elif change=='sample':t['samples']=t['samples'][:2]
            elif change=='config':t['actual_config']['cache_entries']=99
            elif change=='source':r['source_files']['dnsrouter/cache.py']='0'*64
            else:r['status']='failed'
            with self.subTest(change=change),self.assertRaises((ValueError,dns.exception.DNSException)):verify(r)
