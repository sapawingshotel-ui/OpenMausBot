"""Private, operator-managed brand evidence; no automatic promotion of learnings.

The host owns this store. Source text is data, never an instruction or tool grant.
Filesystem/process isolation and semantic source review remain deployment duties.
"""
from __future__ import annotations
import json
import os
import sqlite3
from datetime import datetime,timezone
from pathlib import Path
from workflow import digest

BRANDS={'sapa_wings','old_stone','3143','khong_gian_van_hoa'}
KINDS={'fact','rule','voice','asset','lesson'}
STATUSES={'verified','provisional','historical','disputed'}
VOLATILE={'price','policy','availability','event'}


def utc(value):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:raise ValueError('Timezone-aware evidence date required')
    return dt.astimezone(timezone.utc)


class BrandMemory:
    def __init__(self,path,clock=lambda:datetime.now(timezone.utc)):
        self.clock=clock;path=Path(path)
        if path.is_symlink():raise ValueError('Symlink memory refused')
        fd=os.open(path,os.O_CREAT|os.O_RDWR,0o600);os.close(fd);path.chmod(0o600)
        self.db=sqlite3.connect(path);self.db.row_factory=sqlite3.Row
        self.db.execute('''CREATE TABLE IF NOT EXISTS cards(brand TEXT,key TEXT,version INTEGER,body TEXT NOT NULL,PRIMARY KEY(brand,key,version))''')

    def close(self):self.db.close()

    def operator_record(self,brand,key,card,expected_version=0):
        if brand not in BRANDS or not isinstance(key,str) or not key.strip():raise ValueError('Brand and key required')
        if card.get('kind') not in KINDS or card.get('status') not in STATUSES:raise ValueError('Invalid evidence classification')
        if not all(card.get(k) for k in ('text','source','observed_at')):raise ValueError('Text and source evidence required')
        observed=utc(card['observed_at']);expires=utc(card['valid_until']) if card.get('valid_until') else None
        if observed>self.clock():raise ValueError('Future observation refused')
        if expires and expires<=observed and card['status']=='verified':raise ValueError('Verified evidence cannot already be expired at observation')
        if card.get('topic') in VOLATILE and not expires:raise ValueError('Volatile evidence needs expiry')
        if card['status']=='verified' and not card.get('reviewed_by'):raise ValueError('Verified evidence needs an operator review record')
        if card['kind']=='asset' and card['status']=='verified' and (card.get('rights_status')!='confirmed' or not card.get('sha256')):raise ValueError('Verified asset needs rights and hash')
        if card['kind']=='lesson' and card['status']=='verified' and not card.get('measurement_refs'):raise ValueError('Verified lesson needs measurements')
        if any(k in card for k in ('guest_name','guest_id','passport','booking_records','credentials','access_token')):raise ValueError('Sensitive fields prohibited')
        body=json.dumps(card,ensure_ascii=False,sort_keys=True)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old=self.db.execute('SELECT MAX(version) FROM cards WHERE brand=? AND key=?',(brand,key)).fetchone()[0] or 0
            if expected_version!=old:raise ValueError('Stale memory version')
            self.db.execute('INSERT INTO cards VALUES(?,?,?,?)',(brand,key,old+1,body))
            return old+1

    def cards(self,brand):
        if brand not in BRANDS:raise ValueError('Unknown brand')
        rows=self.db.execute('''SELECT c.* FROM cards c JOIN (SELECT key,MAX(version) v FROM cards WHERE brand=? GROUP BY key) x ON c.key=x.key AND c.version=x.v WHERE c.brand=? ORDER BY c.key''',(brand,brand)).fetchall()
        return [dict(key=r['key'],version=r['version'],**json.loads(r['body'])) for r in rows]

    def snapshot(self,brand):
        accepted=[];excluded=[]
        for c in self.cards(brand):
            reason='not_verified' if c['status']!='verified' else 'expired' if c.get('valid_until') and utc(c['valid_until'])<=self.clock() else None
            (excluded if reason else accepted).append(dict(key=c['key'],version=c['version'],reason=reason) if reason else c)
        content={'brand_id':brand,'cards':accepted,'excluded':excluded}
        return dict(**content,digest=digest(content))

    def verify_snapshot(self,brand,snapshot):
        if not isinstance(snapshot,dict) or snapshot.get('brand_id')!=brand:raise ValueError('Snapshot brand mismatch')
        current=self.snapshot(brand)
        if snapshot!=current:raise ValueError('Memory changed, expired or snapshot was tampered with; revise and re-QC')
        return current

    def build_brief(self,brand,objective,asset_refs=()):
        if not isinstance(objective,str) or not objective.strip():raise ValueError('Objective required')
        snapshot=self.snapshot(brand)
        return {'brief':objective,'brand_id':brand,'memory_snapshot':snapshot,
                'evidence':[{'brand_id':brand,'source':c['source'],'key':c['key'],'version':c['version']} for c in snapshot['cards']],
                'asset_refs':list(asset_refs),'required_outputs':['Vietnamese caption','English caption','alt text','editable design','render preview','source and rights record'],
                'checks':['real hotel assets only','archive disclosure when applicable','three independent QC decisions','no unverified rates, inventory or policy'],
                'external_writes':False,'publication_status':'not_authorized_by_brief'}
