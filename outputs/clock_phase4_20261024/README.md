# Phase 4 reproducible clock demonstration — SIMULATION

Six seeded end-to-end experiments connect optical dynamics, integrated photon counts,
blind resonance acquisition, finite-time photon feedback, the actual continuous LO
output, phase/time error and the unchanged overlapping Allan-deviation engine.
All use local axial 20 G, E=0, 297 K and seed 410024. These are synthetic predictions,
not apparatus measurements, SI accuracy validation or a validated 475 G clock.

The seven-state reference was implemented and passed 10 tests before enabling the
21-state extension (local checkpoint d9b0976; preserved seven-state tree in PR history).
The full local suite passed **123 tests**, preserving the original 91. After final
figure changes, the two export/CLI tests passed again. Ubuntu and Windows Python 3.12
CI run the full suite; their final status and run link are recorded in the PR.
Editable and wheel installations are tested from outside the checkout.

## What each folder contains

`complete_research_bundle.zip` is the complete immutable research run. It contains
all raw native-grid output frequency, N+1 phase/time boundaries, every observed
photon count and programmed timestamp, separate evaluator-only expected counts/
actual times/optical populations, acquisition fits, feedback/actuation, actual-clock
ADEV tables, parameter provenance, reference catalog/BibTeX, source snapshot,
MATLAB attribution/archive and its own complete SHA256 manifest. The larger raw
CSV files are kept inside the ZIP to avoid committing duplicate copies.

Selected tables, config/summary/metadata and every vector PDF/SVG are also directly
available in each folder. Rejected estimates stay rejected; gaps in figures retain
those rejected cycles. Useful output excludes probe dither but retains acquisition,
latency and loss-of-lock time. `locked` column prefixes mean feedback enabled, not
a certification of lock. Lock detection uses counts and estimated uncertainty only.

## Results

| Case | Record (s) | Observed lock | Largest plotted tau (s) | Feedback ADEV | Free ADEV |
|---|---:|---:|---:|---:|---:|
| Seven-state Lindblad | 31.614 | 98.6% | 3.160 | 1.3052e-06 | 7.6350e-06 |
| 21-state rate, N=1000 | 31.614 | 98.6% | 3.160 | 1.4610e-06 | 7.6350e-06 |
| Excessive integral gain | 16.224 | 0.0% | 1.622 | 9.1956e-05 | 3.9161e-06 |
| Long feedback latency | 16.226 | 0.0% | 1.622 | 3.9236e-05 | 3.9161e-06 |
| Insufficient photons | 8.528 | 0.0% | 0.852 | 2.0562e-06 | 2.0562e-06 |
| Quieter oscillator | 31.614 | 98.6% | 3.160 | 1.5655e-06 | 9.5642e-08 |

These are full-record values, not a chosen best-lock segment. The secondary fixed
window starts at the predeclared 2 s; its full curve is exported separately. Each
curve retains drift and all samples; tau is limited to one tenth of the record.
Different record lengths have different largest tau and should not be compared as
identical averaging times. ADEV improves at long tau in the deliberately drift-heavy
10 kHz/s examples but worsens over shorter tau. In `low_drift`, the same loop locks
but injects photon noise into a quieter 100 Hz/s LO. No gain/latency setting is
selected using hidden errors. Poor-gain, latency and low-count failures are retained.
The 21-state run assumes 1000 independent centers/linear detection; it uses the rate
solver benchmarked against Lindblad, not a claim of general rate-model exactness.

## Estimator and optical validation

The two successful examples each include 100 matched-family acquisition/tracking
trials (seed 411) and 40 independent Lindblad-spectrum acquisition trials (seed 412)
at their actual gate/detector settings. Their means/true targets are available only
to the offline evaluator. Production estimation sees observed counts and public
commands/timing; no oracle correction is used.

