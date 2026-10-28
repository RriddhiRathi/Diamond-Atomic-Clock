# Dashboard redesign — Part 1

Base: `7311f8722d289352541001e630409f83f1adcc61` on Phase 4.
Branch: `feature/dashboard-redesign`. The entry command remains
`python -m streamlit run app.py`. No deployment or merge is included.

## Navigation and modes

The sidebar selects one of four sections. Demonstration Mode is the default;
it guides the scientific story and reads completed session results. Research Mode
exposes the existing scientific forms. Switching modes never submits a form.

| Section | Part 1 contents | Later redesign work |
|---|---|---|
| Clock Overview | Research objective, scientific sequence, starting configuration, validated last-run clock metrics and conditional interpretation | Consolidated configuration and deeper interpretation |
| NV-Center Demonstration | Part 2 now adds a rotatable diamond lattice, one N/vacancy pair, four NV-axis overlays and geometric field controls; see [NV_VISUALIZATION.md](NV_VISUALIZATION.md) | Live ODMR/fluorescence integration in Part 3; any optical animation must be labeled schematic |
| Clock Performance | Existing photon-clock controls/results/exports in Research Mode; read-only completed-run metrics and shared full-record Allan plot in Demonstration Mode | Focused acquisition, correction, lock, phase/time and stability layout |
| Advanced Research | All existing tools, grouped into four workspaces, available in Research Mode | Progressive disclosure of detailed controls |

## Inventory of preserved features

| Existing feature | Destination and access |
|---|---|
| Stability lab: five reference signals, published bounds and theoretical projections | Advanced Research → Stability & compensation → Stability lab |
| Temperature/field/oscillator inputs and environment/transition diagnostics | Same workspace → sidebar controls and Environment & transitions |
| Compensation equation, sensitivity, seeded ensemble and percentile bands | Same workspace → Compensation study |
| Nitrogen-14 Hamiltonian, NV explanation, Allan-deviation interpretation | Same workspace → NV center explained; conceptual introduction also in Demonstration |
| Persistent Paper Bucket: search/add, verification labels, JSON/BibTeX, parameter/equation maps | Same workspace → Research Paper Bucket |
| Baseline CSV/source/config/provenance/checksum/vector exports and methodology | Same workspace → Export & methodology |
| Four-orientation ODMR, electric/magnetic fields, polarization/weights, spectra, levels, gradients, paired readout comparison | Advanced Research → ODMR spectroscopy |
| Original intern MATLAB transcript, attribution and ODMR vector/research exports | Same ODMR workspace, attribution expander and export controls |
| Seven/21-state optical fluorescence, populations/counts/contrast, benchmarks and bundles | Advanced Research → Optical measurement |
| Photon acquisition, controller, oscillator, lock fraction, Allan table and full research bundle | Clock Performance in Research Mode, or Advanced Research → Frequency lock |
| Completed session clock metrics and conditional interpretation | Clock Overview; also Clock Performance in Demonstration Mode |

The optional ODMR paired-clock comparison uses the last configuration from
Stability & compensation, or the original `Config` defaults if that workspace has
not been configured. Optical and photon-clock controls remain independent of the
original 475 G stability scenario. No model domains or defaults were changed.

## Entry points and reusable components

- `app.py`: page configuration and the single `render_dashboard()` entry point.
- `diamondclock/dashboard.py`: navigation, mode, landing page, read-only summary,
  route dispatch and persistent workspace input state.
- `diamondclock/legacy_dashboard.py`: original six stability/reference/export tabs,
  moved from `app.py`; `cached_run` and `cached_ensemble` retain source-aware caching.
- `diamondclock/odmr_dashboard.py`: existing `render_odmr` / `cached_odmr`.
- `diamondclock/optical_dashboard.py`: existing `render_optical` / `cached_optical`.
- `diamondclock/clock_dashboard.py`: existing `render_clock` / `cached_clock`;
  `render_clock_stability` factors out the original plot for reuse in Demo Mode.
- Existing Plotly charts, scientific reporting/export functions, source validation,
  reference catalog and package asset discovery are reused.

## Computation and persistence

Overview, Demonstration and Demo Performance never calculate a simulation. Only
the selected Research workspace renders; hidden ODMR/optical/clock forms do not
execute. The original stability workspace still loads its source-cached baseline
when explicitly opened. Ensembles, other experiments and exports require their
existing submit buttons. Navigation and mode are not calculation cache keys.

Explicit widget keys and keep-alive state retain committed inputs across hidden
routes. Button events are excluded so navigation cannot replay a calculation.
Results, ensembles and prepared exports remain in session state; parameter/source/
catalog checks still gate their use. Overview labels its summary as the last
completed run with that run's saved configuration, not pending edits in another form.
The read-only view validates captured source before presenting any results.
State is session-local, not persistence across server restarts or new browser sessions.

## Validation and scope

Existing UI regression tests now enter through public navigation; their calculation,
comparison, reference persistence and export assertions are preserved. New tests
check all routes without calculation, one actual clock run across modes/routes,
input/export retention and rejection of a stale source result. The full suite also
checks unchanged physics, historical output blobs, provenance and clean packaging.

Part 1 originally established the shell. Part 2 supplies the educational 3D lattice;
no live spectrum integration, optical animation, new scientific model, regenerated
research output or full performance redesign is included yet.
