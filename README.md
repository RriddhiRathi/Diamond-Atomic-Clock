# Diamond Atomic Clock

DiamondClock Lab connects NV-center physics, ODMR and photon measurement to
simulated oscillator feedback and clock stability. The unified dashboard provides
**Overview**, **NV-Center & ODMR**, **Clock Performance**, **Research Tools**,
**Paper Bucket**, and **Exports & Documentation**, with no mode switch.
Experiments run only after an explicit submission. Saved scientific examples can
be inspected without recomputation.

See [dashboard use and validation](docs/DASHBOARD_UX.md),
[NV geometry](docs/NV_VISUALIZATION.md),
[ODMR integration and limits](docs/NV_ODMR_DEMONSTRATION.md), and
[clock results and reproducibility](docs/CLOCK_PERFORMANCE.md).
The scope paragraphs below describe the individual models and their assumptions.

Advanced nitrogen-14 NV-center **conditional frequency-stability simulator** with a Streamlit dashboard, Plotly exploration, traceable equations, and reproducible CSV/SVG/PDF exports. Version 0.1, prepared October 19, 2026.

**Start here:** open this entire folder in VS Code. Run everything in the VS Code terminal on your Windows computer. ChatGPT helps review physics and results; Copilot can assist with local edits. Neither is required at runtime. No API key, paid API service, external dataset, or hardware is needed.

## Windows setup (PowerShell)

Install 64-bit Python **3.12** if it is not already installed. In VS Code choose **Terminal > New Terminal**, with this project as the working folder. Use these commands one at a time:

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The dashboard opens at `http://localhost:8501`. If it does not open automatically, paste that address into your browser. Keep the terminal running. Stop with Ctrl+C. These commands call the virtual environment directly, so no PowerShell activation-policy change is needed. Later, double-click `START_WINDOWS.bat` to launch.

In VS Code use **Ctrl+Shift+P > Python: Select Interpreter** and choose `.venv\Scripts\python.exe`. If `py -3.12` fails, Python 3.12 is missing or the Python launcher is unavailable; install Python 3.12, reopen VS Code and try again. A runtime-only installation can use `requirements.txt`; tests additionally need `requirements-dev.txt`.

## First useful run

1. Open **Stability lab**. Default settings give five distinct reference signals with all noise assumptions visible in the sidebar.
2. Open **Research Paper Bucket**. Each paper has a DOI, evidence category, page/equation locator, and implementation location. The parameter table distinguishes measured coefficients from assumed environment/readout inputs.
3. Open **Compensation study**. Compare the calibrated slope, then calculate an ensemble. Increased nuclear readout noise can erase the thermal-compensation benefit.
4. Open **Export & methodology**, click **Prepare reproducible export**, and download the complete run. It includes vector SVG/PDF and all numerical inputs.

The bundled `outputs/demo` directory already contains a completed default run and model ensemble, so you can inspect figures and data before installing anything. `docs/VALIDATION.md` records actual checks performed in the build environment. Windows execution still needs to be checked on your machine.

## Reproduce without the dashboard

```powershell
.\.venv\Scripts\python.exe scripts\run_simulation.py --config examples\default.json --ensemble 20 --out outputs\reproduction
.\.venv\Scripts\python.exe scripts\sensitivity_sweep.py --config examples\default.json
```

Linux/macOS: use `python3 -m venv .venv`, then `.venv/bin/python` in place of `.\.venv\Scripts\python.exe`.

`examples/default.json` specifies every model input. Change a copy, preserve its seed, rerun, and retain the exported metadata and checksums. `references/parameter_provenance.csv` maps defaults; each export regenerates provenance for that run. The provided lock records tested core versions, while `metadata.json` records the actual runtime environment. Exact transitive dependencies are not locked across operating systems.

## What is implemented

- Full 9x9 ground-state electron/nitrogen Hamiltonian, transverse magnetic component, temperature-dependent hyperfine coupling, and eigenstate tracking.
- Stationary correlated thermal and magnetic noise; thermal cycle/drift; correlated paired readout; white and random-walk residual oscillator noise.
- Single electronic transition, electronic average, external thermometer correction with delay/error, nuclear average, and a thermally compensated electronic–nuclear composite.
- Overlapping Allan deviation, seeded realizations, model ensemble bands, and paired calibration-error study.
- Source bucket, equation/code map, active parameter provenance, manuscript-oriented vector figures, CSV data and SHA-256 checksums.

