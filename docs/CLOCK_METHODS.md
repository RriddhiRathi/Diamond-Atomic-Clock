# Phase 4: photon-based NV-referenced oscillator

All outputs are SIMULATION. No apparatus data were fitted. Published optical rates
remain the Tetienne NV E fitted preset; oscillator, detector, controller, timing and
sample shifts are assumptions. Numerical validation is not experimental validation,
SI calibration, or proof of an accurate/composite diamond clock. The Phase 3 domain
remains local axial 5–50 G, E=0 and nominal 297 K. 475 G is rejected. Existing
stability/compensation methods, historical data and MATLAB attribution are retained.

## CLK1. Plant, observer and truth boundary

The plant reuses Phase 3 optical_cycle/optical_dynamics, not a manually imposed
contrast. Inference accepts ONLY immutable CountObservation(probe_offset_Hz,
nominal_gate_s,detected_counts,microwave_on,local_start_s) plus an independently
count-fitted Calibration. No expected counts, density matrix, sample offset, LO
frequency, true timing, random stream, Hamiltonian target or plant object enters
frequency_estimation.py or clock_controller.py. Evaluation computes truth errors
after the simulation and never feeds them back. Tests check this interface and imports.

Initial acquisition frequencies are a fixed PUBLIC grid +/- acquisition_span_Hz
around nominal f0 = published D(297 K) + gamma_e * configured Bz. The plant alone
receives a copied Physics with D0 shifted by reference_offset_Hz; no original
Hamiltonian or coefficient file is edited. The unknown shift is a sample-model
assumption within +/-1 MHz, not temperature variation or an observed correction.
The estimator is not initialized at that hidden transition. Calibration is fitted
from detected counts. Reacquisition freezes the current known actuator command,
cancels queued corrections, and scans around that controlled carrier.

Only oscillator/reference DETUNING is identifiable from this experiment. An
acquisition centre is in commanded-probe coordinates relative to the controlled
carrier, not an absolute SI frequency. Public nominal frequency and hyperfine
spacing do not reveal a realization's private sample/oscillator errors. Diagnostic
Hamiltonian error includes line pulling and estimator-model effects; no oracle bias
correction is applied. Photon locking is not equivalent to UTC accuracy.

## CLK2. Continuous optical dynamics and finite measurement

Frequency modulation acts on a probe DDS branch. The useful output is the continuous
controlled oscillator BEFORE probe modulation. Probe DDS phase remains continuous
at frequency changes; the rotating-frame phase integrates that frequency, so the
same state is carried across settings without arbitrary phase resets. Ground eigenbasis
is fixed because the field and temperature are fixed in each experiment.

The Phase 3 rank-one optical jumps generate only ground-state coherences and excited/
singlet populations from the initial mixed ground state. This is a closed sector:
3x3 ground coherence plus 4 populations gives 13 variables for seven states; 9x9
plus 12 gives 93 for 21 states. The implementation verifies zero coupling OUT of
this sector in the full Liouvillian. It is an exact computational reduction of the
existing Lindblad model, not an extra secular approximation. H/h [Hz] enters with
2*pi only in the coherent generator. Frequency dependence is affine; the dissipators
are unchanged. The count integral is an additional linear state, propagated with a
matrix exponential. Trace/positivity and tiny normalization roundoff are checked.

Every sample evolves rho continuously through laser preparation, unobserved settling,
MW-off reference gates and side probes. Start-up is 50 us of pump-only evolution
from a completely mixed ground manifold. Every frequency switch has configurable
settling, then a nominal photon gate. No stationary reinitialization occurs between
gates. Expected counts integrate efficiency*N*Tr(J_rad rho)+background+dark_rate
through every actual integration segment of each gate. Photon draws are Poisson
APPROXIMATIONS, qualified by driven Lindblad counting-moment/covariance cases, not
certified solely by the <=2% efficiency guard. Quantum gate correlations, technical
intensity noise, detector dead time/afterpulsing and sample variability are omitted
from long records. Larger N assumes linear or parallel detection, not a saturated APD.

The rate backend uses Phase 3's approximate steady Bloch-coherence elimination and
retains population memory between gates. It is not used as a reference. Sequential
finite-time emitted-count differences versus the full Lindblad model are exported
in optical_backend_comparison. That limited grid does not validate every user setting.
21-state assumptions (independent optical channels, omitted excited/singlet nuclear
dynamics/coherence transfer) remain exactly as documented in OPTICAL_METHODS.md.

## CLK3. LO noise, output phase and local timing

