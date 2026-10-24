# Phase 3 scientific and numerical validation

Seven-state implementation was tested before extension: first 5 optical tests passed.
The final test record and committed dataset README report the final complete suite.
Tests validate calculations within model assumptions, not hardware or clock accuracy.

Checks include published NV E total-lifetime consistency; analytic exponential singlet
and excited decay; population normalization and Lindblad trace conservation; density
positivity; rate/master transient agreement with MW off; coherent Rabi cycles and
Hz/rad conversion; ISC polarization and disappearance of readout contrast when channels
become spin symmetric; weak-drive Bloch-rate limit; exact original 14N ground matrix;
nuclear-spectator seven-state reduction; hyperfine line structure; 475 G and other
scope rejection; number-resolved probability mass, expected-count identity, detection
thinning and non-Poisson counts; no second radiative event without repumping; sampled
statistics with sample-size-aware tolerances; Poisson fast mode; seeded reproduction;
complete optical config/source/table binding; checksum coverage and CLI overwrite
refusal; app integration; unchanged historical Git blobs and clock engine.

Exported solver_benchmarks compares Lindblad and approximate rate populations/emission
at B=5,20,50 G, W=1,4 million/s and Rabi=0,20,200 kHz for the electronic model. This
grid is a numerical comparison, not a validation of all continuous settings or of
all 21-state approximations. Number-resolved references use the scenario inputs in
summary.json; single-emitter ideal-efficiency statistics are intentionally compared
with (and can depart from) Poisson.

Examples use the same fitted published rates with nominal 297 K and B=20 G;
laser/detector/microwave/relaxation settings are explicitly assumed. No raw literature
counts were digitized, no parameters were fitted to synthetic data, and no paper
curve was silently relabeled as a new experiment. Optical uncertainty is not
propagated. Existing historical results are never regenerated or certified anew.

Figures are vector SVG/PDF with simulation labels, units, acquisition context and
full source/config bundles. New example runs must use fresh directories. Their
snapshots record the actual computation, including any dirty working tree, rather
than claiming calculation from a later clean publication commit.
