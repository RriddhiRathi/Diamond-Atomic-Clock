# Phase 4 equation -> source -> implementation

| ID | Process and source scope | Implementation / tests |
|---|---|---|
| CLK1 | Plant/observer firewall, public frequency coordinates and unknown sample offset: MODEL architecture, not an absolute SI measurement | count_observations.py; AST/API and blinded estimator tests |
| CLK2 | Existing TET2012/PAN2024 optical model; closed-sector matrix exponential and count integral are project algebra | clock_plant.py; full Liouvillian equality, sequential optical comparisons |
| CLK3 | Phase/time/fractional frequency: NIST2008 Sec.2; finite-band noise generation and LO timing are MODEL discretizations | oscillator.py; scheduler; noise/phase/gate identity tests |
| CLK4 | Poisson likelihood from HIN2018 measurement framework; empirical Lorentzian family and profile/delta-method treatment are project estimator choices | frequency_estimation.py; matched and physical Monte Carlo |
| CLK5 | Integrating-servo principles: PEIK2006 Sec.6 and LER2017 servo analysis; our positional PI, limits, gains and lock logic are MODEL | clock_controller.py; clock_simulation.py; delayed/unstable/low-count cases |
| CLK6 | Existing NIST2008 Eq.(10) overlapping ADEV; SCH2017 documents dead-time aliasing context, not NV validation | stability.py unchanged; actual-output and independent AllanTools tests |
| CLK7 | Scientific source/config/data binding; explicit build and asset discovery: engineering choices and setuptools official documentation | clock_reporting.py; package/export regression |
| CLK8 | Optical/magnetic scope and all omitted apparatus physics: MODEL limits inherited from Phase 3 | CLOCK_METHODS.md; range rejection tests |

No optical-clock experimental instability number is used as an NV prediction.
HIN2018/PAN2024 accessible manuscript equation locators stay distinct from journal
metadata. New source records state accessible version and verification scope.
