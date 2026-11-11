# Static security review — 2026-11-11

Reference: sapawingshotel-ui/OpenMausBot main head observed at 613ed01fdc2b04860ef63e3dbdcb46d7e6b1666d, package 0.1.152. Documentation/source fetched in this session; not a full repository or dependency audit. No upstream code, install scripts, package hooks, downloaded desktop binary or model runtime was executed.

## Reviewed surfaces and findings

- `package.json`: prepare invokes `scripts/install-git-hooks.mjs`; packaging includes binary preparation/download scripts. Do not run a blanket install before dependency, lockfile and download-provenance review.
- `scripts/install-git-hooks.mjs`: uses execFileSync rather than shell concatenation; changes repository core.hooksPath on install. Avoid install lifecycle scripts in the first dependency inspection.
- `SECURITY.md` and `server/request-auth.ts`: documented session-less loopback Slack worker route risk. Do not enable shared Full access or Slack worker integration for this rollout. Loopback is not a sandbox for agents with shell access.
- `docs/team-sharing.md`: imported package bots use workspace defaults, described as Full access outside hosted company workspaces. README says imports are Ask. Treat the discrepancy as significant; use an explicit headless manifest with approval ask and verify actual imported state.
- `docs/self-hosting.md`: some credentials remain plaintext; safety floor and loop guard require configuration and are not a complete sandbox. Do not expose the harness publicly or store credentials in configuration committed to git.
- `docs/mcp-server.md`: bounded control plane exists, but requires an independently running workspace/session for mutations. Current ChatGPT connectors do not establish this session.
- `AGENTS.md` and `docs/verification/README.md`: upstream server/conversation changes require an isolated fixture. This contribution only adds an offline module and a manifest; it does not modify upstream server/conversation code or claim that integration works.

## Current controls

No upstream execution; no model credentials; no network access in local workflow; no PMS writer; no user-data files in public source; seven bots explicitly Ask, computer off and browser disabled. Routines are not provisioned. These are startup defaults, not a complete production permission policy. A real connector adapter must enforce its own authentication and least privilege.

## Release gate

Before live deployment: pin the exact release/commit; inspect complete dependency lockfile and native download scripts; run upstream isolated fixture and team dry-run; check seven bot permissions; authorize engine and app connections; test prompt-injection resistance, read/write boundaries, duplicate remote creates and revision invalidation; use a protected persistent host with logs, resource limits and recovery. Do not enable broad Full access to avoid ordinary approval prompts.

A static pass is not a security certification. Outstanding limitations are deployment blockers, not reasons to ask the owner to resend existing assets.

## Phase-1 agency extension

The expanded catalog/planner is standard-library-only and has no upstream imports, credentials, shell calls, network or publish methods. Brand isolation and fail-closed rehearsal policy are preflight checks, not authenticated authorization. The legacy workflow is still single-brand; never route the three inactive brands through it. See ARCHITECTURE.md for the sampled review of ShortGPT, Editly and the two skill repositories. None was installed or executed; dependency/lockfile and runtime security review remains outstanding.
