# ODMR integration validation

Date: 2026-10-24. Base working branch commit:
`14fe3dcd68d3a2b8fbe04d2b1580dce29b301867` (provenance improvements).

The initial unmodified project passed all 33 tests locally. After integration,
the complete suite passes **56 tests** on Python 3.12/Linux. The PR workflow also
runs Ubuntu and Windows/Python 3.12. Check its final status for platform results.

New checks cover proper tetrahedral rotations and round trips; direct equality to
the old Hamiltonian when By=E=0; Hermiticity; azimuthal invariance at E=0; analytic
uncoupled Zeeman/Stark eigenvalues; Hz/MHz and electric unit conversions; microwave
selection rules and squared strengths; invariance under complex basis changes in
degenerate manifolds; Lorentzian FWHM; normalized orientation averaging; exact grid
length; active hyperfine components; analytic gradients versus central differences;
photon-rate/contrast/duty scaling; white-FM Allan limit; input/scope rejection;
full source/parameter/reference traceability; checksummed SVG/PDF/CSV/ZIP exports;
CLI reproduction and overwrite refusal; and integrated dashboard interactions.

Paired comparison tests establish identical temperature, magnetic field, oscillator
noise, nuclear readout and clock transition traces. Matching electronic readout
sigma produces identical original/informed traces. No equations in physics.py,
simulation.py or stability.py were changed. Historical results and original root
checksum manifest are protected by their existing regression and Git blob checks.

A new illustrative example is supplied under `outputs/odmr_demo_20261024/`. The
complete self-contained bundle is `research_bundle_SIMULATION.zip`; selected vector
figures and CSVs are also exposed alongside it. It uses 18 G in the intern's NV4
geometry, 297 K, E=0, 0.3 MHz FWHM, spectral contrast budget 0.03 and equal orientation
weights. Its separate 4096-sample clock comparison uses the default 475 G clock
scenario, 0.03 per-line contrast, 1e6 detected photons/live second, full duty factor
and half live time per line. The implied ideal electronic sigma is about 10886.6 Hz
at 1 s, versus the original illustrative 50 Hz. That is a more pessimistic input,
not an observed degradation or a measured result.

Each example archive retains its own code snapshot and Git dirty state. It is an
immutable capture of the actual calculation, not a claim that generated results
were computed from the eventual clean PR merge commit. New results must use new
output paths. Exact PDF byte-for-byte reproduction is not promised across runtimes;
numerical inputs, core versions, arrays and source snapshots are supplied.

The four exported PDFs were rendered with Poppler and inspected for clipping,
labels, legend readability and simulation disclaimers. Neither these tests nor
figure review validate the optical population model, experimental photon collection,
feedback, noise assumptions, or sample-dependent coefficients against apparatus.
There is no experimental dataset or literature spectrum fit in this extension.