- **7 states:** matched acquisition bias 1.119 kHz, nominal-95% interval coverage 97.0% (100/100 accepted); physical-spectrum bias -2.986 kHz, coverage 85.0% (40/40 accepted). Actual-loop fixed-window tracking RMSE 28.78 kHz, empirical coverage 97.0% (493 accepted cycles).
- **21 states:** matched acquisition bias 0.025 kHz, nominal-95% interval coverage 92.0% (100/100 accepted); physical-spectrum bias -4.050 kHz, coverage 92.5% (40/40 accepted). Actual-loop fixed-window tracking RMSE 25.44 kHz, empirical coverage 97.2% (493 accepted cycles).

The physical-spectrum coverage includes line-family mismatch, line pulling and
finite trials. In particular 85% coverage in the seven-state sample does **not**
validate a nominal 95% guarantee. Matched-family confidence and actual-loop tracking
coverage do not establish universal physical-model coverage. Published optical-rate
uncertainty is not included. Calibration uncertainty propagation is first order;
tracking is quasi-static within a finite ABBA measurement cycle.

`optical_backend_comparison` tests sequential 1/10 ms gates against exact Lindblad
emissions. `driven_counting_reference` exports exact seven-electronic-state jump
variance and adjacent-gate covariance. Long records still use a qualified Poisson
approximation, not exact quantum trajectories. Numerical tests cover full/restricted
Lindblad equality, trace/positivity, noise/phase identities, local-clock gate timing,
causal latency, count-only interfaces, bias/coverage, failures, provenance and packaging.
All 26 PDF figures were rendered and visually inspected.

## Reproduce

Use Python 3.12, select that same interpreter in VS Code, then run from the repo root:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/run_clock.py --config examples/clock_7.json --validation-trials 100 --physical-trials 40 --out outputs/NEW_CLOCK7
python scripts/run_clock.py --config examples/clock_21.json --validation-trials 100 --physical-trials 40 --out outputs/NEW_CLOCK21
python scripts/run_clock.py --config examples/clock_high_gain.json --out outputs/NEW_HIGH_GAIN
python scripts/run_clock.py --config examples/clock_latency.json --out outputs/NEW_LATENCY
python scripts/run_clock.py --config examples/clock_photon_starved.json --out outputs/NEW_LOW_COUNTS
python scripts/run_clock.py --config examples/clock_low_drift.json --out outputs/NEW_QUIETER_LO
```

Every destination must be fresh. Seeds/configuration reproduce the synthetic data;
Git IDs, timestamps and PDF metadata describe the actual run and can differ on a
rerun. Floating-point values may differ slightly across BLAS/platforms. CI and these
runs limit OPENBLAS_NUM_THREADS, OMP_NUM_THREADS and MKL_NUM_THREADS to 1, which also
avoids excessive overhead for the small optical matrices. The installed
`diamondclock-clock` entry point accepts the same options outside the checkout.

The archived calculations record their actual local calculation commit 4899576 and
source bytes. Publication via GitHub creates different commit IDs; the captured
source snapshot and SHA256 values remain authoritative for each calculation.
New output files do not replace earlier research datasets. No PR is merged and no
Streamlit deployment is performed.

## Remaining physical assumptions

The optical rates are published fitted parameters; LO spectra/drift, detector size/
efficiency, private sample shift, measurement protocol and controller gains are
simulation assumptions. The 21-state optical extension retains the Phase 3 secular
nuclear-channel approximation and original nitrogen-14 ground Hamiltonian. Missing
apparatus validation includes laser/field/temperature fluctuations, sample/rate
uncertainty, detector nonlinearities/dead time, full excited/singlet nuclear dynamics,
measured LO spectrum including flicker, analog actuator/divider/synthesizer noise,
reference aging and SI calibration. The low-field single-transition loop does not
validate the original 475 G electronic/nuclear composite configuration. See
[clock methods](../../docs/CLOCK_METHODS.md),
[validation](../../docs/CLOCK_VALIDATION.md) and the Paper Bucket equation/source maps.
