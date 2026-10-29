# NV demonstration: model-to-presentation mapping

| Quantity | Existing source / implementation | Presentation |
|---|---|---|
| Spin Hamiltonian and D near 2.87 GHz | L2023 Eq. (1); `physics.py`; D2012; existing ODMR map | Passed unchanged to `odmr.spectrum` |
| Lab/NV transformations | `odmr.ROTATIONS`, `transform`; intern-derived frames with attribution retained | Same B vector as Part 2 geometry; selected NV local +x microwave polarization |
| Transition centers, degeneracies, strengths | `odmr.transition_table`, `spectrum`; existing ODMR methodology | Calculated center rug; overlapping centers may differ from dip minima |
| Normalized fluorescence proxy | `odmr.spectrum`, `lorentzian`; DRE2011 context and MODEL assumptions | One selected NV; FWHM/contrast are assumed, not fitted optical-cycle outputs |
| Selected fluorescence | Linear interpolation of that engine grid | Numerical presentation method, not an independent physical model |
| Green/red/purple arrows | Educational illustration | Static; no EM propagation or photon statistics; red opacity follows the displayed normalized signal |
| Seven/21-state photon counting | TET2012, ROB2011, HIN2018, PAN2024; existing optical methods | Separate Advanced Research workflow; amplitudes and counts not mapped here |
| Locking and Allan deviation | Existing Phase 4 methods and source map | Separate Clock Performance workflow; not inferred from an ODMR dip |

No new literature constants or scientific reference records are introduced.
Full inputs, domain rules and limitations: `docs/NV_ODMR_DEMONSTRATION.md`.
