# Validation record

Build date: 2026-10-19. Tested with Python 3.12.14 on Linux. Core dependency versions are pinned in `requirements.txt`; actual environment details accompany each exported run. Native Windows execution has not been tested in this environment.

## Checks completed

The suite contains 16 tests, including:

- Hamiltonian Hermiticity and the analytic uncoupled Zeeman limit.
- Numerical nuclear transitions and thermal derivatives against Lourette 2023 Table III at 297 K and 470 G. The calculation gives 5,085,964.20 Hz and 4,799,631.49 Hz, with slopes -35.1862 Hz/K and -35.3347 Hz/K. Tolerances reflect rounded fitted coefficients. This is verification against a calculation using the same coefficients, not independent experimental validation.
- Convergence of finite-difference thermal slopes; cancellation of the first-order composite temperature term; unit gain for common residual oscillator noise.
- NIST SP 1065 nine-point frequency dataset. Overlapping ADEV matches 91.22945 and 85.95287 at averaging factors 1 and 2.
- Independent comparison with AllanTools `oadev`, including exact overlapping pair counts, for several averaging factors.
- Expected white-FM inverse-square-root averaging behavior and analytic linear-drift ADEV.
- Seed repeatability, zero-noise behavior, ideal local thermal compensation, readout sample-interval scaling, OU stationary variance and lag-one correlation, and invalid-scope rejection.
- Streamlit AppTest initial rendering, parameter submission, three-realization ensemble generation, and export preparation.
- Parameter-to-source/code traceability, valid SVG/PDF generation and ZIP construction.

The complete suite passed after testing the dashboard ensemble and export actions. Vector figure layout is also rendered and inspected visually. CLI reproduction generates the full default 32,768-sample run plus a 20-realization model ensemble; the calibration sweep uses seven paired error settings. The live Streamlit server is checked separately via its health endpoint.

## Limits of this verification

Tests demonstrate numerical consistency of the implementation and known estimator limits. They do not validate the assumed environment spectra, readout errors or oscillator noise against hardware. No closed-loop lock response, experimental performance or new physical compensation mechanism is established. Published measurement upper bounds are contextual references, not targets used to tune noise parameters. Coefficient uncertainties and sample-to-sample variability are outside the ensemble.

Run locally:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
