import copy
import json
import os
from pathlib import Path
import unittest
import dns.exception
from tools.benchmark import render
from tools.check_report import verify


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=json.loads((Path(os.environ.get('DNSROUTER_TEST_REPORT','results/native-macos'))/'report.json').read_text())
    def test_complete_production_report(self):
        self.assertEqual(verify(self.report),36)
        self.assertEqual(render(self.report),(Path(os.environ.get('DNSROUTER_TEST_REPORT','results/native-macos'))/'report.html').read_text())
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
    def test_invalid_counters_peer_binding_and_scheduled_latency_rejected(self):
        for change in ['negative_bytes','errors','unsupported','negative_hits','route_port','peer_delay','scheduled','nan_time','infinite_cpu','truncated']:
            r=copy.deepcopy(self.report);t=r['trials'][0];m=t['proxy_metrics']
            if change=='negative_bytes':m['cache_wire_bytes']=-1
            elif change=='errors':m['upstream_errors']=999
            elif change=='unsupported':m['unsupported']=999
            elif change=='negative_hits':m['negative_hits']=121
            elif change=='route_port':t['actual_config']['routes'][0]['upstreams'][0]['port']=1
            elif change=='peer_delay':t['upstream_readiness'][0]['delay_s']=.001
            elif change=='scheduled':t['scheduled_p95_s']+=.01
            elif change=='nan_time':t['flows'][0]['finished_s']=float('nan')
            elif change=='infinite_cpu':t['samples'][0]['cpu']=float('inf')
            else:
                response=dns.message.from_wire(bytes.fromhex(t['flows'][0]['wire_hex']))
                response.flags|=dns.flags.TC;t['flows'][0]['wire_hex']=response.to_wire().hex()
            with self.subTest(change=change),self.assertRaises(ValueError):verify(r)
