# Atomic clock comparison: value → source → display

This is literature/context, not experimental validation of an NV clock. The page
uses one existing simulation and three rounded conventional-clock guide values.
The new catalog ID `NIST_ATOZ` is an authoritative NIST glossary, not a report of
one matched experimental campaign. Existing catalog records and verification labels
are unchanged. The source was checked on 2026-10-29 against both the NIST PDF and
its matching web entries. The 2010 catalog year denotes the original web-entry
creation date; the linked PDF itself is undated. The web entries list a 2023 update.

| Displayed item | Numerical source and exact locator | Treatment |
|---|---|---|
| Cesium beam | `NIST_ATOZ`, Cesium Beam Oscillator, printed p.8 (PDF page 8): typical stability 5×10⁻¹² at 1 s | ≈5×10⁻¹² at τ=1 s; isolated open-square symbol; not a fountain result |
| Rubidium vapor cell | `NIST_ATOZ`, Rubidium Oscillator, printed p.41 (PDF page 41): typical stability 1×10⁻¹¹ at 1 s | ≈1×10⁻¹¹ at τ=1 s; isolated cross symbol |
| Hydrogen maser | `NIST_ATOZ`, Hydrogen Maser, printed p.25 (PDF page 25): typical stability less than 1×10⁻¹² at 1 s | <1×10⁻¹² at τ=1 s; downward open triangle at the bound; not an exact point |
| NV feedback and free-running output | `MODEL` / dataset alias `DC7`: `outputs/clock_phase4_20261024/7/complete_research_bundle.zip`, `allan_SIMULATION.csv`, `config.json`, `summary.json`, original `metadata.json` and source snapshot | Exact saved full-record overlapping ADEV samples only, with drift, acquisition and failures retained. Table uses the longest valid exactly matched τ (3.16 s). No interpolation or extension beyond the record |

The NV bundle SHA256 is
`7824c92e8274413cab1d8b7911c2556df02eec0b1c94d10d835a49579367684f`.
It is pinned in `references/clock_comparison.json`; the existing archive reader also
verifies its manifest, numerical table hashes and captured configuration. No archive
is changed or regenerated. `DC7` identifies a simulated dataset, not an added paper.
The model attribution remains `MODEL`; relevant original methods and references
are retained in that bundle and the existing clock equation map.

NV configuration: seven-state Lindblad, local axial 20 G, 297 K, 100 independent
detected centers, 10 ms gates, 512 feedback cycles, seed 410024. This is the existing
drift-stress example with assumed free-oscillator drift 10000 Hz/s, not typical
oscillator hardware or a fundamental NV stability limit. The table computes
its feedback/free ratio from matching positive saved values. Improvement at the
selected τ does not imply improvement over the entire curve. The optional quieter-LO
negative example remains in Clock Performance; it is not added to this compact page.

## Source links and statistical scope

- [NIST glossary PDF](https://tf.nist.gov/general/pdf/1548.pdf)
- [Cesium entry](https://www.nist.gov/pml/time-and-frequency-division/popular-links/time-frequency-z/time-and-frequency-z-c-ce)
- [Rubidium entry](https://www.nist.gov/pml/time-and-frequency-division/popular-links/time-frequency-z/time-and-frequency-z-re-ru)
- [Hydrogen entry](https://www.nist.gov/pml/time-and-frequency-division/popular-links/time-frequency-z/time-and-frequency-z-h)

The glossary defines Allan deviation (printed p.2) and describes its use for stability
(printed p.43), but the three oscillator entries do not specify per-device sampling,
confidence intervals, estimator variants or experimental conditions. Accordingly,
they are labeled reported representative fractional stability, not certified exact
matches to the simulator's overlapping ADEV. No raw literature curve is digitized,
no guide value is rescaled to another τ, and no conventional-clock curve is invented.
No systematic accuracy uncertainty is plotted as stability. The optional optical
clock and cesium-fountain categories are omitted from this minimal page rather than
mixing additional estimators or extrapolated coefficients.

Implementation: `diamondclock/clock_comparison.py`; data:
`references/clock_comparison.json`; source record: `references/sources.json`.
The page's Paper Bucket action opens this map directly in the existing map selector.
New source metadata participates in the existing JSON/BibTeX catalog exports.

## Availability and reproduction

Update `feature/dashboard-redesign`, then launch with
`python -m streamlit run app.py --server.port 8502`. Select **Atomic Clock Comparison**.
Opening it reads the saved archive and packaged reference data; it never calculates
a clock or alters session experiment settings. Historical outputs are excluded from
wheels. If the original NV archive is missing, corrupt or has a different hash, the
page explicitly reports the NV result as unavailable and shows only the literature
points; it does not silently regenerate a result. Existing source/configuration checks
and original research workspaces are unchanged.
