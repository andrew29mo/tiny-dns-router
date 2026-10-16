"""Run standard formal unittest discovery and retain exact outcomes."""
import argparse
from pathlib import Path
import unittest
from tools.validation_suite import save


def test_ids(suite):
    result=[]
    for item in suite:
        result.extend(test_ids(item) if isinstance(item,unittest.TestSuite) else [item.id()])
    return sorted(result)


class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.started_ids=[];self.success_ids=[]
    def startTest(self,test):self.started_ids.append(test.id());super().startTest(test)
    def addSuccess(self,test):self.success_ids.append(test.id());super().addSuccess(test)


def run(output):
    r=dict(schema_version=1,status='running',expected_ids=[],started_ids=[],success_ids=[])
    save(output,r)
    try:
        suite=unittest.defaultTestLoader.discover('tests');r['expected_ids']=test_ids(suite);save(output,r)
        result=unittest.TextTestRunner(verbosity=2,buffer=True,resultclass=Result).run(suite)
        r.update(started_ids=sorted(result.started_ids),success_ids=sorted(result.success_ids))
        if not r['expected_ids'] or not result.wasSuccessful() or r['expected_ids']!=r['started_ids'] or r['expected_ids']!=r['success_ids']:raise RuntimeError('Incomplete or unsuccessful formal tests')
        r['status']='passed';save(output,r)
    except BaseException as e:r.update(status='failed',error_type=type(e).__name__);save(output,r);raise
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.output)
