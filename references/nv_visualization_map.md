### Crystal geometry (not a quantum-dynamics result)

**Diamond basis.** Cubic lab axes x=[100], y=[010], z=[001]. In units of the
conventional cell edge **a**, the FCC sites are
`F = {(0,0,0), (0,1/2,1/2), (1/2,0,1/2), (1/2,1/2,0)}`.
Diamond has basis `F ∪ (F + (1/4,1/4,1/4))`, repeated by integer cubic
translations. The finite context contains 3×3×3 half-open conventional cells:
216 original sites. Only occupied-site pairs separated by `√3 a/4` are bonded.
There are no periodic wraparound bonds or bonds to the empty site.

Source: **AFLOW2017**, [diamond A4 prototype, cF8, space group 227](https://aflow.org/p/A_cF8_227_a-001/).
AFLOW uses a different origin; translating its cubic coordinates by `(1/8,1/8,1/8)`
and reducing modulo cubic translations gives the same two FCC sublattices.
The zero/quarter basis and nearest-neighbor separation are
also explicitly shown in [TU Wien, Basic Properties of the Diamond Structure](https://www.iue.tuwien.ac.at/phd/ungersboeck/node27.html),
text around Eq. (3.21). No numerical lattice constant is assumed: all lengths use a.

**One NV pair.** Nitrogen substitutes the site `(5/4,5/4,5/4)`. Exactly one
adjacent carbon is removed: `r_V = r_N + (a/4) s_k`, where `s_k` is one of
`[-1,1,1]`, `[1,1,-1]`, `[-1,-1,-1]`, `[1,-1,1]`.
The directed axis **n = (r_V − r_N)/|r_V − r_N|** points **N → vacancy**.
These are the existing `odmr.ROTATIONS[:,2,:]` axes in the same order, not a
new spin-frame convention. Nitrogen has three remaining nearest-neighbor carbon
bonds. The vacancy wire marker is not an atom; the NV arrow is not a chemical bond.
Changing orientation moves the single removed site; overlays show alternative
axes, not additional defects. The atomic structure is ideal and unrelaxed.

**Field geometry.** Angle θ is measured from the selected NV +z axis; azimuth φ
is measured from that NV frame's +x toward +y, using the existing ODMR frames.
`B_NV = B (sinθ cosφ, sinθ sinφ, cosθ)` and `B_lab = R_k.T @ B_NV`.
The drawn B arrow is parallel to this actual lab vector. The displayed angle is
`acos(clip(B_lab·n/|B_lab|,−1,1))`, the signed axial projection is `B_lab·n`,
and **1 G = 10⁻⁴ T**. At B=0 the direction/angle is undefined and no B arrow
is drawn. The default is aligned 20 G at nominal 297 K; only 0–50 G is offered.
Off-axis controls are geometric, not an extension of the validated axial optical
clock domain. Changing these controls never runs or updates an ODMR/clock experiment.

### Conceptual educational explanation

For the negatively charged NV⁻ electronic ground state, S=1 and the zero-field
splitting is approximately 2.87 GHz at the project's reference temperature
(**L2023**, Eq. (1), `physics.Physics.D0_Hz`; **D2012**, spin Hamiltonian).
Field orientation sets both axial and transverse Hamiltonian components. Optical
preparation/readout and microwave driving provide spin-dependent fluorescence
(**TET2012**, optical cycle; **DRE2011**, ODMR). This page does not calculate
level shifts, a spectrum, photon counts, charge density or quantum dynamics.

### Actual simulated numerical results

These remain in **Advanced Research** and **Clock Performance**. The 3D page's
only numerical quantities are crystal coordinates and field-vector geometry;
they are not simulated clock results or experimental imaging. Atom radii, colors
and vector lengths are schematic. The finite cluster is not a macroscopic crystal
or a modeled surface. The default neighborhood is a crop of the same context.

Implementation and tests: `nv_visualization.py` (basis, connectivity, defect,
frames, vectors, Plotly); `nv_dashboard.py` (UI only);
`tests/test_nv_visualization.py`, `tests/test_app_nv.py`.