## Scientific scope

This is an advanced prototype of a frequency reference with phenomenological residual oscillator noise. It is not a closed-loop clock emulator or an experimental demonstration. It does not model pulse control, photon statistics from first principles, servo dynamics or the Dick effect. See `docs/METHODOLOGY.md` for all assumptions and omissions. Default noise levels are illustrative and have not been fitted to a published experiment.

The corrected published 2026 composite paper and the 2023 physical coefficient table were checked. Historical Acosta numbers are linked with the 2011 erratum. The 2013 stability curves are theoretical projections. Published bounds are contextual comparisons only; no raw published data were obtained. A small ADEV does not by itself establish accuracy or a publishable result.

## Deadline workflow: October 19–20

**First:** install, pass tests, launch, inspect source tracking. **Next:** choose and document one defensible environment/readout scenario; retain default results as an illustrative baseline. **Then:** run 20+ realizations and the calibration sweep; export all inputs. **Before submission:** use `docs/PAPER_NOTES.md` to describe simulated results accurately, review assumptions with your supervisor, and keep the figure caption and metadata together. A paper can use this as a modeling study; experimental performance claims require measured evidence.

## Project map

```text
app.py                          Interactive dashboard
diamondclock/physics.py         Hamiltonian, transitions, calibration
diamondclock/simulation.py      Noise and compensation
diamondclock/stability.py       Overlapping Allan deviation
diamondclock/reporting.py       Vector figures and export bundles
references/                     Bibliography, benchmarks, equation map
examples/default.json           Complete reproducible configuration
scripts/                        CLI reproduction and sensitivity study
tests/                          Numerical and dashboard validation
docs/                           Methodology, validation and manuscript notes
outputs/demo/                   Prepared simulated results and figures
```

## Provenance and persistent Paper Bucket

See [provenance and reference handling](docs/PROVENANCE_AND_REFERENCES.md) for source snapshots, historical checksum limitations, durable reference storage, and export verification. New CLI runs require a fresh output directory. The existing historical results are preserved unchanged.

## Integrated ODMR spectroscopy

Open the **ODMR spectroscopy** tab in the same dashboard. Adjust magnetic/electric
fields, microwave polarization, temperature, FWHM and orientation weights, then
select **Calculate ODMR**. Inspect all four spectra, their weighted ensemble,
energy ranks and magnetic gradients. The existing clock tabs remain available.

An optional comparison uses the current clock sidebar bias and replaces only
its assumed electronic readout sigma with an ideal resolved-line photon-noise
estimate. It is a conditional scenario, not a new accuracy or stability measurement.
Line contrast, rate and linewidth must be supplied; overlapping lines and correlated
readout are rejected for this isolated-line estimate. See
[ODMR methodology](docs/ODMR_METHODS.md) and the
[equation-to-code map](references/odmr_equation_map.md).

Reproduce a research bundle in a NEW directory:

```powershell
python scripts/run_odmr.py --config examples/odmr_intern_geometry.json --readout-config examples/odmr_readout.json --compare --samples 4096 --out outputs/odmr-new-run
```

Exports include CSV spectra, transitions, level sweeps, sensitivities, paired clock
records and Allan curves, SVG/PDF figures, source snapshots, configuration,
references and checksums. The supplied intern MATLAB transcript is retained under
[legacy/matlab](legacy/matlab/README.md); original authorship is acknowledged there.
The example uses the intern's nominal 18 G geometry; the paired clock comparison
uses the separately recorded clock bias, normally 475 G.

Validation and example results: [ODMR_VALIDATION.md](docs/ODMR_VALIDATION.md).

## Phase 3: optical excitation and photon measurements

The existing app now has an **Optical measurement** tab. The seven-state Lindblad
reference simulates laser pumping, spin-dependent ISC, singlet shelving, radiative
emission and coherent GHz microwave driving. The 21-state extension uses the
unchanged nitrogen-14 ground Hamiltonian with explicitly secular optical channels.
Contrast is calculated from populations/counts. Fast Poisson scans and a
number-resolved photon-counting reference are separately labeled.

```bash
python scripts/run_optical.py --states 7 --out outputs/my_optical_7
python scripts/run_optical.py --states 21 --out outputs/my_optical_21
python scripts/run_optical.py --config examples/optical_21.json --out outputs/my_optical_config
```

