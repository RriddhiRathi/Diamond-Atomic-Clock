# Unified dashboard: use and validation

Launch from the repository root with Python 3.12:

```bash
python -m pip install -e ".[dev]"
python -m streamlit run app.py --server.port 8502
```

## Navigation

| Page | Direct access |
|---|---|
| Overview | Scientific workflow, last valid session-run summary, saved examples, concise scope expander |
| NV-Center & ODMR | Existing 3D crystal and cached ODMR curve, field controls, selector and fluorescence proxy |
| Clock Performance | Existing explicit run form, six verified saved examples, acquisition, correction, phase/time, Allan analysis, diagnostics and exports |
| Research Tools | Stability & compensation, detailed ODMR, seven/21-state optical readout, frequency-lock diagnostics |
| Paper Bucket | Persistent catalog and verification labels, search/add, six equation maps, four parameter reporters, original MATLAB attribution, JSON/BibTeX |
| Exports & Documentation | Prepared session bundles, original archived ZIP/SVG/PDF outputs, reference exports and scientific methods |

The Demonstration/Research mode gate has been removed. Old session routes migrate
to the corresponding new label; only the obsolete `dashboard_mode` key is removed.
Inputs, completed results, cached functions, ensemble data and prepared exports keep
their existing keys. Source/configuration/catalog validity checks remain in force.
Results from older source snapshots are retained but cannot be presented as valid
current-source results. No source hash is rewritten to make an old run appear fresh.

Opening a page or changing research workspace never starts an optical, clock,
ensemble or stability experiment. Stability & compensation now also requires the
explicit **Run simulation** submit; previously it calculated a baseline on opening.
It stores the completed record independently of visible controls. A failed new run
retains the previous result. Reference pages call only the existing parameter-reporting
functions. NV field/orientation changes retain the Part 3 cached ODMR calculation;
frequency, zoom, overlay and other view changes reuse the spectrum.

## Readability and scientific integrity

- Compact headings, metric cards and page spacing use the existing dark theme.
- The 3D crystal and ODMR spectrum stay side by side on desktop. Geometry, spectrum,
  linewidth and contrast are unchanged. The optional selector-centered zoom changes
  only the x-axis viewport (±5 existing FWHM), with the exact displayed range labeled.
- Plotly figures share font, background, grid, axis and bounded horizontal legend
  settings. Clock comparison curves use distinct dash patterns and Allan markers,
  so the distinction does not depend solely on color. Published-bound markers remain
  labeled separately and are visible on the dark screen theme.
- Every tracking point is retained. Rejected cycles remain gaps. Reported 1σ remains
  in hover text and may be shown as error bars using the detailed uncertainty toggle;
  no uncertainties are rescaled or replaced with invented bands.
- Allan axes remain logarithmic. Actual points, full-record/fixed-window labels and
  exact matched-τ ratios are unchanged. The interpretation appears directly below
  the graph, including curve-crossing and lock-with-worse-stability outcomes.
- Screen styling does not alter existing publication exporters. Historical ZIP,
  CSV, SVG and PDF files are not regenerated or edited.
- Catalog verification labels and source provenance are unchanged. MODEL/project
  methods are distinguished from literature support; user references remain unverified
  and unmapped. Unknown source IDs are explicitly marked as mapping gaps, with no
  inferred citation. Source equations/constants remain in the original map files.

Prepared export downloads in the hub preserve original source, configuration and
reference-catalog checks. Archived downloads verify the original checksum manifests
and numerical-table bindings. The hub reads existing outputs; preparing a new bundle
remains an explicit action in the relevant workspace. CSVs, references, captured source
and MATLAB attribution remain inside the complete research bundles.

## Validation scope

Streamlit AppTest checks cover the six routes, direct configuration and references,
all research workspaces, state migration, one explicit stability run across pages,
clock/export retention, source rejection and no unintended expensive calculations.
Plot tests check logarithmic axes, scientific tick formatting, distinguishable curves,
uncertainty visibility with identical arrays, and viewport-only spectrum zoom.
The full existing scientific regression suite and clean editable/wheel installation
checks remain required.

**Browser visual validation is incomplete in the Work environment.** The available
browser reported `ERR_CONNECTION_REFUSED` for the running workspace server at
`http://localhost:8502`; no local Chromium/Firefox/WebKit binary was installed.
No browser download was retried and no screenshots were claimed as reviewed.
CSS/Plotly settings and Streamlit interaction tests do not prove that legends or
controls are unclipped at every viewport.

Before presentation, inspect all six pages locally at 1366×768 and 1920×1080. Check
legend bounds, control grouping, metric wrapping, table width, plot zoom, keyboard
focus and scrolling. No merge or deployment is included in this UI refinement.
