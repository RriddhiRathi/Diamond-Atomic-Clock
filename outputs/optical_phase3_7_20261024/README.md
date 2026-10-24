# Phase 3 7-state optical measurement example — SIMULATION

Numerically generated on 2026-10-24. Not an experimental spectrum or clock result.
Reproduce: `python scripts/run_optical.py --config examples/optical_7.json --out outputs/NEW_PATH`.

The 81-frequency CW scan contains 162 paired MW-off/on acquisition gates, each
1 ms, plus expected/detected counts, every optical-state population, timing and
seeds. Nominal 297 K, axial 20 G, pump 2 million/s, Rabi 200 kHz, 100 independent
centers, detection efficiency 0.01 and root seed 310024. Fast counts are labeled
Poisson approximations. Expected maximum contrast on this grid is
12.452716%; it is not a fitted resonance.

Also included: 101-point pump initialization, 13 pump-response settings (electronic
reference), 18 solver benchmarks, three selected-model comparisons and 8192
number-resolved reference trials in two counting scenarios. Those seven-state
counting-reference scenarios/seeds are shared by the 7- and 21-state examples;
they are not independent experimental replications. Four SVG/PDF figure pairs
show spectrum/contrast, populations, pump response and photon statistics.

Validation: **91 tests passed on Linux/Python 3.12.14**, including the original 56.
The first seven-state stage passed five tests before extension. Eight exported
PDFs across both examples were rendered with Poppler and visually inspected.
The initial-state caption was separately checked after its final clarification.
No clipping or overlapping labels remained. The source snapshot records local
commit 8d764fa plus the dirty working tree at calculation time, not a later PR
publication commit. Core source bytes and complete parameters are captured.

`research_bundle_SIMULATION.zip` is the complete run, with its own checksums,
source snapshot, methods, equation mapping, environment, references (including
any persistent unverified user entries) and original MATLAB attribution archive.
Files alongside it are the convenient top-level view; this directory's separate
SHA256 manifest covers that view and the ZIP. Existing results are unchanged.

Scope: single local axial NV, 5–50 G, E=0, nominal room temperature 297 K.
Published fitted optical rates are for Tetienne NV E. Detector, laser, microwave
and ground relaxation inputs are assumed; their uncertainty is not propagated.
21-state optical channels are secular and omit excited/singlet nuclear dynamics.
475 G is rejected. There is no resonance estimator, feedback servo, clock-output
simulation or new experimental accuracy/stability claim.