Each output folder must be new. Bundles include expected and sampled counts, all
optical populations, acquisition timing/seeds, initialization traces, reference
count distributions/trials, solver benchmarks, provenance and vector SVG/PDF plots.
Paper Bucket entries distinguish published fitted rates from operating assumptions.
Only local axial 5–50 G, E=0 and nominal 297 K are supported by this phase; **475 G
is rejected**. This is simulated data, with no fit to apparatus and no clock servo.
Read [optical methods](docs/OPTICAL_METHODS.md), [validation](docs/OPTICAL_VALIDATION.md)
and the [equation map](references/optical_equation_map.md). Existing clock/ODMR
features and the original intern MATLAB attribution archive are retained. No
Streamlit redeployment is part of Phase 3.

## Phase 4: photon-based frequency locking

Install from the project root (including Windows/VS Code):

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

Editable package discovery is explicit. The installed `diamondclock-clock` command
also works outside the checkout; wheel installs include scientific assets/source
snapshots. In the same Streamlit app, **Clock Performance** provides count-only
acquisition, uncertainty, a causal latency-queued PI loop, oscillator phase/time
error and output-based Allan deviation. Nothing is automatically deployed.

```bash
python scripts/run_clock.py --states 7 --cycles 512 --validation-trials 100 --physical-trials 40 --out outputs/NEW_CLOCK7
python scripts/run_clock.py --states 21 --cycles 512 --out outputs/NEW_CLOCK21
python scripts/run_clock.py --scenario high-gain --cycles 256 --out outputs/NEW_UNSTABLE
python scripts/run_clock.py --scenario latency --cycles 256 --out outputs/NEW_LATENCY
python scripts/run_clock.py --scenario photon-starved --cycles 128 --out outputs/NEW_LOW_COUNTS
```

Use `--config examples/clock_7.json` (or `clock_21.json`) for exact demonstration
inputs. Every output path must be new. Existing optical and legacy stability runs
are unchanged. The seven-state long-run plant is the Lindblad reference; the
21-state CLI default uses the finite-time-benchmarked rate reduction and assumes
1000 independent centers/linear detection. No locking or stability improvement is
guaranteed. Full records and a predeclared fixed evaluation window are both retained.
Read [clock methods](docs/CLOCK_METHODS.md) and [validation](docs/CLOCK_VALIDATION.md).

Scope remains local axial 5–50 G, E=0, 297 K; **475 G is rejected**. Synthetic
counts, fitted optical parameters and controller/noise assumptions are distinguished
in the Paper Bucket. This is an NV-referenced oscillator simulation, not an
experimental accuracy claim or a validated 475 G composite clock.

## Unified dashboard

**Overview** now summarizes the last completed session experiment and its
scientific conclusion. **Clock Performance** presents photon acquisition, oscillator
correction and lock flags, phase/time error, full-record or predeclared-window Allan
deviation, and limitations. Each stability ratio identifies its matched averaging
time; observed lock is not treated as proof of better stability or absolute accuracy.

Choose **Browse saved experiments** for the original verified seven/21-state runs,
failed-lock cases, and the quieter-oscillator example that locks but worsens stability.
These read existing research bundles without rerunning or modifying historical data.
Research Tools preserves the original controls and diagnostics. Paper Bucket provides
direct reference access; CSV/provenance bundles and SVG/PDF figures remain available
in each workspace and Exports & Documentation. The 3D ODMR demonstration
remains an independent educational workflow.

See [Clock Performance guide](docs/CLOCK_PERFORMANCE.md) for exact run commands,
comparison methodology, archive handling, limitations and reproducibility. The launch
command remains `python -m streamlit run app.py --server.port 8502` after
`python -m pip install -e ".[dev]"`. No merge or deployment is performed.

The six navigation pages are **Overview**, **NV-Center & ODMR**, **Clock Performance**,
**Research Tools**, **Paper Bucket**, and **Exports & Documentation**. No mode switch
is required. All expensive experiments, including Stability & compensation, run only
on explicit submission. See [dashboard use and validation](docs/DASHBOARD_UX.md).

**Atomic Clock Comparison** adds one contextual table and graph alongside the
existing pages. It compares the original seven-state saved simulation with NIST
representative cesium-beam, rubidium-cell and hydrogen-maser stability values.
Literature points retain their qualifiers; they are not matched experimental tests
or evidence that the simulated NV reference matches conventional clocks.
See the [value-to-source map](references/clock_comparison_map.md), also available in
Paper Bucket → Equation maps → Atomic clock comparison. No simulation runs when
opening this page.
