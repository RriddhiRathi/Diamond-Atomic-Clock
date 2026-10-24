# ODMR spectroscopy and conditional clock comparison

All generated spectra, energy diagrams and Allan curves are **SIMULATION**. Paper
coefficients/equations are literature-derived; field settings, linewidth, contrast,
photon rate, orientation weights and population/readout models are assumptions.
This integration neither establishes clock accuracy nor validates hardware stability.

## O1. Shared ground-state Hamiltonian and units

The unchanged clock `Physics` coefficients and `hamiltonian` are reused. With
spin-one dimensionless operators and cyclic frequency units (no 2 pi factor),

H/h = D(T) Sz² + Q(T) Iz² + Aparallel(T) Sz Iz
      + Aperp(T) (Sx Ix + Sy Iy) + gamma_e B.S - gamma_n B.I + H_E/h.

L2023 Eq. (1), p. 064084-2 and Table II, p. 064084-5 supply the original model.
The spectroscopy extension adds By; it does not replace or change the clock API.
Hz is used internally, MHz only for presentation, G for magnetic fields, V/m for
applied electric fields. 1 G = 1e-4 T. The existing local temperature Taylor
expansion is restricted to 297 +/-5 K.

D2012 Eq. (24), printed p. 205203-7, supplies the weak static electric coupling:

H_E/h = d_parallel Ez Sz² - d_perp Ex (Sx²-Sy²) + d_perp Ey (Sx Sy+Sy Sx).

D2012 Sec. II B, printed p. 205203-6, quotes 0.35(2) Hz cm/V (text before
Eq. (17)) and 17(3) Hz cm/V (discussion following Eq. (16)). Converted coefficients
are 0.0035 and 0.17 Hz/(V/m). These are coefficients quoted in that theory paper,
not new fits or newly measured constants; parameter uncertainty is not propagated.
The original experimental source V1990 is linked separately; its numerical text
has not been independently rechecked here. Do not mark it as fully verified.

The local x/y axes are the explicit right-handed frames in `odmr.ROTATIONS`,
transcribed from the intern's matrices. This defines our Stark tensor convention;
users must map their sample's transverse axes and NV polarity into these frames.
Orthogonality alone does not calibrate the crystal's physical azimuth or polarity.
No arbitrary rotation of local x/y while retaining the same Stark tensor is allowed.
No extra strain is added: the original D may already include an axial offset. An
independent strain tensor, electric response of Q/A, excited-state physics and
anisotropic electron g corrections are outside this extension. Electric perturbation
norm is restricted to 1% of D as an explicit conservative model-scope assumption.

## O2. Four orientations and microwave transitions

For each orientation k, v_NV = R_k v_lab and v_lab = R_k.T v_NV. All matrices
have determinant +1; local z axes have mutual dot products -1/3. Spherical angles
use polar theta from +z and azimuth phi from +x toward +y. UI angles are degrees.

