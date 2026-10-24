from dataclasses import replace
import numpy as np
import pytest
from diamondclock.physics import Physics, hamiltonian
from diamondclock.optical_parameters import OpticalConfig, OpticalRates
from diamondclock.optical_dynamics import build_system
from diamondclock.optical_cycle import steady_state, rate_steady, populations, liouvillian


def test_exact_existing_ground_hamiltonian_and_spectrum():
    c=OpticalConfig(states=21)
    s=build_system(c)
    np.testing.assert_array_equal(s.ground_hamiltonian_Hz,hamiltonian(297,20,0))
    np.testing.assert_allclose(s.ground_energies_Hz,np.linalg.eigvalsh(hamiltonian(297,20,0)),atol=1e-6,rtol=0)
    assert s.dimension==21
    rho=steady_state(s)
    assert np.linalg.eigvalsh(rho).min()>-1e-10
    assert np.linalg.norm(liouvillian(s)@rho.ravel(order='F'))<1e-4
    assert abs(sum(populations(s,rho).values())-1)<1e-10


def test_nuclear_spectator_reduces_to_seven_states():
    # Remove hyperfine/nuclear Zeeman only in a COPIED Physics for analytic test.
    p=replace(Physics(),Q0_Hz=0,Apar0_Hz=0,Aperp0_Hz=0,gamma_n_Hz_G=0)
    for rabi in (0,1e5):
        a=build_system(replace(OpticalConfig(),rabi_Hz=rabi),p=p)
        b=build_system(replace(OpticalConfig(states=21),rabi_Hz=rabi),p=p)
        pa=populations(a,steady_state(a));pb=populations(b,steady_state(b))
        np.testing.assert_allclose(list(pa.values()),list(pb.values()),atol=1e-9)


def test_21_optical_only_rate_agreement_and_hyperfine():
    s=build_system(replace(OpticalConfig(states=21),rabi_Hz=0))
    np.testing.assert_allclose(np.diag(steady_state(s)),np.diag(rate_steady(s)),atol=2e-8)
    e=s.ground_energies_Hz
    assert len(np.unique(np.round(e,0)))==9


@pytest.mark.parametrize('changes',[{'Bz_G':475},{'Bz_G':0},{'Bz_G':51},{'temperature_K':298},
    {'pump_s':-1},{'rabi_Hz':2e6},{'states':9},{'pure_dephasing_s':float('nan')}])
def test_operating_scope_rejection(changes):
    with pytest.raises(ValueError):build_system(replace(OpticalConfig(),**changes))
