"""Local authenticated task rehearsal. No network, model or publishing adapter.

Trusted process setup owns the principal registry; workers receive only their
own bearer. Filesystem/process access must be separated before deployment.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from agency import load_config, validate


def seal(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class TaskStore:
    def __init__(self, path, principals, clock=time.time, memory=None):
        self.clock=clock
        self.memory=memory
        self.config=load_config(); validate(self.config)
        self.principals=json.loads(json.dumps(principals))
        self.stages=[s['id'] for s in self.config['stages']]
        self.owners={s['id']:s['owner'] for s in self.config['stages']}
        path=Path(path)
        if path.exists() and path.is_symlink(): raise ValueError('Symlink database refused')
        fd=os.open(path,os.O_CREAT|os.O_RDWR,0o600); os.close(fd); os.chmod(path,0o600)
        self.db=sqlite3.connect(path,timeout=5)
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS tasks(brand TEXT, id TEXT, revision INTEGER NOT NULL, stage TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL, lease TEXT, lease_until REAL, actor TEXT, attempts INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'ready', PRIMARY KEY(brand,id));
        CREATE TABLE IF NOT EXISTS artifacts(brand TEXT,id TEXT,revision INTEGER,stage TEXT,actor TEXT,body TEXT,digest TEXT,PRIMARY KEY(brand,id,revision,stage));
        CREATE TABLE IF NOT EXISTS reviews(brand TEXT,id TEXT,revision INTEGER,kind TEXT,actor TEXT,digest TEXT,PRIMARY KEY(brand,id,revision,kind));
        CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY,brand TEXT,id TEXT,actor TEXT,event TEXT,at REAL);
        ''')

    def close(self): self.db.close()

    def auth(self, token, brand, capability):
        if not isinstance(token,str) or len(token)<32: raise PermissionError('Invalid credential')
        who=None
        for p in self.principals:
            if hmac.compare_digest(p['token_hash'],token_hash(token)): who=p
        if who is None or who['expires_at']<=self.clock() or brand not in who['brands'] or capability not in who['capabilities']:
            raise PermissionError('Unauthorized or expired scope')
        if brand!='sapa_wings': raise PermissionError('Brand is not enabled for pilot')
        return who['id']

    def event(self,brand,task,actor,event):
        self.db.execute('INSERT INTO audit(brand,id,actor,event,at) VALUES(?,?,?,?,?)',(brand,task,actor,event,self.clock()))

    def row(self,brand,task):
        r=self.db.execute('SELECT * FROM tasks WHERE brand=? AND id=?',(brand,task)).fetchone()
        if r is None: raise ValueError('Unknown task')
        return dict(r)

    def get(self,token,brand,task):
        self.auth(token,brand,'read'); r=self.row(brand,task)
        r.pop('lease'); r['payload']=json.loads(r['payload']); return r

    def _payload(self,brand,payload):
        if not isinstance(payload,dict) or not payload.get('brief'): raise ValueError('Brief required')
        if any(e.get('brand_id')!=brand for e in payload.get('evidence',[])): raise ValueError('Cross-brand evidence')
        self._memory(brand,payload)
        return json.dumps(payload,ensure_ascii=False)

    def _memory(self,brand,payload):
        snapshot=payload.get('memory_snapshot')
        if self.memory is not None:
            if snapshot is None: raise ValueError('Memory-backed task requires a snapshot')
            self.memory.verify_snapshot(brand,snapshot)
        elif snapshot is not None:
            raise ValueError('Memory-backed task requires a trusted memory store')

    def create(self,token,brand,task,payload):
        actor=self.auth(token,brand,'create'); body=self._payload(brand,payload)
        if not isinstance(task,str) or not task.strip(): raise ValueError('Task ID required')
        with self.db:
            self.db.execute('INSERT INTO tasks(brand,id,revision,stage,payload,digest) VALUES(?,?,1,?,?,?)',(brand,task,'research',body,seal(payload)))
            self.event(brand,task,actor,'created')

    def revise(self,token,brand,task,expected_revision,payload):
        actor=self.auth(token,brand,'revise'); body=self._payload(brand,payload)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            r=self.row(brand,task)
            if r['revision']!=expected_revision: raise ValueError('Stale revision')
            self.db.execute("UPDATE tasks SET revision=revision+1,stage='research',payload=?,digest=?,lease=NULL,lease_until=NULL,actor=NULL,attempts=0,state='ready' WHERE brand=? AND id=?",(body,seal(payload),brand,task))
            self.event(brand,task,actor,'revised_qc_revoked')

    def claim(self,token,brand,task,stage):
        actor=self.auth(token,brand,'work:'+self.owners.get(stage,'unknown'))
        if stage in ('qc','publishing'): raise ValueError('Use dedicated review or publish preflight')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE'); r=self.row(brand,task)
            if r['stage']!=stage or r['state']=='held' or (r['lease_until'] or 0)>self.clock(): raise ValueError('Task unavailable')
            if r['attempts']>=3: raise ValueError('Retry limit reached')
            lease=secrets.token_urlsafe(32)
            self.db.execute("UPDATE tasks SET lease=?,lease_until=?,actor=?,attempts=attempts+1,state='leased' WHERE brand=? AND id=?",(token_hash(lease),self.clock()+120,actor,brand,task))
            self.event(brand,task,actor,'claimed:'+stage)
            return dict(lease=lease,revision=r['revision'],digest=r['digest'],stage=stage)

    def _lease(self,r,actor,lease,revision):
        if r['actor']!=actor or r['revision']!=revision or (r['lease_until'] or 0)<=self.clock() or not hmac.compare_digest(r['lease'] or '',token_hash(lease)):
            raise PermissionError('Invalid, stale or expired lease')

    def complete(self,token,brand,task,lease,revision,stage,output):
        actor=self.auth(token,brand,'work:'+self.owners.get(stage,'unknown'))
        if stage in ('qc','publishing') or not isinstance(output,dict) or not output.get('output_refs') or not output.get('evidence_refs'):
            raise ValueError('Stage evidence and output references required')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');r=self.row(brand,task)
            self._lease(r,actor,lease,revision)
            self._memory(brand,json.loads(r['payload']))
            if r['stage']!=stage: raise ValueError('Stage changed')
            body=json.dumps(output,ensure_ascii=False)
            digest=seal([r['digest'],stage,output])
            self.db.execute('INSERT INTO artifacts VALUES(?,?,?,?,?,?,?)',(brand,task,revision,stage,actor,body,digest))
            target=self.stages[self.stages.index(stage)+1] if stage!='optimization' else 'done'
            self.db.execute("UPDATE tasks SET stage=?,digest=?,lease=NULL,lease_until=NULL,actor=NULL,attempts=0,state='ready' WHERE brand=? AND id=?",(target,digest,brand,task))
            self.event(brand,task,actor,'completed:'+stage)

    def fail(self,token,brand,task,lease,revision,stage):
        actor=self.auth(token,brand,'work:'+self.owners.get(stage,'unknown'))
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');r=self.row(brand,task);self._lease(r,actor,lease,revision)
            self._memory(brand,json.loads(r['payload']))
            if r['stage']!=stage: raise ValueError('Stage changed')
            state='held' if r['attempts']>=3 else 'ready'
            self.db.execute('UPDATE tasks SET lease=NULL,lease_until=NULL,actor=NULL,state=? WHERE brand=? AND id=?',(state,brand,task))
            self.event(brand,task,actor,'failed:'+stage)

    def review(self,token,brand,task,revision,digest,kind,passed):
        if kind not in ('fact','visual','rights') or type(passed) is not bool: raise ValueError('Invalid review')
        actor=self.auth(token,brand,'qc:'+kind)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');r=self.row(brand,task)
            if r['stage']!='qc' or r['state']=='held' or r['revision']!=revision or r['digest']!=digest: raise ValueError('Stale or unavailable review')
            self._memory(brand,json.loads(r['payload']))
            writers={x[0] for x in self.db.execute('SELECT actor FROM artifacts WHERE brand=? AND id=? AND revision=?',(brand,task,revision))}
            if actor in writers: raise PermissionError('Author cannot review own revision')
            reviewers={x[0] for x in self.db.execute('SELECT actor FROM reviews WHERE brand=? AND id=? AND revision=?',(brand,task,revision))}
            if actor in reviewers: raise PermissionError('Independent reviewer identities required')
            if not passed:
                self.db.execute("UPDATE tasks SET state='held' WHERE brand=? AND id=?",(brand,task));self.event(brand,task,actor,'qc_failed:'+kind);return
            self.db.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?)',(brand,task,revision,kind,actor,digest))
            self.event(brand,task,actor,'qc_passed:'+kind)
            count=self.db.execute('SELECT COUNT(*) FROM reviews WHERE brand=? AND id=? AND revision=? AND digest=?',(brand,task,revision,digest)).fetchone()[0]
            if count==3: self.db.execute("UPDATE tasks SET stage='publishing' WHERE brand=? AND id=?",(brand,task))

    def publish_preflight(self,token,brand,task,revision,digest):
        actor=self.auth(token,brand,'publish_preflight')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');r=self.row(brand,task)
            if r['stage']!='publishing' or r['revision']!=revision or r['digest']!=digest or r['state']=='held': raise ValueError('Current QC seal required')
            count=self.db.execute('SELECT COUNT(*) FROM reviews WHERE brand=? AND id=? AND revision=? AND digest=?',(brand,task,revision,digest)).fetchone()[0]
            if count!=3: raise ValueError('Three QC reviews required')
            self._memory(brand,json.loads(r['payload']))
            key=seal([brand,task,revision,digest])
            self.event(brand,task,actor,'publish_rehearsal_blocked')
            return dict(task_key=key,revision=revision,digest=digest,external_writes=False,status='blocked_no_live_adapter_or_publish_authority')
