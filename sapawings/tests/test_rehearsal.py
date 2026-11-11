import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rehearsal import run

class RehearsalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        photo=self.root/'photo';photo.write_bytes(b'synthetic test bytes')
        (self.root/'BOUTIQUE-1.png').write_bytes(b'synthetic render bytes')
        self.inputs=self.root/'inputs.json';self.inputs.write_text(json.dumps([dict(photo=str(photo),source='synthetic:source',vi='test',en='test',alt='test')]))
    def tearDown(self):self.temp.cleanup()
    def test_restart_no_duplicate_or_automatic_qc(self):
        a=run(self.inputs,self.root/'state');b=run(self.inputs,self.root/'state')
        self.assertEqual(a,b);self.assertEqual(a['tasks'][0]['stage'],'qc');self.assertFalse(a['tasks'][0]['external_writes'])
    def test_changed_real_asset_requires_revision(self):
        run(self.inputs,self.root/'state');(self.root/'photo').write_bytes(b'changed')
        with self.assertRaises(ValueError):run(self.inputs,self.root/'state')

if __name__=='__main__':unittest.main()
