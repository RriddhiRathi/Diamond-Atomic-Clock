# Phase 4 validation record

The seven-state clock was implemented first. Its initial 10 tests passed before
21-state support was enabled (local checkpoint d9b0976). These included exact restricted/
full Lindblad evolution, phase/frequency/time identities, end-to-end seeded photon
feedback, count-only acquisition/tracking, profile intervals, interface isolation,
controller sign, saturation, lock counters and deterministic unstable gains.
The final test count and Ubuntu/Windows CI result are recorded in the PR and demo README.

New tests cover the 21-state transient rate/Lindblad comparison; matched acquisition
and tracking coverage with independently sampled calibration counts; physical Lindblad
spectral-model bias; actual clock phase driving the existing Allan engine; constant
frequency error vs time error; white FM and phase-noise normalization; LO-derived
true gate duration; causal actuator latency; driven photon variance and adjacent-gate
covariance; gain/latency/photon failures; zero-gain unlocked equivalence; domain and
475 G rejection; seeding; all existing scientific/historical regression checks;
CLI/dashboard interactions; config/source/data tamper rejection; editable and wheel
imports/resources/run/export outside the source checkout on Ubuntu and Windows.

Validation datasets are separate:
- matched_estimator_validation: ideal empirical line family, independent calibration
  and tracking draws, randomized hidden centre/detuning. Acquisition MC uses Fisher/
  Wald intervals (production acquisition also profiles); tracking total intervals
  include first-order calibration shape uncertainty. Bias/coverage are empirical,
  not hard-coded to zero/95%.
- physical_estimator_validation: means from actual Lindblad optical spectra;
  estimator sees only sampled counts. Error to an independently assigned Hamiltonian
  transition includes model discrepancy/line pulling. No oracle bias correction.
- optical_backend_comparison: sequential gate-integrated emissions vs exact reduced
  Lindblad, including preparation and switching, no per-gate steady-state resets.
- driven_counting_reference: factorial counting moments and adjacent-gate covariance
  of the quantum optical model; not only the Phase 3 microwave-off histogram.

These finite tests do not validate every point in the accepted configuration box.
Long records use a labeled Poisson gate approximation. Reference quantum moments
quantify residual overdispersion/correlation but are not a full experimental noise
budget. Coverage tests include accepted/rejected counts; rejected results are recorded
rather than replaced with truth. Model-mismatch bias can remain.

Reproducible default and failure configurations are under examples/clock_*.json.
The demonstration combines acquisition and feedback, useful-output frequency/phase/
time error and full-record/fixed-window ADEV. Poor settings need not lock, and locked
output can be worse than unlocked at some averaging times. All plots carry simulation
labels and complete input files. Source snapshots record the calculation's actual
Git/dirty state, not a later publication commit. No historical result is regenerated.

An additional low-drift example retains ordinary controller gains and adequate
photons. It tests the distinction between successful lock and improved stability;
feedback noise can dominate a quieter free oscillator. Actual-loop estimator error
and nominal-interval coverage are exported separately from matched-model trials.
