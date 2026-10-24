# Optical model equation -> source -> implementation

| ID | Equation/process | Source and exact scope | Code / validation |
|---|---|---|---|
| OPM1 | Seven-state optical cycle | TET2012 Sec.2.1, Fig.1, Eqs.(1)-(5); ROB2011 five-state lumping is context | optical_cycle.py; test_optical_seven.py |
| OPM2 | gamma_r,k0,kpm,q0,qpm fitted rates | TET2012 Table 1 printed p.9 NV E; total lifetimes derived | optical_parameters.py; lifetime tests |
| OPM3 | Incoherent pump/radiative/ISC/singlet jumps | HIN2018 accessible arXiv v1 Eqs.(5)-(13); general channel form; rates from TET2012 | optical_cycle.py:_assemble |
| OPM4 | Lindblad and rotating MW | PAN2024 accessible arXiv v1 Sec.II Eqs.(3)-(4); our Rabi convention independently tested | optical_cycle.py:liouvillian; Rabi test |
| OPM5 | Rate reduction and CW MW elimination | TET2012 Eq.(5); DRE2011 accessible arXiv appendix Eq.(16), algebraic steady-coherence elimination | rate_generator; exported solver grid |
| OPM6 | 21-state optical channels | MODEL extension, existing L2023 9x9 ground H; not validated by electronic-only papers | optical_dynamics.py; H overlap, spectator reduction tests |
| OPM7 | Counts/efficiency/darks; count-derived contrast | HIN2018 arXiv v1 Sec.III Eqs.(27)-(30) qualified approximation; background/N/efficiency are MODEL | optical_measurement.py; counting statistics tests |
| OPM8 | Number-resolved Lindblad counts | PAN2024 arXiv v1 Sec.II B; our detected-jump thinning/cutoff | photon_detection.py; mean, probability and short-gate tests |
| OPM9 | Provenance, scope and no servo | MODEL engineering choices; not experimental results | optical_reporting.py; tamper/stale/CLI tests |

Rates are s^-1. Existing H/h in Hz gets 2*pi only in coherent propagation.
Manuscript version/page locators and journal DOI metadata are distinguished in the Paper Bucket.
