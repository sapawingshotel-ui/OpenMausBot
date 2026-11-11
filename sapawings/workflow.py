"""Offline marketing workflow; live connector receipts enter through the operator.

Role labels are routing metadata, not an authentication boundary. This module
has no network client, model engine, credential store or PMS write capability.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROLES = ('Chief of Staff', 'Marketing', 'Design', 'Research', 'Hotel Operations', 'Revenue', 'Quality Control')
ALLOWED = {'draft': ('researched', 'Research'), 'researched': ('designed', 'Design'), 'designed': ('qc_passed', 'Quality Control')}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def qc_errors(post):
    errors = []
    if not all(isinstance(post.get(k), str) and post[k].strip() for k in ('vi', 'en', 'alt')):
        errors.append('Vietnamese, English and alt text are required')
    asset = post.get('asset', {})
    if asset.get('origin') != 'real_photo' or asset.get('reviewed') is not True:
        errors.append('A visually reviewed real photo is required')
    if not asset.get('source') or not asset.get('sha256'):
        errors.append('Photo provenance and checksum are required')
    if asset.get('archive') and not (post.get('archive_disclosed') is True and 'ảnh lưu trữ' in post.get('vi', '').lower() and 'archive photo' in post.get('en', '').lower()):
        errors.append('Archive disclosure must appear in both captions')
    if asset.get('room_type_ambiguous') and post.get('room_type_claim'):
        errors.append('Ambiguous photo cannot support a room type claim')
    if not post.get('sources'):
        errors.append('Research sources are required')
    for claim in post.get('claims', []):
        if claim.get('status') != 'verified' or not claim.get('source') or not claim.get('checked_at'):
            errors.append('Unverified claim: ' + str(claim.get('text', '')))
        expiry = claim.get('valid_until')
        if expiry and datetime.fromisoformat(expiry.replace('Z', '+00:00')) <= datetime.now(timezone.utc):
            errors.append('Expired claim: ' + str(claim.get('text', '')))
    return errors


class Workflow:
    def __init__(self, db):
        self.db = sqlite3.connect(str(db))
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS posts(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL, seal TEXT);
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY, post_id TEXT, role TEXT, event TEXT, at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS outbox(key TEXT PRIMARY KEY, post_id TEXT UNIQUE NOT NULL, seal TEXT NOT NULL, scheduled_at TEXT NOT NULL, state TEXT NOT NULL, receipt TEXT);
        ''')

    def event(self, post_id, role, event):
        self.db.execute('INSERT INTO events(post_id,role,event,at) VALUES(?,?,?,?)', (post_id, role, event, datetime.now(timezone.utc).isoformat()))

    def get(self, post_id):
        row = self.db.execute('SELECT * FROM posts WHERE id=?', (post_id,)).fetchone()
        if row is None:
            raise ValueError('Unknown post')
        return dict(row) | {'payload': json.loads(row['payload'])}

    def create(self, post_id, payload):
        with self.db:
            self.db.execute('INSERT INTO posts VALUES(?,1,?,?,NULL)', (post_id, 'draft', json.dumps(payload, ensure_ascii=False)))
            self.event(post_id, 'Marketing', 'draft_created')

    def advance(self, post_id, role):
        with self.db:
            p = self.get(post_id)
            rule = ALLOWED.get(p['state'])
            if not rule or rule[1] != role:
                raise ValueError('Invalid state or routing role')
            target = rule[0]
            if target == 'researched' and not p['payload'].get('sources'):
                raise ValueError('Missing research evidence')
            if target == 'designed' and not p['payload'].get('design_sha256'):
                raise ValueError('Missing rendered design checksum')
            if target == 'qc_passed':
                errors = qc_errors(p['payload'])
                if errors:
                    raise ValueError('; '.join(errors))
            seal = digest(p['payload']) if target == 'qc_passed' else None
            self.db.execute('UPDATE posts SET state=?,seal=? WHERE id=?', (target, seal, post_id))
            self.event(post_id, role, target)

    def revise(self, post_id, payload):
        with self.db:
            p = self.get(post_id)
            if p['state'] in ('scheduled', 'published', 'measured'):
                raise ValueError('Use a new campaign revision and reconcile the live post first')
            self.db.execute('DELETE FROM outbox WHERE post_id=?', (post_id,))
            self.db.execute('UPDATE posts SET revision=revision+1,state=\'draft\',payload=?,seal=NULL WHERE id=?', (json.dumps(payload, ensure_ascii=False), post_id))
            self.event(post_id, 'Marketing', 'revision_invalidated_qc')

    def request_schedule(self, post_id, when):
        at = datetime.fromisoformat(when.replace('Z', '+00:00'))
        if at.tzinfo is None or at <= datetime.now(timezone.utc):
            raise ValueError('Schedule must be future and timezone aware')
        with self.db:
            p = self.get(post_id)
            if p['state'] not in ('qc_passed', 'schedule_requested') or digest(p['payload']) != p['seal']:
                raise ValueError('Current revision has not passed QC')
            old = self.db.execute('SELECT * FROM outbox WHERE post_id=?', (post_id,)).fetchone()
            if old:
                if old['scheduled_at'] != when:
                    raise ValueError('An outbox request already exists at another time')
                return old['key']
            key = digest([post_id, p['revision'], p['seal'], when])
            self.db.execute('INSERT INTO outbox VALUES(?,?,?,?,?,NULL)', (key, post_id, p['seal'], when, 'requested'))
            self.db.execute('UPDATE posts SET state=\'schedule_requested\' WHERE id=?', (post_id,))
            self.event(post_id, 'Chief of Staff', 'schedule_requested')
            return key

    def confirm_schedule(self, key, receipt):
        # A human/operator imports a connector readback; this is not API authentication.
        if not receipt.get('external_id') or not receipt.get('readback_verified') or receipt.get('draft') is not False:
            raise ValueError('A live scheduled post and verified readback are required')
        with self.db:
            row = self.db.execute('SELECT * FROM outbox WHERE key=?', (key,)).fetchone()
            if not row:
                raise ValueError('Unknown outbox request')
            p = self.get(row['post_id'])
            if p['seal'] != row['seal'] or digest(p['payload']) != row['seal']:
                raise ValueError('Revision changed')
            if receipt.get('scheduled_at') != row['scheduled_at']:
                raise ValueError('Scheduled time mismatch')
            if row['state'] == 'scheduled':
                if json.loads(row['receipt']) != receipt:
                    raise ValueError('Conflicting connector receipt')
                return
            self.db.execute('UPDATE outbox SET state=\'scheduled\',receipt=? WHERE key=?', (json.dumps(receipt), key))
            self.db.execute('UPDATE posts SET state=\'scheduled\' WHERE id=?', (row['post_id'],))
            self.event(row['post_id'], 'Marketing', 'schedule_readback_confirmed')


def summarize(rows):
    # Input must already be mapped by connector field IDs. Missing is not zero.
    fields = ('reach', 'reactions', 'comments', 'shares', 'link_clicks')
    result = {'posts': len(rows), 'scope': 'sum of per-post values; reach is not deduplicated people'}
    for key in fields:
        values = [r.get(key) for r in rows]
        result[key] = sum(values) if all(isinstance(v, (int, float)) and v >= 0 for v in values) else None
    return result
