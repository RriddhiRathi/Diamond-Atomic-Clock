# ODMR equation and implementation map

| ID | Equation / parameter | Source and locator | Python implementation | Evidence |
|---|---|---|---|---|
| O1a | Full 14NV H/h; D,Q,A, gamma | L2023 Eq. (1), p. 064084-2; Table II, p. 064084-5; existing F2009 gamma mapping | physics.hamiltonian, physics.Physics; odmr.spectroscopy_hamiltonian | Existing literature coefficients; local thermal expansion |
| O1b | Static Stark Hamiltonian | D2012 Eq. (24), p. 205203-7 | odmr.spectroscopy_hamiltonian | Published weak-static-field model, chosen transverse axes |
| O1c | d_parallel = 0.35(2), d_perp=17(3) Hz cm/V | D2012 Sec. II B, p. 205203-6: before Eq. (17), after Eq. (16); original experiment V1990 linked, not numerically reverified | odmr.Stark, odmr_parameter_provenance | Literature-quoted values; 1/100 conversion to Hz/(V/m); no uncertainty propagation |
| O2a | Four proper lab-to-NV rotations | MATLAB_INTERN supplied matrices; R R.T=1 and det R=1 are numerical checks | odmr.ROTATIONS, transform, spherical | Original intern implementation; crystal-axis convention assumption |
| O2b | Magnetic-dipole strength | Magnetic perturbation of O1a; corrected intern transition intent; modulus-square rule | odmr.microwave_operator, transition_table | Algebraic magnetic-dipole calculation; relative strengths, not optical rates |
| O2c | Degenerate manifold strength Frobenius norm | MODEL: sum of modulus squares over orthonormal states | odmr._groups, transition_table | Basis-invariant algebraic grouping; 1e-5 Hz numerical tolerance |
| O3a | Fluorescence dip and Lorentzian FWHM | DRE2011 Eq. (1), p. 195204-2; MODEL multiple-line sum | odmr.lorentzian, spectrum | Phenomenological Lorentzian assumption |
| O3b | Brightness-weighted populations and equal-default orientation weights | MODEL docs/ODMR_METHODS.md O3 | odmr.transition_table, spectrum | Explicit unvalidated optical/population proxy |
| O4 | Hellmann-Feynman magnetic gradient | MODEL: differentiate O1a for nondegenerate eigenstates | odmr.transition_sensitivities | Derived identity; finite-difference verification; degenerate slopes undefined |
| O5a | Ideal eta_nu, Lorentzian prefactor 4/(3 sqrt(3)) | DRE2011 Eqs. (2)-(3), p. 195204-2 | odmr_bridge.readout_eta | Low contrast, resolved line, optimal slope; R, contrast, duty and linewidth assumed |
| O5b | Half live time per line, 5 FWHM isolation, independent photon readout | MODEL: explicit measurement protocol and conservative guard | odmr_bridge.resolved_clock_readout | No full-spectrum fit or servo validation |
| O5c | sigma_nu=eta_nu/sqrt(dt); sigma_y white-FM limit | MODEL independent interval averages; NIST2008 Eq. (10), printed p.16 | unchanged simulation.simulate and stability.overlapping_adev; odmr_bridge.compare_stability | Conditional simulation and estimator identity |
