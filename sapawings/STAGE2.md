# Stage 2 — persistent rehearsal queue and dependency gate

Date: 2026-11-11. Upstream reference: `613ed01fdc2b04860ef63e3dbdcb46d7e6b1666d`.

## Implemented and verified locally

`task_store.py` adds a SQLite task/artifact/review/audit store, brand-scoped queries, bearer authentication against a trusted principal registry, capability and expiry checks, atomic lease claims, 120-second leases, bounded retries, optimistic revision checks and output hash chaining. Completion requires references but does not establish their factual truth. Three distinct reviewers must sign the same revision; authors cannot review their own artifacts. Revision changes invalidate active leases and QC. Status and audit rows never include raw bearer or lease values. Database files use mode 0600.

The publication method only evaluates a preflight and returns `external_writes=false`, with a deterministic task key. No network adapter, provider target, publish grant API, model dispatcher, HTTP listener or PMS access is present. There is no method to advance publishing into analytics: actual publication and receipt integration must be built first. Existing `workflow.py` is still a separate legacy pilot.

Authentication is meaningful at this library boundary only: trusted host code supplies the registry and calls methods with the worker's bearer. It is not an OS security boundary. A worker sharing the Python process, registry, arbitrary SQL handle or database filesystem can bypass it. Deploy with separate worker processes, no database mount for workers, an authenticated service boundary, protected registry and credential rotation/revocation. Do not expose `TaskStore.db` or trusted setup to models. The module does not claim authenticated network gateway deployment, cross-process sandboxing, global concurrency enforcement, rate limiting or immutable audit storage.

## Dependency findings and fixture decision

Fetched source without executing repository code or lifecycle hooks. Installed no upstream dependencies. The read-only server/shared/scripts inventory has 3,391 source/config files, about 40 MB; this inventory is not a review of all files. Node 24 is available locally. Reviewed the upstream fixture launcher and its temporary home, fake engine, allowlisted child environment, explicit URL and cleanup design. No live app was contacted.

Parsed the complete `pnpm-lock.yaml`: 1,188 package entries, each with an integrity value, no non-registry resolution detected. There are three workspace importers and 56 direct runtime plus 23 direct development dependencies in the root manifest. Workspace build permission allows Electron and esbuild lifecycle scripts; the root `prepare` installs git hooks. No `requiresBuild` fields in this lockfile does not imply no install scripts.

Queried npm's public bulk advisory endpoint using only public package names and locked versions, filtered ranges with the installed semver library, and deduplicated by package plus advisory URL. See `dependency_findings.json`: **46 package–advisory pairs across 12 package names: 23 high, 18 moderate, 5 low**. There were 68 matching package/range records before deduplication. Multiple ranges/versions and related advisories must not be counted as separate exploited defects.

Findings include the root runtime `undici@8.11.2` (eight matching advisories), older transitive undici branches, Electron, Vite/Vitest, XML parsing and rendering/build dependencies. `zod@4.4.3` is matched; do not incorrectly flag the root `zod@4.6.7` for the same range. These counts combine runtime, build and development dependencies. Reachability/exploitability and patched-version compatibility have not been assessed; the scan does not establish compromise or an exploit in this application. Future scans can change.

**Decision: block upstream installation and fake-engine fixture execution pending remediation/review.** This is the implemented project security gate, not a request to bypass it. Do not ask the owner to approve execution of known unresolved findings merely to finish a demo. First trace impacted dependency paths, verify advisory fixes against maintainer sources, prepare compatible version changes and regenerate the lockfile without lifecycle scripts, then rescan and test in a disposable environment. Do not blanket override every package across major versions. In particular, native Electron/rendering dependencies require separate compatibility tests.

No fixture launch, team import, model turn or upstream server behavior has been verified. This stage changes only the `sapawings/` extension and documentation, so its local tests do not require claiming a server/conversation change works under upstream AGENTS.md.

## Existing-artifact rehearsal

`rehearsal.py` accepts an operator-selected private campaign input and state directory. It checks the actual source/photo/render hashes, replays handoffs over existing artifacts, persists two tasks at QC, and refuses to reuse a task if its inputs or media changed. It neither creates new copy nor proves research/trend analysis was freshly performed. All three semantic/visual/rights reviews remain pending. Tokens are generated in memory and are not written to the output. The report contains no token.

The local run used the two previously prepared boutique posts and real hotel photo/render files. Ran it twice: same task revisions and digests, two QC-pending tasks, zero model calls, zero publication calls. It did not alter their existing live Metricool schedules. Private inputs, source references, database and result JSON remain outside GitHub.

## Verification and next work

38 standard-library unittest cases passed: 22 prior tests, 14 task-store tests and two rehearsal tests. They cover scoped authentication/expiry, incorrect capability, cross-brand evidence, concurrent database connections, lease reclamation, stale completion, three-failure hold, revision revocation, QC separation, author self-review refusal, no credential in status/audit, persistence and changed-media rehearsal refusal. These are local boundary tests, not a penetration test or live multi-agent proof.

Commands from repository root:

```bash
python3 -m unittest discover -s sapawings/tests -v
python3 sapawings/rehearsal.py --inputs /PRIVATE/campaign_inputs.json --state-dir /PRIVATE/rehearsal
```

Keep private state in an operator-owned directory, never the public repository. This script expects the prior campaign format and `BOUTIQUE-N.png` beside it; it is a bounded rehearsal utility, not a general publishing CLI.

Next: dependency remediation with verified compatibility; isolated upstream fixture; authenticated service/process separation; vetted model and read-only tool adapters; approved brand/rights review; one true brief-to-QC pilot; dashboard and installed skill packages. Canva connection, model/hosting access or spending should be requested only when their specific implementation is ready for review. No new permission is needed to continue source review or local code.