Oscillator offset_Hz is Hz; drift_Hz_s is Hz/s; white_fm_Hz_at_1s is the standard
white-FM frequency average at 1 s. On a native true-time interval h its sigma is
white_fm_Hz_at_1s/sqrt(h/1 s). Random-walk increments have sigma
random_walk_Hz_sqrt_s * sqrt(h). Three independent named SeedSequence streams
produce white FM, random-walk FM, and white phase nodes. Linearly interpolated
phase nodes have phase_noise_rad RMS at sample nodes; their differenced phase /
(2*pi*h) contributes frequency. Thus phase and frequency arrays are consistent,
with an explicit numerical band set by h. This is a discrete finite-band scenario,
not infinite-band white PM or a calibrated oscillator spectrum. Flicker FM and a
measured analog oscillator transfer function are not implemented in this phase.
Drift uses interval midpoint averages. Timestep/bandwidth convergence is required
for new noise regimes. At most 1% fractional deviation is accepted by the scheduler.

Let delta_f[k] be the continuous controlled carrier interval average minus fixed f0.
phi_error[n+1] = phi_error[n] + 2*pi*delta_f[n]*h;
x[n] = phi_error[n]/(2*pi*f0); y[k]=delta_f[k]/f0.
Positive x means the simulated clock leads the nominal reference. Probe modulation
is NEVER integrated into useful clock phase. Offset can yield nonzero time error
while having zero Allan deviation. Phase deviations are accumulated directly to
avoid cancellation of enormous carrier phases. Full unwrapped carrier phase is
also exported, but precision-sensitive analysis uses phase deviations.

Nominal gate duration and latency are local-clock seconds: C=t+x, dC/dt=1+delta_f/f0.
A gate ends when C increases by the programmed duration; the private scheduler
computes actual SI-coordinate duration. Observations contain only programmed gate
duration/local timestamp; actual start/end times and expected counts are exported
separately as evaluator truth. No ideal external timebase is fed into inference.
The frequency and actuator values are piecewise constant in native intervals,
with exact splitting at gate boundaries/queued-actuation deadlines. Output interval
averages retain all acquisition, settling, processing-latency and loss-of-lock time.

## CLK4. Acquisition, line family and uncertainty

Acquisition uses raw counts, including MW-off references. Its empirical rate family
is beta * [1-sum_j C_j/(1+4*((probe-centre-offset_j)/Gamma)^2)]. Gamma is FWHM.
beta, centre, Gamma and C_j are fitted; contrast is NOT fixed to plant truth.
The seven-state family has one dip. The 21-state family has three dips with a
shared width and PUBLIC nominal offsets +/-abs(A_parallel),0. No nuclear label
is chosen by hidden populations or by the deepest simulated-mean dip. Shared widths,
fixed spacing and additive dips are estimator approximations, not exact Lindblad
identities. Their bias/coverage versus Lindblad-generated spectra are measured in
physical_estimator_validation; users must not assume the matched-family coverage
also proves physical-model accuracy. Unresolved/multimodal features can fail.

For counts n_i and predicted means mu_i(theta), the minimized negative likelihood
(up to constants) is sum(mu_i-n_i+n_i*log(n_i/mu_i)); n=0 contributes mu_i.
This is half the Poisson deviance. A bounded multi-start least-squares implementation
uses signed square-root deviance residuals. Starts depend only on observed counts
and the public search window. Distinct near-equivalent minima are flagged ambiguous.
Low contrast, bad likelihood ratio, scan boundaries and poorly identified frequency
are rejected. Acquisition covariance comes from Poisson Fisher information with
fitted nuisance parameters. Production acquisition additionally profiles nuisance
parameters for 95% likelihood endpoints at delta negative-log-likelihood 1.9207294.
Wilks/Fisher thresholds are asymptotic, not guaranteed confidence at low counts.

Tracking sequence: MW off, +d, -d, -d, +d, MW off; each has settling and a gate.
This symmetric ABBA design reduces first-order ordering effects but does not prove
complete immunity to nonlinear/drifting brightness or fast LO noise. A profile
likelihood fits carrier detuning e using the calibrated shape; the contemporaneous
baseline is profiled analytically: beta=sum(n)/sum(t*relative_response(e)).
The reported timestamp is the mean gate midpoint on the local timebase, not an
oracle instantaneous frequency at correction time. The cycle model is a quasi-static
estimator approximation; the plant integrates actual within-gate LO noise and dynamics.

Count-only profile endpoints are exported. Independent calibration-shape covariance
(log width and fitted dip fractions) is propagated to detuning to first order using
implicit likelihood derivatives. Total sigma combines curvature variance and that
shape contribution. Total nominal 95% intervals use +/-1.96 total sigma. These are
APPROXIMATE intervals: matched calibration/tracking Monte Carlo evaluates empirical
coverage. Calibration covariance is not a full physical-rate uncertainty budget.
No covariance is invented for published optical parameters. Sparse/flat/unbounded
tracking likelihood and capture-boundary estimates are invalid; invalid estimates
freeze integration and trigger observed-quality handling rather than fake zeros.

