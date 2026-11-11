import copy
import secrets
import sys
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from brand_memory import BrandMemory
import test_task_store as fixtures

class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.now=datetime(2026,11,11,6,tzinfo=timezone.utc)
        self.m=BrandMemory(Path(self.tmp.name)/'memory.sqlite',clock=lambda:self.now)
        self.card=dict(kind='fact',status='verified',topic='location',text='test fact',source='synthetic:source',observed_at='2026-11-10T00:00:00Z',reviewed_by='operator')
    def tearDown(self):self.m.close();self.tmp.cleanup()
    def test_brand_separation_and_restart(self):
        self.m.operator_record('sapa_wings','location',self.card)
        self.assertEqual(self.m.snapshot('old_stone')['cards'],[])
        path=Path(self.tmp.name)/'memory.sqlite';self.m.close();self.m=BrandMemory(path,clock=lambda:self.now)
        self.assertEqual(len(self.m.snapshot('sapa_wings')['cards']),1)
    def test_provisional_historical_disputed_never_become_facts(self):
        for s in ('provisional','historical','disputed'):
            self.m.operator_record('sapa_wings',s,dict(self.card,status=s))
        snapshot=self.m.snapshot('sapa_wings');self.assertFalse(snapshot['cards']);self.assertEqual(len(snapshot['excluded']),3)
    def test_expiry_changes_snapshot(self):
        self.m.operator_record('sapa_wings','policy',dict(self.card,topic='policy',valid_until='2026-11-12T00:00:00Z'))
        s=self.m.snapshot('sapa_wings');self.now+=timedelta(days=2)
        with self.assertRaises(ValueError):self.m.verify_snapshot('sapa_wings',s)
        self.assertEqual(self.m.snapshot('sapa_wings')['excluded'][0]['reason'],'expired')
    def test_volatile_requires_expiry(self):
        for topic in ('price','policy','availability','event'):
            with self.assertRaises(ValueError):self.m.operator_record('sapa_wings',topic,dict(self.card,topic=topic))
    def test_review_rights_and_measurements_required(self):
        c=dict(self.card);c.pop('reviewed_by')
        with self.assertRaises(ValueError):self.m.operator_record('sapa_wings','no-review',c)
        with self.assertRaises(ValueError):self.m.operator_record('sapa_wings','asset',dict(self.card,kind='asset'))
        with self.assertRaises(ValueError):self.m.operator_record('sapa_wings','lesson',dict(self.card,kind='lesson'))
    def test_optimistic_updates_and_old_version_not_retrieved(self):
        self.m.operator_record('sapa_wings','fact',self.card)
        with self.assertRaises(ValueError):self.m.operator_record('sapa_wings','fact',self.card)
        self.m.operator_record('sapa_wings','fact',dict(self.card,status='disputed'),expected_version=1)
        self.assertFalse(self.m.snapshot('sapa_wings')['cards'])
        self.assertEqual(self.m.db.execute('SELECT COUNT(*) FROM cards').fetchone()[0],2)
    def test_historical_evidence_can_be_observed_after_expiry(self):
        self.m.operator_record('sapa_wings','old-price',dict(self.card,status='historical',topic='price',valid_until='2024-01-01T00:00:00Z'))
        self.assertFalse(self.m.snapshot('sapa_wings')['cards'])

    def test_tampered_snapshot_rejected(self):
        s=self.m.snapshot('sapa_wings');s['cards'].append(self.card)
        with self.assertRaises(ValueError):self.m.verify_snapshot('sapa_wings',s)
        with self.assertRaises(ValueError):self.m.verify_snapshot('old_stone',self.m.snapshot('sapa_wings'))
    def test_date_and_sensitive_fields(self):
        for changes in ({'observed_at':'2026-11-10T00:00:00'},{'observed_at':'2030-01-01T00:00:00Z'},{'guest_name':'private'}):
            with self.assertRaises(ValueError):self.m.operator_record('sapa_wings','x',dict(self.card,**changes))

class MemoryWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.fx=fixtures.StoreTests();self.fx.setUp()
        self.m=BrandMemory(Path(self.fx.tmp.name)/'memory.sqlite')
        self.card=dict(kind='rule',status='verified',text='Use real hotel photos',source='synthetic:owner brief',observed_at='2026-11-10T00:00:00Z',reviewed_by='owner')
        self.m.operator_record('sapa_wings','real-photos',self.card)
        self.fx.s.memory=self.m
        with self.fx.s.db:self.fx.s.db.execute('DELETE FROM tasks')
        self.fx.s.create(self.fx.tokens['chief'],'sapa_wings','one',self.m.build_brief('sapa_wings','test memory workflow'))
    def tearDown(self):self.m.close();self.fx.tearDown()
    def test_memory_change_invalidates_publish_preflight(self):
        r=self.fx.qc()
        self.m.operator_record('sapa_wings','real-photos',dict(self.card,text='Changed rule'),expected_version=1)
        with self.assertRaises(ValueError):self.fx.s.publish_preflight(self.fx.tokens['chief'],'sapa_wings','one',1,r['digest'])
    def test_memory_change_invalidates_pending_qc(self):
        r=self.fx.to_qc()
        self.m.operator_record('sapa_wings','real-photos',dict(self.card,text='Changed rule'),expected_version=1)
        with self.assertRaises(ValueError):self.fx.s.review(self.fx.tokens['fact'],'sapa_wings','one',1,r['digest'],'fact',True)
    def test_memory_change_invalidates_inflight_completion(self):
        f=self.fx;l=f.s.claim(f.tokens['writer'],'sapa_wings','one','research')
        self.m.operator_record('sapa_wings','real-photos',dict(self.card,text='Changed rule'),expected_version=1)
        with self.assertRaises(ValueError):f.s.complete(f.tokens['writer'],'sapa_wings','one',l['lease'],1,'research',{'output_refs':['x'],'evidence_refs':['y']})

    def test_snapshot_cannot_be_detached_or_forged(self):
        with self.assertRaises(ValueError):self.fx.s.create(self.fx.tokens['chief'],'sapa_wings','missing',{'brief':'missing snapshot'})
        brief=self.m.build_brief('sapa_wings','test');brief['memory_snapshot']['digest']='forged'
        with self.assertRaises(ValueError):self.fx.s.create(self.fx.tokens['chief'],'sapa_wings','forged',brief)
        self.fx.s.memory=None
        with self.assertRaises(ValueError):self.fx.s.create(self.fx.tokens['chief'],'sapa_wings','detached',self.m.build_brief('sapa_wings','test'))

if __name__=='__main__':unittest.main()
