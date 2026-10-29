# Unified clock results — dashboard Part 4

The dashboard presents completed Phase 4 outputs without altering any solver,
coefficient, frequency/phase convention or Allan-deviation calculation. All results
are **SIMULATION**, not experimental NV-clock performance or SI accuracy.

## One experiment and its evidence

Clock Overview reads the last successfully completed current-session clock result.
It does not run a simulation. Its compact cards show the observed lock fraction,
public nominal frequency in GHz, feedback endpoint time error in µs, paired feedback
and free-running fractional-frequency Allan deviations, and their dimensionless
ratio. Both ADEV cards identify the same averaging time: the longest valid matched
full-record τ. This is a transparent display choice, not selection of a best value.
The conclusion uses **all** available matched τ points. Configuration, optical
backend, field, temperature, gate, seed, requested/completed cycles, record duration
and free-running endpoint error accompany the cards. Missing values are unavailable.

The empty state offers configuration or existing saved experiments. Three workflow
links lead to NV/ODMR, clock evidence and Advanced Research. The Part 3 phenomenological
ODMR demonstration is educational and independent of the Phase 4 optical-count loop;
its slider is not a clock lock measurement.

Clock Performance offers a current-session run or a verified historical example.
Demonstration Mode shows the five evidence sections without simulation controls.
Research Mode retains the original seven/21-state configuration form inside an
expander, every diagnostic table, configuration/source metadata, Paper Bucket-backed
export, full research ZIP and individual original SVG/PDF figure downloads.
Advanced Research → Frequency lock retains the same workspace and state.

1. **Acquisition:** actual simulated photon counts versus commanded probe offset;
   count-fitted centre, reported sigma and nominal 95% profile interval when accepted.
   Rejected acquisitions retain their reason. Multiple acquisition attempts are
   selectable. Offsets are relative to the controlled carrier, not absolute frequency.
   The separate offline-validation expander labels the public nominal and private
   Hamiltonian target explicitly. Neither private target nor expected counts are
   supplied to the estimator.
2. **Frequency correction:** paired engine oscillator outputs minus the public
   nominal frequency (kHz) on true simulation time. A separate chart uses local-clock
   timestamps for count-derived detuning estimates, reported 1σ and observed lock
   flags. Invalid estimates remain gaps. The zero line denotes public nominal,
   not an independently measured or inferred Hamiltonian resonance. Probe dither
   remains excluded from useful output.
3. **Phase/time:** the engine's N+1 phase boundaries include the exact final endpoint.
   Phase is in radians, time error in µs. Positive time error means the simulated
   clock leads nominal; the existing integration convention is unchanged.
4. **Allan deviation:** primary full-record curves and a separately selected secondary
   fixed window beginning at the predeclared configuration time. Both retain drift;
   the full record includes acquisition and failures. Log axes plot only finite,
   positive values with valid pair counts (where supplied). Duplicate method/τ
   rows are ambiguous and excluded. No interpolation, extrapolation or fit is used.
5. **Interpretation:** observed lock, final-cycle lock/loss, record timeout, the whole
   matched stability comparison, endpoint errors and the optical/count/controller
   assumptions. Lock detection is not proof of improved frequency stability.

## Stability comparison and conclusions

Within a **single analysis window**, exact matching τ values are joined between
feedback-enabled and free-running outputs. Their identical LO realization, native
bandwidth and contiguous sampling are established by the existing engine. Only
finite positive ADEV pairs yield R(τ) = feedback ADEV / free ADEV. R below one is
lower instability at that τ, above one is higher; equality uses relative tolerance
1e-10 to avoid labeling roundoff as an improvement. The ratio is a presentation
metric, not a new model equation. The UI lists every matched τ/ratio and lets the
reader select a point. No comparison between different windows or experiments is
inferred. Unmatched/zero/invalid values cannot support a ratio; an empty comparison
produces an explicit insufficient-evidence conclusion.

