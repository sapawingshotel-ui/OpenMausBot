import copy
import secrets
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from task_store import TaskStore,token_hash

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.now=1000.; self.tokens={}; self.registry=[]
        roles={'chief':['read','create','revise','publish_preflight'],
          'writer':['read']+['work:'+r for r in ['research_2','research_1','content_1','content_3','creative_1']],
          'fact':['read','qc:fact'],'visual':['read','qc:visual'],'rights':['read','qc:rights'],
          'other':['read','create']}
        for name,caps in roles.items():
            token=secrets.token_urlsafe(32); self.tokens[name]=token
            self.registry.append(dict(id=name,token_hash=token_hash(token),brands=['old_stone'] if name=='other' else ['sapa_wings'],capabilities=caps,expires_at=2000))
        self.path=Path(self.tmp.name)/'queue.sqlite'
        self.s=TaskStore(self.path,self.registry,clock=lambda:self.now)
        self.s.create(self.tokens['chief'],'sapa_wings','one',{'brief':'synthetic test','evidence':[{'brand_id':'sapa_wings'}]})
    def tearDown(self): self.s.close();self.tmp.cleanup()
    def get(self): return self.s.get(self.tokens['chief'],'sapa_wings','one')
    def to_qc(self):
        for stage in ['research','trends','brief','script','production']:
            t=self.tokens['writer']; l=self.s.claim(t,'sapa_wings','one',stage)
            self.s.complete(t,'sapa_wings','one',l['lease'],l['revision'],stage,{'output_refs':['synthetic:output'],'evidence_refs':['synthetic:evidence']})
        return self.get()
    def qc(self):
        r=self.to_qc()
        for kind in ['fact','visual','rights']: self.s.review(self.tokens[kind],'sapa_wings','one',r['revision'],r['digest'],kind,True)
        return self.get()
    def test_survives_restart(self):
        self.s.close();self.s=TaskStore(self.path,self.registry,clock=lambda:self.now)
        self.assertEqual(self.get()['stage'],'research')
        self.assertEqual(self.path.stat().st_mode&0o777,0o600)
    def test_invalid_and_cross_brand_credentials(self):
        for token in ['invalid',secrets.token_urlsafe(32),self.tokens['other']]:
            with self.assertRaises(PermissionError): self.s.get(token,'sapa_wings','one')
        with self.assertRaises(PermissionError): self.s.create(self.tokens['other'],'old_stone','one',{'brief':'x'})
    def test_expired_token(self):
        self.now=2001
        with self.assertRaises(PermissionError): self.get()
    def test_no_self_assignment(self):
        with self.assertRaises(PermissionError): self.s.claim(self.tokens['chief'],'sapa_wings','one','research')
        with self.assertRaises(ValueError): self.s.claim(self.tokens['writer'],'sapa_wings','one','script')
    def test_concurrent_claims(self):
        second=TaskStore(self.path,self.registry,clock=lambda:self.now)
        try:
            self.s.claim(self.tokens['writer'],'sapa_wings','one','research')
            with self.assertRaises(ValueError): second.claim(self.tokens['writer'],'sapa_wings','one','research')
        finally: second.close()
    def test_lease_expiry_and_stale_completion(self):
        t=self.tokens['writer']; old=self.s.claim(t,'sapa_wings','one','research');self.now+=121
        newer=self.s.claim(t,'sapa_wings','one','research')
        with self.assertRaises(PermissionError): self.s.complete(t,'sapa_wings','one',old['lease'],1,'research',{'output_refs':['x'],'evidence_refs':['y']})
        self.s.complete(t,'sapa_wings','one',newer['lease'],1,'research',{'output_refs':['x'],'evidence_refs':['y']})
        self.assertEqual(self.get()['stage'],'trends')
    def test_revise_revokes_lease(self):
        l=self.s.claim(self.tokens['writer'],'sapa_wings','one','research')
        self.s.revise(self.tokens['chief'],'sapa_wings','one',1,{'brief':'new'})
        with self.assertRaises(PermissionError): self.s.complete(self.tokens['writer'],'sapa_wings','one',l['lease'],1,'research',{'output_refs':['x'],'evidence_refs':['y']})
        self.assertEqual(self.get()['revision'],2)
    def test_three_failures_hold(self):
        for _ in range(3):
            l=self.s.claim(self.tokens['writer'],'sapa_wings','one','research')
            self.s.fail(self.tokens['writer'],'sapa_wings','one',l['lease'],1,'research')
        self.assertEqual(self.get()['state'],'held')
        with self.assertRaises(ValueError): self.s.claim(self.tokens['writer'],'sapa_wings','one','research')
    def test_qc_seal_revision_invalidated(self):
        r=self.qc();t=self.tokens['chief'];p=self.s.publish_preflight(t,'sapa_wings','one',1,r['digest'])
        self.assertFalse(p['external_writes']);self.assertIn('blocked',p['status'])
        self.assertEqual(p['task_key'],self.s.publish_preflight(t,'sapa_wings','one',1,r['digest'])['task_key'])
        self.s.revise(t,'sapa_wings','one',1,{'brief':'edited'})
        with self.assertRaises(ValueError): self.s.publish_preflight(t,'sapa_wings','one',1,r['digest'])
    def test_missing_qc_and_failed_qc(self):
        r=self.to_qc()
        with self.assertRaises(ValueError): self.s.publish_preflight(self.tokens['chief'],'sapa_wings','one',1,r['digest'])
        self.s.review(self.tokens['fact'],'sapa_wings','one',1,r['digest'],'fact',False)
        self.assertEqual(self.get()['state'],'held')
    def test_writer_cannot_review_own_work(self):
        r=self.to_qc();self.s.principals[1]['capabilities'].append('qc:fact')
        with self.assertRaises(PermissionError): self.s.review(self.tokens['writer'],'sapa_wings','one',1,r['digest'],'fact',True)
    def test_one_identity_cannot_supply_three_reviews(self):
        r=self.to_qc();self.s.principals[2]['capabilities'].append('qc:visual')
        self.s.review(self.tokens['fact'],'sapa_wings','one',1,r['digest'],'fact',True)
        with self.assertRaises(PermissionError): self.s.review(self.tokens['fact'],'sapa_wings','one',1,r['digest'],'visual',True)
    def test_no_token_or_lease_in_status_or_audit(self):
        lease=self.s.claim(self.tokens['writer'],'sapa_wings','one','research')['lease']
        text=str(self.get())+str([tuple(x) for x in self.s.db.execute('SELECT * FROM audit')])
        self.assertNotIn(lease,text)
        for token in self.tokens.values(): self.assertNotIn(token,text)
    def test_cross_brand_evidence_and_missing_stage_evidence(self):
        with self.assertRaises(ValueError): self.s.revise(self.tokens['chief'],'sapa_wings','one',1,{'brief':'x','evidence':[{'brand_id':'old_stone'}]})
        l=self.s.claim(self.tokens['writer'],'sapa_wings','one','research')
        with self.assertRaises(ValueError): self.s.complete(self.tokens['writer'],'sapa_wings','one',l['lease'],1,'research',{})

if __name__=='__main__':unittest.main()
