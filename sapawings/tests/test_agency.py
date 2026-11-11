import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agency import load_config, manifest, plan, validate

class AgencyTest(unittest.TestCase):
    def setUp(self): self.c=load_config()
    def test_contract_complete(self):
        self.assertEqual(validate(self.c),dict(roles=30,departments=7,brands=4,stages=9,mode='offline_preflight_only'))
    def test_brand_isolation(self):
        with self.assertRaises(ValueError): plan(self.c,'sapa_wings','one',[{'brand_id':'old_stone'}])
        with self.assertRaises(ValueError): plan(self.c,'sapa_wings','one',[{}])
    def test_unverified_brands_blocked(self):
        for b in ('old_stone','3143','khong_gian_van_hoa','unknown'):
            with self.assertRaises(ValueError): manifest(self.c,b)
    def test_policy_cannot_enable_writes(self):
        for k,v in [('publish_enabled',True),('pms_access','write'),('computer','on'),('external_adapters','automatic'),('approval','full'),('runtime_deployed',True),('spend_enabled',True),('browser',True),('max_concurrent_workers',30)]:
            c=copy.deepcopy(self.c); c['policy'][k]=v
            with self.assertRaises(ValueError): validate(c)
    def test_duplicate_or_missing_assignment(self):
        c=copy.deepcopy(self.c); c['departments'][0]['specialists'].append('research_1')
        with self.assertRaises(ValueError): validate(c)
        c=copy.deepcopy(self.c); c['departments'][0]['specialists'].remove('research_4')
        with self.assertRaises(ValueError): validate(c)
    def test_qc_cannot_be_skipped_or_reassigned(self):
        c=copy.deepcopy(self.c); c['stages'].pop(5)
        with self.assertRaises(ValueError): validate(c)
        c=copy.deepcopy(self.c); c['stages'][5]['owner']='content_1'
        with self.assertRaises(ValueError): validate(c)
    def test_namespace_collision(self):
        c=copy.deepcopy(self.c); c['brands'][1]['namespace']=c['brands'][0]['namespace']
        with self.assertRaises(ValueError): validate(c)
    def test_generated_manifest_has_one_chief_eight_workers(self):
        m=manifest(self.c)
        self.assertEqual(m['defaults'],dict(approval='ask',computer='off',browser=False))
        self.assertEqual(len(m['bots']),8)
        self.assertEqual(sum(b['chief'] for b in m['bots']),1)
        self.assertEqual(len(m['rooms'][0]['members']),8)
        self.assertFalse(m['teams'][0]['prune'])
    def test_rehearsal_never_marks_work_completed(self):
        p=plan(self.c,'sapa_wings','campaign-a',[{'brand_id':'sapa_wings'}])
        self.assertFalse(p['external_writes'])
        self.assertTrue(all(s['state']=='planned' for s in p['steps']))
        self.assertEqual(p['task_key'],plan(self.c,'sapa_wings','campaign-a')['task_key'])
        self.assertNotEqual(p['task_key'],plan(self.c,'sapa_wings','campaign-b')['task_key'])
    def test_empty_task_rejected(self):
        with self.assertRaises(ValueError): plan(self.c,'sapa_wings',' ')

if __name__=='__main__': unittest.main()