If lower and higher ratios occur in the same curve, the conclusion says the outcome
depends on averaging time. Counts of lower, higher and numerically equal points and
the sampled τ range accompany that conclusion. This does not establish a continuous
crossover location or statistical significance. Pair counts are not confidence bounds.
Lower ADEV does not establish better absolute accuracy, and a smaller finite-record
time error is not a long-term timing-performance guarantee. `locked` table prefixes
mean the feedback-enabled branch, not certification of actual lock.

## Preserved historical experiments

The six existing `outputs/clock_phase4_20261024/*/complete_research_bundle.zip`
files are read through the existing export format. The viewer verifies the complete
SHA256 manifest with `run_provenance.verify_files`, the displayed numerical-table
hashes from metadata, and captured configuration before displaying real saved CSV
values. It does not invoke a solver or fabricate cards from the README. Interactive
plots use saved arrays. Vector and complete-bundle downloads use the **original
bytes**. Full CSV data, source snapshots, references and MATLAB attribution remain
inside each ZIP. The archive records its own calculation commit and source; no
current-source provenance is substituted. Archives are not assigned to `clock_result`
or sent to the current-source exporter. Source snapshots are authoritative for the
archived calculation; this viewer is not a new numerical revalidation of those models.

Available demonstrations:

- Seven-state Lindblad and 21-state rate (1000 independent centers): observed lock,
  with stability improvement at long τ and degradation at shorter τ.
- Quieter oscillator: observed lock **with worse ADEV**, preserving the key negative result.
- Excessive gain, long latency and insufficient photons: failed-lock cases.

Historical outputs are intentionally excluded from wheels. The viewer explicitly
reports their absence outside a Git checkout; it does not silently download or
recompute them. The current-session view and original CLI/export path remain usable.

## State and provenance

Navigation, modes, window, τ and diagnostic selection never call `calculate_clock`.
Only the explicit form submission does. Cached runs reuse the original configuration
and source fingerprint. A failed new calculation keeps the last successful result.
Browser form edits do not reach Python before submission. When server-side controls
differ from a saved run, that difference is labeled; charts and exports use the saved
run's configuration. Source/configuration/protocol and numerical/summary hashes are checked
before a session result is displayed; stale, modified or incompatible results are
retained in state but not shown. Prepared exports retain their original validation
and reference-catalog checks. Session state does not persist across server restarts.

## Local run and reproducibility

Use Python 3.12 from the repository root (stop a running Streamlit process first):

```bash
git switch feature/dashboard-redesign
git pull --ff-only origin feature/dashboard-redesign
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m streamlit run app.py --server.port 8502
```

Open `http://localhost:8502`. Overview → Browse saved experiments provides immediate
evidence without recomputation. To calculate a new run, choose Research Mode →
Clock Performance → Current session run → Configure a photon-clock experiment →
Simulate photon-based clock. Prepare the research bundle explicitly when needed.
Use the same activated environment for `python -m pytest -q`.

For exact original example configurations (always select a fresh output directory):

```bash
python scripts/run_clock.py --config examples/clock_7.json --out outputs/NEW_CLOCK7
python scripts/run_clock.py --config examples/clock_21.json --out outputs/NEW_CLOCK21
python scripts/run_clock.py --config examples/clock_low_drift.json --out outputs/NEW_QUIETER_LO
python scripts/run_clock.py --config examples/clock_high_gain.json --out outputs/NEW_HIGH_GAIN
```

The original successful bundles also used `--validation-trials 100 --physical-trials 40`;
see the preserved archive README for all protocols. Those optional Monte Carlo jobs
are not launched by the dashboard. Limit OPENBLAS_NUM_THREADS, OMP_NUM_THREADS and
MKL_NUM_THREADS to 1 as in CI. Seeded numerical values can differ slightly across
BLAS/platforms; fresh run Git IDs/timestamps/PDF metadata describe that run.

Read [clock methods](CLOCK_METHODS.md), [validation](CLOCK_VALIDATION.md),
[clock equation/reference map](../references/clock_equation_map.md), and the preserved
[archive documentation](../outputs/clock_phase4_20261024/README.md). Part 4 changes
presentation only. No historical run, scientific engine, main branch, merge or
Streamlit deployment is changed.
