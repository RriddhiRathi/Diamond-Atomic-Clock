# Interactive NV visualization — dashboard redesign Part 2

Run the existing `python -m streamlit run app.py`, select **Demonstration Mode**
and **NV-Center Demonstration**. Research Mode offers the same educational page;
its controls remain independent of the scientific experiment workspaces.

The main Plotly WebGL view rotates with the mouse, zooms with the wheel and pans
with the toolbar. Carbon is a silver sphere mesh, substitutional nitrogen is blue,
and the vacancy is three amber wire circles around an empty carbon site. A teal
N→V arrow defines the selected axis; a thinner yellow arrow shows B. They overlap
when aligned, with distinct arrowheads. The main view defaults to the defect's
neighborhood to reduce clutter. Full context shows the same 3×3×3-cell cluster.

## Geometry and conventions

The conventional cubic basis is two FCC sublattices offset by `(1/4,1/4,1/4)`.
Lab axes are [100], [010], [001]. All coordinates use lattice units a, with no
new measured lattice constant. The construction contains 216 sites; one carbon
is replaced by nitrogen and one is removed, leaving 214 C + 1 N. Only actual
occupied-site pairs at `sqrt(3)*a/4` are joined. Interior pristine sites have four
tetrahedral neighbors, with direction dot products −1/3. Cluster boundaries have
truncated coordination, not modeled surface chemistry or extra NV vacancies.

Nitrogen is at cubic `(1.25,1.25,1.25) a`. The selected vacancy is a nearest
neighbor in one of the four existing ODMR local +z directions. This B-sublattice
choice lets all N→V axes agree directly with `odmr.ROTATIONS[:,2,:]` without
changing the validated ODMR frames. Plot coordinates are translated to put N at
the origin: `(r−r_N)/a`. The complete source/equation map is
[nv_visualization_map.md](../references/nv_visualization_map.md), also displayed
in the page's scientific-notes expander. AFLOW2017 is added to the Paper Bucket;
all existing reference records are retained unchanged.

The field controls use polar angle to the selected NV axis and azimuth in that
same NV x/y frame. The existing spherical and frame-transform functions construct
the lab B vector. The displayed angle and axial projection are derived from it,
not copied from slider labels. 1 G = 1e-4 T. At zero magnitude the angle is
undefined and its arrow is omitted. The 20 G aligned, 297 K starting example
matches the low-field optical-clock context. Off-axis geometry is educational,
not additional optical/clock validation or a solver configuration change.

## Controls and persistence

- Four selected NV orientations and optional overlays of the other three axes.
- B magnitude 0–50 G, polar angle 0–180°, azimuth −180–180°.
- Defect neighborhood versus full crystal context.
- Bonds, atom labels and ideal bond-length labels, hidden unless selected.
- Rotation, zoom, pan and a **Reset 3D view** button.

View/field changes do not call scientific solvers. `nv_` state keys retain
committed controls across navigation. Reset has its own transient button key;
it increments the Plotly scene revision to restore the initial camera without
changing field, orientation or scientific results. Camera orbit is preserved
across ordinary control changes via scene `uirevision`; cross-page persistence
of a browser-only camera orbit is not guaranteed. Field/option state is session-
local, as in Part 1.

## Architecture and limitations

`nv_visualization.py` separates lattice generation, connectivity, defect placement,
NV-frame/vector math and Plotly construction. `nv_dashboard.py` only renders UI.
The existing dashboard shell routes here and preserves the new input keys. No
scientific solver, historical output archive or saved PDF/SVG is modified.

Low-poly sphere meshes are batched into carbon/nitrogen traces; the full view has
only 215 occupied sites. Radii, arrow lengths and colors are schematic, not atomic
radii or a shared scale between field strength and real-space distance. Arrows
show direction; read the numerical panel for magnitude. Atom labels can clutter
the full view, so they default off. Other orientation overlays are alternative
axes, not extra nitrogen atoms or vacancies.

This is an ideal, unrelaxed bulk geometry cutout. It omits charge/spin density,
defect relaxation, strain, surface termination, optical ray tracing and quantum
dynamics. There is no atomically resolved experimental image. Plotly 3D requires
WebGL; 3D PDF/SVG export is not promised. Its camera toolbar/PNG snapshot is for
the educational illustration, separate from the simulator's research exports.
No new dependencies or frontend framework are introduced. Parts 3 and 4 remain
out of scope: no new live spectrum, optical animation or clock-performance layout.
