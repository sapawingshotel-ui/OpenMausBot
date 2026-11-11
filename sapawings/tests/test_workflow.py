import tempfile
import unittest
from pathlib import Path
from workflow import Workflow, qc_errors, summarize


def payload():
    return {'vi':'Ảnh lưu trữ của khách sạn.', 'en':'Hotel archive photo.', 'alt':'A real room', 'archive_disclosed':True, 'asset':{'origin':'real_photo','reviewed':True,'source':'fixture://photo','sha256':'fixture-checksum','archive':True}, 'sources':['fixture://source'], 'claims':[], 'design_sha256':'render-checksum'}


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.flow = Workflow(Path(self.tmp.name)/'isolated.sqlite')
        self.flow.create('p1', payload())

    def tearDown(self):
        self.flow.db.close()
        self.tmp.cleanup()

    def ready(self):
        for role in ('Research','Design','Quality Control'):
            self.flow.advance('p1',role)

    def test_no_shortcut_to_publish(self):
        with self.assertRaises(ValueError):
            self.flow.request_schedule('p1','2099-01-01T10:00:00+07:00')

    def test_role_order(self):
        with self.assertRaises(ValueError):self.flow.advance('p1','Quality Control')

    def test_archive_requires_actual_caption(self):
        p=payload();p['en']='A current room';self.assertTrue(qc_errors(p))

    def test_ambiguous_type_rejected(self):
        p=payload();p['asset']['room_type_ambiguous']=True;p['room_type_claim']='Family';self.assertTrue(qc_errors(p))

    def test_unverified_price_rejected(self):
        p=payload();p['claims']=[{'text':'500K/night','status':'historical','source':'2023'}];self.assertTrue(qc_errors(p))

    def test_idempotent_outbox(self):
        self.ready();a=self.flow.request_schedule('p1','2099-01-01T10:00:00+07:00');b=self.flow.request_schedule('p1','2099-01-01T10:00:00+07:00');self.assertEqual(a,b)

    def test_revision_revokes_qc_and_pending(self):
        self.ready();key=self.flow.request_schedule('p1','2099-01-01T10:00:00+07:00');p=payload();p['vi']='Ảnh lưu trữ đã sửa';self.flow.revise('p1',p)
        with self.assertRaises(ValueError):self.flow.confirm_schedule(key,{'external_id':'x','readback_verified':True,'draft':False,'scheduled_at':'2099-01-01T10:00:00+07:00'})
        self.assertEqual(self.flow.get('p1')['state'],'draft')

    def test_timezone_required(self):
        self.ready()
        with self.assertRaises(ValueError):self.flow.request_schedule('p1','2099-01-01T10:00:00')

    def test_draft_receipt_not_scheduled(self):
        self.ready();key=self.flow.request_schedule('p1','2099-01-01T10:00:00+07:00')
        with self.assertRaises(ValueError):self.flow.confirm_schedule(key,{'external_id':'x','readback_verified':True,'draft':True})

    def test_live_receipt_and_duplicate(self):
        self.ready();key=self.flow.request_schedule('p1','2099-01-01T10:00:00+07:00');r={'external_id':'x','readback_verified':True,'draft':False,'scheduled_at':'2099-01-01T10:00:00+07:00'}
        self.flow.confirm_schedule(key,r);self.flow.confirm_schedule(key,r);self.assertEqual(self.flow.get('p1')['state'],'scheduled')
        with self.assertRaises(ValueError):self.flow.revise('p1',payload())

    def test_missing_metric_is_not_zero(self):
        self.assertIsNone(summarize([{'reach':None}])['reach'])

    def test_per_post_sum(self):
        self.assertEqual(summarize([{'reach':3},{'reach':14},{'reach':15},{'reach':41}])['reach'],73)


if __name__=='__main__':unittest.main()
