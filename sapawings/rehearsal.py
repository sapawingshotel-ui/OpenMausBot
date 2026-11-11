"""Replay existing reviewed artifacts through local handoffs; leave QC pending."""
import argparse
import hashlib
import json
import secrets
import time
from pathlib import Path
from task_store import TaskStore,token_hash


def run(inputs,state_dir):
    root=Path(state_dir);root.mkdir(parents=True,exist_ok=True,mode=0o700);root.chmod(0o700)
    source=Path(inputs);posts=json.loads(source.read_text())
    caps={'chief':['read','create']}
    stage_roles={'research':'research_2','trends':'research_1','brief':'content_1','script':'content_3','production':'creative_1'}
    for rid in stage_roles.values():caps[rid]=['work:'+rid]
    tokens={name:secrets.token_urlsafe(32) for name in caps}
    registry=[dict(id=name,token_hash=token_hash(tokens[name]),brands=['sapa_wings'],capabilities=cap,expires_at=time.time()+900) for name,cap in caps.items()]
    store=TaskStore(root/'tasks.sqlite',registry)
    result=[]
    try:
        for i,post in enumerate(posts,1):
            photo=Path(post['photo']);image=source.parent/('BOUTIQUE-'+str(i)+'.png')
            hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (photo,image)}
            payload={'brief':'Rehearsal using existing boutique artifacts; no new content generation or publication',
                     'vi':post['vi'],'en':post['en'],'alt':post['alt'],
                     'evidence':[{'brand_id':'sapa_wings','source':post['source'],'archive':True}],
                     'asset_hashes':hashes,'mode':'existing_artifact_handoff_rehearsal'}
            task='boutique-rehearsal-'+str(i)
            existing=store.db.execute('SELECT id FROM tasks WHERE brand=? AND id=?',('sapa_wings',task)).fetchone()
            if not existing:store.create(tokens['chief'],'sapa_wings',task,payload)
            current=store.get(tokens['chief'],'sapa_wings',task)
            if current['payload']!=payload: raise ValueError('Existing rehearsal inputs changed; an authorized revision is required')
            for stage,owner in stage_roles.items():
                if current['stage']!=stage:continue
                lease=store.claim(tokens[owner],'sapa_wings',task,stage)
                store.complete(tokens[owner],'sapa_wings',task,lease['lease'],lease['revision'],stage,
                  {'output_refs':[str(image) if stage=='production' else str(source)],'evidence_refs':[post['source']],
                   'checks':'existing artifact references only; semantic/visual/rights QC remains pending','asset_hashes':hashes})
                current=store.get(tokens['chief'],'sapa_wings',task)
            result.append({'task_id':task,'stage':current['stage'],'revision':current['revision'],'digest':current['digest'],'qc':'pending_three_independent_reviews','external_writes':False})
        report={'mode':'local_existing_artifact_rehearsal','model_calls':0,'live_publication_calls':0,'tasks':result}
        target=root/'rehearsal-result.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2));target.chmod(0o600)
        return report
    finally:store.close()


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',required=True);ap.add_argument('--state-dir',required=True);args=ap.parse_args()
    print(json.dumps(run(args.inputs,args.state_dir),ensure_ascii=False,indent=2))
