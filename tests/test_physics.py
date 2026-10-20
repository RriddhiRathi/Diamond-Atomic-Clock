from dataclasses import replace
import numpy as np
from diamondclock.physics import Physics,hamiltonian,calibration,observables,composite_weights


def test_published_transition_calculations():
    # L2023 Table III at T=297 K, B=470 G. Rounded fitted parameters propagate
    # ~tens of Hz; 50 Hz tolerance is appropriate, not an experimental fit.
    c=calibration(470.)
    np.testing.assert_allclose(c['nominal_Hz'][2:4],[5_085_950.,4_799_650.],atol=50,rtol=0)
    np.testing.assert_allclose(c['slope_Hz_K'][2:4],[-35.2,-35.3],atol=.12,rtol=0)
    assert abs((c['nominal_Hz'][2]-c['nominal_Hz'][3])-286299.)<40


def test_hermitian_and_uncoupled_zeeman_limit():
    p=replace(Physics(),Apar0_Hz=0.,Aperp0_Hz=0.)
    h=hamiltonian(297.,475.,.3,p)
    np.testing.assert_allclose(h,h.conj().T)
    f=observables(297.,475.,p=p)
    np.testing.assert_allclose(f[:2],[p.D0_Hz+p.gamma_e_Hz_G*475,p.D0_Hz-p.gamma_e_Hz_G*475],atol=1e-5)
    np.testing.assert_allclose(f[4:],[p.D0_Hz,p.Q0_Hz],atol=1e-5)


def test_composite_preserves_lo_and_cancels_temperature():
    c=calibration()
    ld,lq=c['lambda_per_K'][[4,5]]
    wd,wq=composite_weights(ld,lq)
    assert abs(wd+wq-1)<1e-15
    assert abs(wd*ld+wq*lq)<1e-18
    assert 1.3<wq<1.5


def test_derivative_convergence():
    c=calibration()
    h=.02
    derivative=(observables(297+h,475)-observables(297-h,475))/(2*h)
    np.testing.assert_allclose(derivative,c['slope_Hz_K'],atol=.002,rtol=0)
