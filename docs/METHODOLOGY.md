# Diamond Atomic Clock methodology, version 0.1

## Interpretation

All generated traces and stability curves are **simulations conditional on the supplied configuration**. No experimental dataset is loaded. Published measurement limits are separate reference markers; theoretical projections are optional guides. The project does not establish absolute accuracy, a quantum-limited clock, or new experimental performance.

## Physical model (M1-M3)

Use the negatively charged nitrogen-14 NV center: electron spin S=1 and nitrogen spin I=1. Construct and diagonalize the full nine-dimensional ground-state Hamiltonian in cyclic frequency units H/h (Hz). Magnetic fields are in gauss; 1 G = 100 microtesla. Gyromagnetic ratios are in Hz/G. Electron Zeeman and nuclear Zeeman terms have opposite signs in the adopted convention. There is no angular-frequency factor of 2π in the matrix.

The Hamiltonian and coefficient data are traced through the Research Paper Bucket. Parameters D, Q, A_parallel and A_perp vary through the local expansion **X(T)=X0+X1 ΔT+0.5 X2 ΔT²** (M1), where X2 is the second derivative. The expansion is restricted by software to |ΔT| <= 5 K around 297 K. This is a conservative scope choice, not a published validation interval for this truncated expansion. Coefficients are central values for the cited sample; their uncertainties and sample variability are not propagated.

Eigenstates are labeled at the bias point by maximum product-state overlap with a global unique assignment. Each subsequent eigensystem is matched to that reference; the calculation rejects nonunique matches or overlap below 0.8. Strongly mixed states and level anticrossings require a different analysis. Bias is restricted to 10–600 G, static transverse field to +/-1 G.

Transitions are energy differences labeled by their dominant |m_s,m_I> character. Electronic f+ and f- connect |0,+1> to |+1,+1> and |-1,+1>. Nuclear f1 and f2 connect |0,0> to |0,+1> and |0,-1>. M2 defines Dobs=(f+ + f-)/2 and **Qobs=-(f1+f2)/2**, retaining the signed quadrupole convention. These observables differ from the Hamiltonian D,Q due to hyperfine mixing; exact diagonalization retains that correction.

For M3, central differences at 297 +/-0.01 K give observable slopes and λ=(df/dT)/f0. Calculate the electronic–nuclear weights from these actual half-sum slopes, not from rounded D and Q coefficients. Tests check convergence of these derivatives.

## Stochastic construction and sampling (M5)

N samples represent contiguous intervals of length Δt with no dead time. Each generated environment value is held constant over its interval; the Hamiltonian frequency is thus the effective interval average in this discrete model. This approximates a continuously varying environment when Δt is small relative to its correlation times. It does not resolve fast field dynamics, pulse timing or an acquisition transfer function.

Temperature and the two field components use independent stationary Ornstein–Uhlenbeck sequences:

**x[k]=a x[k-1]+σ sqrt(1-a²) ξ[k], a=exp(-Δt/t_c), x[0]~N(0,σ²)**.

The implementation uses `sqrt(-expm1(-2Δt/t_c))` for numerical stability. Temperature adds a sine with user-selected peak amplitude and period, plus linear drift in K/hour. These are illustrative environment models, not experimentally estimated spectra. OU RMS refers only to the stationary component; adding a sine and drift changes the record RMS.

Each transition pair receives Gaussian errors e1=σ z1 and e2=σ(ρ z1+sqrt(1-ρ²) z2). Pairs are mutually independent; ρ is the correlation within a pair. Electronic and nuclear σ are specified **per transition at a one-second interval**, and scale as 1/sqrt(Δt). This white readout model is phenomenological; photon collection, contrast, linewidth and decoherence are not independently modeled. No photon-shot-noise-limited claim is made.

The residual oscillator term is common to all methods: independent white fractional FM with standard deviation A/sqrt(Δt), a discrete random-walk FM with increment standard deviation q sqrt(Δt), and optional linear fractional drift. Here A is the white-FM Allan deviation at one second; q is diffusion, not an ADEV value. Random walk begins at zero. This term describes assumed **residual** oscillator noise after unspecified stabilization. There is no feedback loop, servo bandwidth, frequency-lock simulation, dead-time aliasing or Dick-effect calculation. Common oscillator noise survives the composite sum because its weights sum to one.

