# Sa Pa Wings AI — Marketing foundation

Seven role configurations for OpenMausBot and a separately tested local marketing workflow. The workflow records Research → Design → Quality Control, invalidates QC on edits, creates an idempotent schedule outbox, and accepts a verified connector readback before marking a post scheduled.

This is a first implementation, not a deployed autonomous service. `workflow.py` performs no model calls or network requests. Role strings are routing labels, not authentication. An operator must actually inspect evidence: checks cannot prove captions are factually complete or a photo belongs to the hotel. Scheduling requests do not publish anything.

## Verify without dependencies

From this directory:

```
python3 -m unittest discover -s tests -v
```

Tests use temporary SQLite databases and synthetic data. No PMS, credentials or live app is touched. The upstream server has not been installed, executed or end-to-end tested by these tests.

## OpenMausBot configuration

`team.json` follows the `version: 1` headless team format in `docs/headless-cli.md` of the reviewed repository. It explicitly sets approval `ask`, computer `off`, browser `false`; it declares no engine, keys, routines or connections. It does not import via the portable `.openmaus.json` route, whose permissions use workspace defaults.

On a separately installed, reviewed and isolated OpenMausBot workspace, use an explicit server URL to inspect the proposed change:

```
openmausbot team apply sapawings/team.json --dry-run --url http://127.0.0.1:REVIEWED_PORT
```

Replace REVIEWED_PORT with the fixture's exact port. Do not point this at a live workspace for testing. No model is pinned: select an exact available model after authenticated runtime setup. Do not use `--prune`. Verify all seven bots retain Ask and have no computer access before real work. This dry-run command has not been run in the current environment; only JSON structure and the local workflow tests have been verified.

## Connection boundaries

GitHub, Drive and Metricool available in ChatGPT are not automatically inherited by OpenMausBot. Configure and authorize its own connections separately. Never export ChatGPT tokens, guest data, banking details, raw analytics or private Drive identifiers into this public repository. Keep runtime snapshots outside this folder and out of git.

## Marketing operations

1. Research records current facts, dates and sources.
2. Marketing writes bilingual copy and a single CTA.
3. Design composes reviewed real images with boutique typography and legible archive notes.
4. QC reviews the exact text and design revision. An edit revokes the pass.
5. Chief of Staff enqueues a timezone-aware future schedule, within granted authority.
6. A live adapter/operator sends it once, reconciles uncertain responses by checking provider state, and records readback. Never blindly retry a remote create.
7. Measurement joins published posts by external ID and date; missing metrics remain null, post reach totals are explicitly not unique audience, and actual enquiries/bookings require a separate attribution source.

## Rollout

- Phase 1: configuration, security review, local state machine, real-photo designs, content pack and measured baseline.
- Phase 2: isolated upstream fixture, model login, least-privilege connectors, exact-revision QC and draft-only rehearsal.
- Phase 3: approve live scheduling scope, small campaign, verify publication and metrics.
- Phase 4: opt-in background service, bounded routines, budgets, audit and recovery. Hotel Operations and Revenue stay read-only until explicitly expanded.
