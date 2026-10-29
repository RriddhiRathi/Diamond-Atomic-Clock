# Dashboard Part 3: recovered ODMR demonstration

Continues Part 2 `cb49ce9` using the preserved `nv_spectroscopy.py` and
`nv_dashboard.py` draft. The original draft remains outside the repository at
`/workspace/scratch/4e2075578020/part3-draft/` in the recovery environment.
Run the existing app and choose Demonstration Mode → NV-Center Demonstration.

## Scientific integration

`nv_spectroscopy.cached_spectrum` calls the unchanged `odmr.spectrum()` once per
field vector, selected orientation and source fingerprint. This reuses the existing
9×9 electron/nitrogen-14 Hamiltonian, four frame transformations, degeneracy-aware
transition table and Lorentzian transition-strength fluorescence proxy. It does
not call the slower energy/field sweep, gradient or clock-comparison workflows.
The cache holds at most 16 configurations. No new scientific solver is introduced.

The lab B vector is exactly the vector constructed by Part 2's `magnetic_field`
and drawn in the lattice. Each selected orientation uses the same `ROTATIONS`
frame. Microwave polarization is local +x of the selected NV, transformed to lab;
it is a direction, not calibrated power. One-hot weights select that NV for the
primary curve and fluorescence indication. The optional other-orientation curves
are separate comparisons, not an ensemble brightness assigned to the single defect.

The default remains aligned 20 G, 297 K, E=0. Controls cover 0–50 G and any field
angle. The GHz plotting window uses the existing dashboard's conservative coverage
bound D ± (gamma_e |B| + 20 MHz), not an estimate of individual resonance positions.
Actual transition centers come from the engine table. Only centers inside this GHz
window with dip weight >1e-8 receive rug markers; the full calculated GHz curve
retains all engine contributions. Nuclear-frequency transitions are outside this
electronic ODMR window. Degenerate/overlapping transitions are not artificially
split; their centers can differ from a combined fluorescence minimum.

FWHM 0.3 MHz, contrast budget 0.03 and the proxy brightness model remain existing
scenario assumptions. The 10001-point grid gives approximately 4–32 kHz spacing
over the allowed field range. Source references: L2023 (ground-state Hamiltonian),
D2012 (spectroscopy), DRE2011 (ODMR context), TET2012 (separate optical cycle).
See also `references/nv_odmr_demo_map.md` and existing ODMR/optical equation maps.

## Frequency, readout and overlays

The frequency selector uses GHz; calculation and interpolation use Hz. Its bounds
come directly from the calculated grid. Initial selection is the lowest sampled
fluorescence point. Later field changes retain the frequency if in range, otherwise
clamp it to the new domain. No resonance rounding or automatic dip tracking occurs.
The slider uses a 100 Hz step; this is control granularity, not physical resolution
or a frequency-estimation uncertainty. Endpoint round trips accept only an eight-ULP
floating-point tolerance. Meaningful out-of-range queries are rejected.

Fluorescence at the selector is piecewise-linear interpolation of the primary
spectral grid. The marker uses that same value; there is no new line fit or
extrapolation. Moving the selector, hiding overlays, or navigating does not rerun
the engine. `nv_` session keys preserve input state; the source fingerprint and
captured source context still gate cached scientific values.

Laser-on/MW-on indication follows the interpolated proxy. MW-off uses its defined
normalized reference of 1. Laser-off emission is **not modeled**, rather than being
reported as a calculated zero photon rate. The conditional MW-on curve remains
visible for explanation in either case. Green excitation, red emission and purple
microwave arrows are optional static cartoons, not EM propagation, polarization
vectors, photon trajectories or measured light. Red arrow opacity uses the same
normalized displayed signal without exaggeration. No particle statistics or
continuous animation is generated; motion is limited to user-controlled rotation.

## Detailed optical readout and clock limitations

Seven/21-state optical-cycle calculations are deliberately not coupled to this
proxy. `optical_scope` checks the selected local field against the existing
positive axial 5–50 G, E=0, 297 K domain, explicitly rejecting off-axis, zero and
reversed fields. This is a domain diagnostic, not a solver call. Even supported
fields require a separately configured run in Advanced Research → Optical
measurement. Its expected/sample photon counts, detector parameters, solver and
seed remain unchanged. No mapping between its contrast and the Lorentzian proxy
has been validated. There are no synthetic photon counts on the primary demo page.

An ODMR dip alone does not demonstrate a lock, improved Allan deviation, accuracy,
or experimental clock performance. The existing Clock Performance workflow is
separate. Part 4, new scientific outputs, historical archive regeneration, merges
and Streamlit deployment are outside this change.

## Reproducibility and validation

The parameter download records the engine config, selected frequency, switches,
interpolated/displayed signal, domain diagnostic, source fingerprint, source file
hashes and calculation Git state. Existing Paper Bucket records are unchanged;
full research exports remain in their existing workspaces.

Tests compare the adapter's curves and transition tables to the existing engine
for all four orientations, verify vector consistency, zero field, units, marker
positions, interpolation/boundaries, deterministic data, and unsupported optical
domains. An AppTest counts engine calls across frequency/view/navigation changes.
All original numerical, export, packaging and navigation tests remain in the suite.
The earlier 3D-page assertion now expects two plots and the new spectroscopy label;
its guards against optical/clock execution and state-loss assertions are retained.