## Reference signals

Each reference uses fractional frequency difference relative to its own nominal frequency at 297 K and the configured bias. Static offsets therefore do not appear in Allan deviation.

1. Single electronic transition: fractional change of f+, plus readout and residual oscillator noise.
2. Electronic average: fractional change of Dobs, plus averaged electronic readout and oscillator noise. Opposite Zeeman shifts cancel to leading order; full-model residual shifts remain.
3. External thermometer: electronic average minus λD_est times the measured temperature change. Thermometer white error and an optional delay remain. Delay is rounded to the nearest interval and the first reading is held over startup.
4. Nuclear average: fractional change of signed Qobs, plus averaged nuclear readout and oscillator noise.
5. Composite: yC=wD yD+wQ yQ. Define λQ_est=λQ(1+error/100), wQ=λD/(λD-λQ_est), wD=1-wQ. The same error setting multiplies the external thermometer's D slope. These two effects are distinct scenario perturbations linked to one control for convenience. At zero slope error the calibrated first-order thermal response cancels locally; curvature and magnetic sensitivity remain. Readout can make the composite worse.

## Stability estimator (M4)

For finite, uniformly spaced fractional-frequency samples y[i], define z[j]=(1/m) sum(y[j:j+m]) and calculate **ADEV=sqrt(mean((z[j+m]-z[j])²)/2)**. This is the overlapping estimator in NIST SP 1065 Eq. (10). There are N-2m+1 overlapping differences. Cumulative sums evaluate it efficiently. Subtracting the overall mean improves conditioning; deterministic drift is retained.

Averaging factors are unique rounded integers on a logarithmic grid, supplemented by exactly representable 1, 2 and 5 times powers-of-ten averaging times. The default largest m is floor(N/10), so τ <= NΔt/10. This restriction is conservative and does not guarantee small uncertainty. Overlapping differences are correlated; their count is not equivalent degrees of freedom. The software does not attach naive ADEV/sqrt(pair-count) confidence bars. Zero ADEV is mathematically valid for constant signals and cannot be displayed on logarithmic axes.

## Ensemble and sensitivity study (M6, M8)

Independent realizations use NumPy SeedSequence child streams. Quantiles at each averaging time are 5%, median, 95%. They describe the distribution of this simulated estimator under the configured stochastic model. They are **not measurement confidence intervals**, coefficient uncertainty, or evidence that a real clock meets the same stability. Twenty or more realizations are useful for exploration; stable tail estimates require more. The optional calibration sweep uses the same root seed across error levels so environmental realizations are paired; those runs are not independent repetitions.

## Comparison and provenance (M7)

The bibliography identifies original papers, exact locators, corrected versions, and implementation symbols. The parameter table is generated directly from dataclass metadata, including all configuration assumptions. The 2023 transition table provides a published calculation cross-check; it is based on the same fitted coefficients and is not independent experimental validation. The 2026 reported ADEV bounds are contextual comparisons. No raw record was obtained and no simulated noise level was fitted to their curve. Do not compute an improvement claim against an upper bound. Different acquisition protocols, reference oscillators and samples prevent an equivalence claim.

## Reproduction and limitations

Exports include configuration, source hashes, package versions, provenance, full simulated series, ADEV, vector figures and checksums. Reproducing on the tested environment with the same seed gives matching numerical arrays; operating-system and numerical-library changes can cause small floating-point differences. Arrays are generated with named component streams to keep parameter sweeps paired.

Excluded: fluctuating strain/electric fields, optical/RF power shifts, laser heating dynamics, stochastic hyperfine coefficients beyond their temperature model, isotope-15, other NV orientations, inhomogeneous ensembles, transition strengths, preparation/readout fidelity, pulse control errors, servo dynamics, reference-clock noise subtraction, experimental coefficient uncertainty and absolute frequency calibration. A scalar electron gyromagnetic ratio is used for the small transverse field, neglecting the small g-tensor anisotropy reported by Felton et al. (2009). Ground-state simulation at 475 G does not simulate the excited-state optical-polarization mechanism. Publication use needs an explicit statement of these assumptions and further validation against an independent measured record.