## CLK5. Controller, latency and failures

e>0 means the controlled oscillator is too high relative to the operational feature.
The positional PI convention is
I_next = I - Ki*T_cycle*estimated_e;
u_request = clip(I_next - Kp*estimated_e, +/-correction_limit_Hz).
Kp is dimensionless; Ki is 1/s. Conditional integration prevents winding farther
into saturation. Acquisition seeds I from CURRENT known actuator command plus the
count-fitted centre. With both gains zero acquisition steering is disabled and the
useful output equals the unlocked oscillator. Initial acquisition commands and every
tracking command enter the same latency queue. They cannot influence counts already
acquired. Requests are activated only after their local-clock deadline. Processing
is pipelined with subsequent measurements; latency is not automatically all dead time.
The actuator is ideal zero-order held with finite range, NOT a modeled analog slew/
settling response. Range limits and no phase resets are enforced. Loop gains are
engineering scenarios inspired by PEIK2006/LER2017, not measured NV controller gains.

Lock detection uses estimate validity, |e_hat|+sigma < lock_error_Hz, sigma below
lock_sigma_Hz, saturation and configurable consecutive-good/bad counts. No true
frequency or physical output error enters this decision. On loss a capped number
of new acquisitions is allowed. Failed acquisition, false locks, instability and
worse ADEV are valid results. The demonstration includes high-gain, long-latency
and low-count cases using ordinary model settings, without forced lock flags.
Lock fraction is observed; truth residuals and false-lock assessments are offline.

## CLK6. Actual clock Allan deviation and comparison

Existing stability.overlapping_adev is called directly with contiguous native-grid
output averages delta_f/f0, not inferred frequency errors or control corrections.
Locked and unlocked outputs share the identical free LO realization and band.
Every interval remains, including failed locks. Full record and a SECONDARY fixed
window t>=fixed_analysis_start_s (default 2 s, set before simulation) are exported
separately. No best-lock window is selected; disjoint intervals are not concatenated.
Drift is retained; maximum tau remains record/10. Ensemble quantiles are not
measurement confidence intervals. Column prefix `locked` identifies the feedback-enabled branch, not certification
that it is locked. Observed lock fraction is shown separately.
No universal improvement is expected at short tau;
feedback can inject photon noise and create servo peaking. This simulator includes
sampled/finite-time noise paths but does not claim a general validated Dick-effect
calculation. SCH2017 supplies dead-time context, not an NV performance benchmark.

## CLK7. Provenance and installation

All sources, nested configuration (including private plant assumptions for later
reproduction), validation protocol, Physics, numerical table hashes, environment,
references and MATLAB attribution are bound before export. Changed sources, tables,
summary or config are rejected. Output directories must be fresh. Independent
oscillator/photon streams prevent count draw counts from changing free LO noise.
Public observation and evaluator-truth tables are distinct. Sources explain which
rates were published fits and which parameters/algorithms are scenario assumptions.

Editable-installation fix: explicit setuptools build backend/discovery of diamondclock,
matching runtime dependencies and dev extra. CI now installs -e .[dev]. Wheel builds
include scientific assets and an actual source snapshot via ScientificBuild; runtime
ROOT resolves checkout assets or packaged assets. Installed wheel reference storage
is user writable. Tests install/import/run outside the checkout, so pytest pythonpath
cannot conceal broken packaging. Historical output trees are not copied into wheels
or changed; they remain in Git. The package does not need VS Code to stay open.

## CLK8. Remaining limits

This is an end-to-end CONDITIONAL low-field NV-referenced oscillator, not a complete
experimental atomic clock or the original 475 G electronic/nuclear composite.
Unmodeled apparatus systematics include optical-rate/sample uncertainty, laser
technical noise, field/temperature drift, detector nonlinearity/dead time, excited-state
hyperfine/nuclear coherence transfer, reference aging, oscillator hardware spectrum,
analog actuator dynamics, synthesizer/divider noise, and SI calibration. Default field
and temperature stay fixed in each run. More detailed models require new validation;
closing a software loop does not validate those omissions.

The default 10 kHz/s oscillator drift is a deliberately drift-dominated stress
demonstration, not a claim of typical quartz/OCXO behavior. `clock_low_drift.json`
uses 100 Hz/s with the same measurement noise/gains and can lock while making ADEV
worse: photon feedback is not automatically beneficial to an already quieter LO.
The 21-state successful example assumes 1000 independent centers/linear detection;
100 centers at the same gate can fail the uncertainty-based lock criterion.

The offline `evaluation_tracking_error` table compares accepted estimates with
duration-weighted actual MW-on carrier detuning to the Hamiltonian target. It
includes line pulling and the within-cycle approximation. Its fixed-window coverage
is an empirical diagnostic, not a truth-driven adjustment of controller gains or CIs.
