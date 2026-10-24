# Diamond Atomic Clock

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
