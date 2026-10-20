# Manuscript use

## Suggested scope

"A reproducible simulation study of environmental and readout limits in a composite NV-center diamond frequency reference."

The composite compensation principle is established prior work. A new dashboard alone does not establish scientific novelty. A useful modeling question is the trade-off among nuclear readout noise, calibration mismatch, thermal curvature and residual magnetic/oscillator noise. Extend the paired sweep or run independent ensembles after selecting a scientifically justified operating scenario.

## Methods wording to adapt after choosing a scenario

"We simulated the ground-state electron and nitrogen-14 spin Hamiltonian using the coupling parameters and local temperature derivatives reported by Lourette et al. (2023). Transition frequencies were calculated by numerical diagonalization. Fractional electronic and nuclear half-sum signals were combined using the first-order compensation principle of Lourette et al. (2026), with slopes evaluated for the simulated observables. Environmental, readout and residual oscillator processes were generated from explicitly stated stochastic assumptions. Overlapping Allan deviation was evaluated following NIST SP 1065. These results are numerical simulations and do not represent experimental clock measurements."

Replace this text with the final configuration, duration, sampling convention, seed scheme, ensemble size, package versions and rationale for assumed noise levels. Cite the underlying papers directly, not the simulator as a replacement for those citations.

## Figure caption starter

"Simulated overlapping Allan deviation of five NV-center frequency-reference signals under the assumptions in [scenario table]. The nine-state ground-state model includes temperature-dependent zero-field splitting and hyperfine coefficients, magnetic fluctuations, paired readout noise and common residual oscillator noise. Curves show one seeded realization; where shown, shaded bands span the 5th–95th percentiles of independent model realizations. Downward open markers indicate reported upper limits from Lourette et al. (2026), not imported raw measurements. No experimental fitting or drift removal was performed. Averaging times are restricted to one tenth of the simulated record."

## Before including a figure

Keep SVG/PDF, complete CSVs, config, metadata, seed list, checksums and exact source-code revision together. State that the ensemble excludes physical-coefficient uncertainty. Avoid claiming improvement over a published upper bound or calling simulated traces "measured". State that oscillator noise is an assumed additive residual rather than the result of a solved feedback loop.

The 2023 transition checks share the same physical coefficients as the implementation, so describe them as verification against published calculations. An independent measured dataset is still needed for empirical validation. The 2026 paper states its supporting raw data are available from its authors upon reasonable request; no request has been sent.
