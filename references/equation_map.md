| Equation or method | Source and exact location | Python implementation |
|---|---|---|
| Spin-one electron + spin-one 14N Hamiltonian, in Hz | L2023 Eq. (1), p. 064084-2; L2026 Eq. (1), p. 064046-2 | `diamondclock/physics.py:hamiltonian` |
| Local quadratic coefficient expansion (M1) | Taylor expansion derived here; measured derivatives: L2023 Table II, p. 064084-5 | `physics.py:thermal_parameters` |
| Electronic half-sum; signed nuclear half-sum (M2) | L2026 Fig. 1 and Appendix A, p. 064046-9 | `physics.py:observables` |
| Fractional half-sum thermal slopes by central difference (M3) | Numerical method; L2026 Appendix A motivates correcting half-sum slopes | `physics.py:calibration` |
| Composite weights, sum equal to one | L2026 Eq. (5), p. 064046-3 | `physics.py:composite_weights` |
| Fractional frequency and overlapping Allan deviation (M4) | NIST2008 Sec. 5.2.4, Eq. (10), printed p.16 | `stability.py:overlapping_adev` |
| Stationary OU recurrence; sinusoidal and linear environmental terms (M5) | MODEL: explicitly chosen stochastic process; not a measured noise spectrum | `simulation.py:ou,simulate` |
| Correlated paired readout; white and random-walk residual oscillator noise (M5) | MODEL: Gaussian construction and discrete random walk | `simulation.py:paired_readout,simulate` |
| External thermometer correction and delay (M5) | MODEL: first-order subtraction using calibrated slope, with gain error | `simulation.py:simulate` |
| Model ensemble percentiles (M6) | MODEL: sample quantiles of independent realizations | `simulation.py:ensemble` |
| Projection guides and reported upper-limit markers (M7) | H2013 abstract; L2026 abstract / Fig. 3 | `reporting.py:stability_figure`; `references/benchmarks.csv` |
| Paired calibration-error sweep (M8) | MODEL: parameter experiment using shared seed | `scripts/sensitivity_sweep.py` |

Every numerical parameter carries units, source ID, locator and assumption notes in the dashboard parameter table and `parameter_provenance.csv`. Spin matrices and eigensystem tracking are numerical linear algebra. Display styling and plot sampling are presentation choices.

## ODMR extension

The original M1-M8 mapping remains above. The additive spectroscopy and optional
readout bridge are mapped in [odmr_equation_map.md](odmr_equation_map.md), with full
units, assumptions and attribution in [ODMR_METHODS.md](../docs/ODMR_METHODS.md).

## Phase 3 optical measurement

The additional optical equations, published fitted rates, detector assumptions and
21-state extension are mapped in `references/optical_equation_map.md` and documented
in `docs/OPTICAL_METHODS.md`. Existing clock equations and inputs are unchanged.