The normalized, linearly polarized microwave operator is
M = sum_k u_k (S_k - gamma_n/gamma_e I_k).
Relative transition strength is |<j|M|i>|². Absolute microwave amplitude, Rabi
calibration, saturation and power broadening are not inferred. This is the magnetic
perturbation of O1 (and the corrected intent of the intern's transition function).
Only positive-frequency, distinct energy manifolds are included. Numerically
identical eigenvalues within 1e-5 Hz are grouped; strength between groups a,b is
||V_b† M V_a||_F². This makes grouped strength independent of eigenvector choices
inside exactly degenerate manifolds. Such transitions do not have unique individual
Hellmann-Feynman slopes; their sensitivity entries are NaN, not false zeros.

## O3. Explicit fluorescence proxy

P0 = 1 - Sz² is the electronic bright-state projector. For each energy manifold,
b_a = Tr(V_a† P0 V_a)/rank(a). Assume scalar population per state b_a/3 and
brightness b_a within that manifold. The proxy dip weight is
w_ab = ||V_b† M V_a||_F² (b_a-b_b)²/3.

This brightness/population model is a project assumption (MODEL), not a published
optical rate-equation solution. It approximates electron polarization with an
unpolarized nitrogen spin at weak mixing; strong mixing or nuclear polarization
can invalidate the contrast proxy. No excited-state polarization near 510 G is
predicted. Frequencies remain Hamiltonian predictions within its stated scope.

L(nu;nu0,Gamma) = 1/[1+4(nu-nu0)²/Gamma²], with Gamma explicitly FWHM.
F_k(nu) = 1-C sum_ab w_ab L_ab(nu). Combined fluorescence is the nonnegative
orientation-weighted average, weights normalized to sum to one. C is an assumed
bright-to-dark contrast budget. It is NOT the fitted contrast of every hyperfine
line. No per-spectrum maximum normalization hides selection-rule suppression.
DRE2011 Eq. (1), p. 195204-2 motivates the fluorescence-dip representation;
choosing Lorentzian broadening here is phenomenological. Grid resolution warnings
are shown when spacing exceeds FWHM/5; off-window resonances remain in CSV tables.

## O4. Energy levels and field sensitivity

Plots show sorted energy ranks relative to the lowest energy for that orientation
and field. Labels are ranks, not tracked ms/mi states; crossings can exchange spin
character. For nondegenerate states, dE_i/dB_k = <i|gamma_e S_k-gamma_n I_k|i>,
and transition slopes are differences of these expectation values (Hellmann-Feynman
identity, algebraic derivation from O1). The plotted gradient norm is invariant to
orthogonal coordinate changes; CSV components are in each local NV frame.
The norm is not the derivative of the four-orientation ensemble minimum.

## O5. Clock connection and original-versus-informed comparison

The original stochastic engine, clock transitions, seeds, compensation, and Allan
estimator are unchanged. At the CURRENT SIDEBAR clock bias, E=0 and temperature
297 K, the bridge identifies the same f+ and f- used in the original clock model.
It checks that each selected transition has an active ODMR counterpart and that
the nearest other active line (dip weight >1e-5) is at least 5 FWHM away. This is a
conservative numerical guard, not a proof that experimental line pulling vanishes.
Broader overlapping-line operation is rejected, not passed into an isolated-line
formula. A future full-spectrum estimator would need a defined fit/lock protocol.

For the low-contrast resolved Lorentzian at its optimum slope, DRE2011 Eqs. (2)-(3),
printed p. 195204-2 give ideal frequency-noise amplitude

eta_nu = [4/(3 sqrt(3))] Gamma / [C_line sqrt(R d/2)]  [Hz sqrt(s)].

R is detected photons per live second, d is live-time fraction, and each of the two
clock electronic lines gets half the available time. C_line is a SEPARATE user
assumption for each addressed line, not inferred from the ensemble proxy C. The
estimate assumes a known fluorescence baseline, optimal frequency placement,
independent Poisson detection, negligible technical noise and no extra reference
measurement overhead. It models neither a full frequency scan nor a feedback servo.
Default field/linewidth/contrast/rate settings have not been fitted to hardware.

Set per-line electron_readout_Hz = eta_nu at 1 s in a COPIED Config. The existing
engine uses sigma_nu(dt)=eta_nu/sqrt(dt). For contiguous independent white frequency
samples, sigma_y(tau)=eta_nu/[nu_reference sqrt(tau)] for a single transition.
This follows the existing overlapping Allan estimator (NIST2008 Eq. (10)). It is
not a conversion of the line's FWHM directly into jitter. Existing normalization
by each observable, pair averaging and composite weights are preserved. Independent
photon readout requires paired correlation zero; other settings are rejected so
nuclear correlation is not silently changed. All other Config fields, including
nuclear readout and LO noise, remain identical; same seeds pair all random streams.
Only electronic readout sigma changes. Baseline outputs are never overwritten.

The four-orientation spectra are NOT automatically fed into a single-NV clock lock.
Spectroscopy controls and clock bias are deliberately explicit in the UI and export.
The comparison assesses readout assumptions; it is not an independently validated
new clock, nor evidence of improved accuracy. A worse Allan curve is a valid result.
Linewidth does not determine environment RMS, OU correlation time, nuclear readout,
LO noise, Dick effects or servo response. No confidence bands are inferred from a
single paired record.

## O6. Reproduction, attribution and validation

Run `python scripts/run_odmr.py --out outputs/odmr-new-run --compare --samples 4096`.
Every output directory must be new. JSON files record full spectroscopy/readout/
clock/Physics/Stark inputs, seeds, capture time, Git state and source hashes. The
bundle contains CSV data, SVG/PDF figures, parameter/equation mappings, the exact
reference catalog and source snapshots, including the archived MATLAB transcript.
Checksums cover every member. All exported curves are explicitly labeled simulation;
no digitized literature spectrum or measured performance is included.

`legacy/matlab/` acknowledges the original intern and retains the supplied, broken
MATLAB transcript (whitespace-normalized, not an original byte-identical .m file).
Python repairs disabled hyperfine/quadrupole terms, absent electric coupling,
missing coordinate functions, conjugation, |amplitude|^4 versus |amplitude|²,
self-transitions, sorting, FWHM/grid definitions and naming errors. Constant energy
offsets such as subtracting 2I/3 are harmless for transition frequencies.

The new tests check known limits, units, rotations, grouping, selection rules,
finite-difference sensitivities, white-noise averaging, input rejection, unchanged
original engine/baselines, old dashboard flows and new reproducible exports. They
establish numerical consistency, not experimental validation. See ODMR_VALIDATION.md.

## Original MATLAB parameter comparison

| Quantity | Supplied MATLAB | Shared Python default | Decision |
|---|---:|---:|---|
| D at reference temperature | 2870 MHz | 2870.280 MHz | Retain sourced L2023 coefficient |
| A_parallel | -2.14 MHz | -2.165190 MHz | Retain sourced coefficient |
| A_perp | -2.7 MHz | -2.635000 MHz | Retain sourced coefficient |
| Quadrupole | -4.95 MHz | -4.945880 MHz | Retain sourced coefficient |
| Electron gamma | about 2.803195 MHz/G from rounded constants | 2.803300 MHz/G | Reuse existing convention and provenance |
| Nitrogen gamma | about 307.969 Hz/G with positive sign in unused Hnuc | 307.59 Hz/G with minus sign | Reuse existing nuclear convention |
| Electric coefficients | 3.5e-9 and 0.17e-6, units not declared | 0.0035 and 0.17 Hz/(V/m) | MATLAB numbers are consistent with MHz/(V/m), but its electric terms were absent |
| Geometry | 18 G, theta=3pi/8, phi=3pi/7 in NV4 | `examples/odmr_intern_geometry.json` | Preserve same nominal B geometry for comparison; all four frames retained |
| Nuclear terms | Constructed incorrectly, then excluded | Full 9x9 Hamiltonian | Enabled through original tested Python engine |

The example geometry matches the intern's stated intent; numerical agreement with
the broken transcript is not claimed. Refined constants and enabled hyperfine terms
will change peak positions from a repaired electron-only MATLAB calculation.
