# Provenance and persistent references

New dashboard and CLI runs capture source bytes before calculation, configuration,
physical coefficients, UTC capture time, and Git commit/working-tree state. Exports
contain these bytes under `source_snapshot/`, their SHA-256 hashes, the actual
reference catalog, and bundle checksums. Git commit alone is not a clean-tree claim.
Dependency versions are recorded, not a fully locked execution environment.

The dashboard cache includes the current source fingerprint. Source changes after
capture reject export. Source changes within a running process require restarting
the app/CLI, avoiding a snapshot of new files paired with already imported code.
Legacy callers of `export_files` without a capture remain supported but explicitly
record `capture_stage=export_only` and `computation_source_verified=false`.
This field attests source capture/binding, not experimental validation or independent
certification of arbitrary caller-provided arrays. Use the app or CLI for bound runs.

The CLI refuses an existing output directory, including an empty one. Use a fresh
path for every run, e.g. `python scripts/run_simulation.py --out outputs/run-20261020-a`.
The helper `verify_files` verifies exported bundle members against SHA256SUMS.txt.
Checksums detect corruption; they are not digital signatures.

## Historical baseline

Everything under `outputs/` and the root `PROJECT_SHA256SUMS.txt` is preserved from
commit d0889da26ca05ebd2d5d36d8ec27a8ea0a6f7dee. The original manifests are historical
records, not regenerated checksums for this branch. Their Git blob IDs are recorded
in `provenance/historical_baseline.json` and protected by a regression test.

The prior review identified stale source hashes in demo metadata for app.py,
diamondclock/__init__.py, diamondclock/reporting.py, references/sources.json, and
docs/METHODOLOGY.md. Demo bundle checksums also disagree for metadata.json,
sources.json, and METHODOLOGY.md. The physics, simulation, and stability modules
matched the recorded source hashes in that review. These discrepancies are not
repaired by rewriting the old outputs and do not establish the precise execution
history of those results. New run provenance does not retroactively certify them.
Historical numerical results have not been recomputed for this change.

## Paper Bucket

User entries are stored in SQLite at `user_data/references.sqlite3`, ignored by Git.
Set `DIAMONDCLOCK_REFERENCE_DB` to a persistent, writable absolute path on hosted
installations. An ephemeral hosted filesystem loses data when replaced. Back up
the database or download JSON/BibTeX. All sessions on one installation share this
catalog; there is no per-user authentication or automatic cross-installation sync.
Storage errors are shown and disable reference/run downloads rather than silently
exporting an incomplete catalog.

A DOI is only an identifier. DOI syntax and HTTP(S) URL syntax are checked; no
network or peer-review verification is performed when adding a paper. New papers
are always unverified and unmapped, including when a submitted object contains
verification fields. Repository-curated records display their previously recorded
review date; this change does not claim a fresh literature review. MODEL is labeled
as assumptions/numerical methods rather than a verified publication.

Both standalone JSON/BibTeX downloads and new run ZIPs include saved user entries,
verification labels, notes, and DOI-less source URLs. A separate snapshot retains
the original curated bibliography used for equation and parameter mappings.
Adding a reference never changes physical coefficients, equations, benchmarks,
or the simulation engine. Promotion to a curated equation/parameter source requires
a reviewed repository change with original-paper locators.
