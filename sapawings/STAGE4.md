# Stage 4 — transitive undici remediation and real-photo carousel draft

Date: 2026-11-11. OpenMausBot runtime remains disabled.

## Targeted dependency changes

Update locked undici 6.28.0 → 6.29.1 and 7.29.0 → 7.30.1, alongside the prior root 8.12.2 update. Registry metadata confirms unchanged Node engine requirements and no dependency children for each old/new pair. Exact new integrity values come from npm. Matching snapshot edges and keys were updated, with explicit same-major pnpm overrides (`undici@>=6 <7`, `undici@>=7 <8`) in workspace configuration and lockfile metadata. No other package resolution changed. This is a targeted lock edit, not a claimed pnpm-generated or installed lockfile.

A fresh complete-lockfile public npm advisory query, semver filtering and package+URL deduplication returned **28 package–advisory pairs (17 high, nine moderate, two low)**, versus 46 previously. There are no matching advisory ranges for the three selected undici versions. `STAGE4_SCAN.json` contains current findings. The earlier dependency scan/path files remain historical snapshots, not the new graph.

These are declared-version findings, not exploitability or compromise claims. Remaining affected packages include dev/build as well as runtime paths. No lifecycle scripts, package code, upstream fixture, frozen install, build or runtime compatibility tests were executed. Overrides must be validated against parent-package behavior in a disposable environment. Do not start OpenMausBot or merge based only on the lowered count. Remediate/triage the remaining findings, validate the frozen lock with lifecycle scripts disabled, rescan and then qualify the isolated upstream fixture.

## Actual marketing output

Produced a private draft of the three-slide Sa Pa Wings stay-enquiry carousel, 1080×1350 per slide, with Vietnamese/English copy, a real archived hotel photograph, archive disclosures, editable self-contained SVG sources, PNG exports, bilingual caption and font license. The photograph was resized/re-encoded for layout and cropped through SVG; facilities were not generated or reconstructed. The original source checksum is retained privately. No real media or private source URLs were added to this public repository.

Rendered all slides and a three-panel contact preview. Programmatic checks verify dimensions, all 36 text lines fit the intended horizontal bounds and used fonts contain the actual Unicode glyphs. Font: DejaVu Serif/Sans, redistribution notice included. The image-output inspection channel was unavailable in this run, so **fresh visual inspection remains pending**. Programmatic checks do not prove aesthetics, diacritic placement, image cropping or readability. Comprehensive photo rights review also remains pending. The assets are a draft, not publish-ready.

A Work operator attached real output references/hashes to the existing memory-bound task and advanced its handoffs to QC. Research scope was first-party information plus a documented evergreen fallback, not fresh trend discovery. This was manual operator work in Work, not a running team of external models. No independent QC approvals were fabricated. All three reviews remain pending; no publication request or schedule change was made. The local queue still checks the memory snapshot, but does not automatically re-hash external artifact files at publication: the future adapter must do so.

## Validation and limits

51 existing standard-library tests still pass. No new tests were added merely to mirror this low-impact artwork or configuration edit. Static YAML comparison checked the two version/integrity/edge changes before adding the explicit matching overrides; workspace and lockfile override maps agree. Native application compatibility remains untested.

Private deliverable package contains editable SVGs, PNGs, caption, resized photo, checks and license. Private task/memory databases are not included. The package is review material; no implied commercial photo-rights grant or publication authorization is created.

Next: review the real render, resolve rights from existing asset evidence, remediate remaining dependency branches and qualify the upstream fixture before any autonomous service. Model connection and publishing authorization must be scoped when an executable integration is ready; PMS stays untouched.
