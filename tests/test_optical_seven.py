from dataclasses import replace
import numpy as np
from scipy.linalg import expm
from diamondclock.optical_parameters import OpticalConfig, OpticalRates
from diamondclock.optical_cycle import seven_state, liouvillian, steady_state, rate_generator, rate_steady, transient, populations


def test_published_rates_lifetimes_and_branching():
    r=OpticalRates()
    assert np.isclose(1/(r.radiative_s+r.isc_zero_s)*1e9,13.6986301369863)
    assert np.isclose(1/(r.radiative_s+r.isc_pm_s)*1e9,8.5689802913453)
    assert np.isclose(1/(r.singlet_zero_s+2*r.singlet_pm_s)*1e9,526.31578947)


def test_trace_generator_and_rate_reduction():
    s=seven_state(replace(OpticalConfig(),rabi_Hz=0))
    l=liouvillian(s);k=rate_generator(s)
    tr=np.eye(7).ravel(order='F')
    np.testing.assert_allclose(tr@l.toarray(),0,atol=3e-8)
    np.testing.assert_allclose(k.sum(axis=0),0,atol=3e-8)
    np.testing.assert_allclose(steady_state(s),rate_steady(s),atol=1e-12)
    times=np.linspace(0,2e-6,21);rr=transient(s,times)
    for t,rho in zip(times,rr):
        np.testing.assert_allclose(np.diag(rho),expm(k*t)@np.diag(s.initial()),atol=2e-11)
        assert np.linalg.eigvalsh(rho).min()>=-1e-10


def test_isc_polarization_and_generated_contrast():
    c=OpticalConfig();off=seven_state(replace(c,rabi_Hz=0));on=seven_state(c)
    po=populations(off,steady_state(off));pn=populations(on,steady_state(on))
    assert po['ground_zero']/(po['ground_zero']+po['ground_pm'])>.65
    assert pn['excited_zero']+pn['excited_pm'] < po['excited_zero']+po['excited_pm']
    equal=OpticalRates(isc_zero_s=20e6,isc_pm_s=20e6,singlet_zero_s=1e6,singlet_pm_s=1e6)
    a=steady_state(seven_state(c,equal));b=steady_state(seven_state(replace(c,rabi_Hz=0),equal))
    np.testing.assert_allclose(np.trace(a[3:6,3:6]),np.trace(b[3:6,3:6]),atol=1e-12)


def test_rabi_units_and_relaxation_limits():
    c=replace(OpticalConfig(),pump_s=0,pure_dephasing_s=0,ground_pair_s=0,rabi_Hz=1e6)
    s=seven_state(c);r=np.zeros((7,7),complex);r[0,0]=1
    result=transient(s,np.linspace(0,1e-6,21),r)
    assert result[10,0,0].real < .001  # half a Rabi cycle transfers g0
    assert result[20,0,0].real > .999
    # Laser off: a prepared singlet decays with TOTAL return q0+2*qpm.
    s=seven_state(replace(c,rabi_Hz=0));r=np.zeros((7,7),complex);r[6,6]=1
    times=np.linspace(0,2e-6,11);result=transient(s,times,r)
    np.testing.assert_allclose(result[:,6,6].real,np.exp(-1.9e6*times),atol=1e-10)


def test_bloch_rate_matches_resolved_weak_drive():
    for pump in [1e6,4e6]:
        s=seven_state(replace(OpticalConfig(),pump_s=pump,rabi_Hz=20e3))
        np.testing.assert_allclose(np.diag(steady_state(s)),np.diag(rate_steady(s)),atol=2e-7)


def test_radiative_and_isc_competing_lifetime():
    c=replace(OpticalConfig(),pump_s=0,rabi_Hz=0,ground_pair_s=0)
    s=seven_state(c);r=OpticalRates();times=np.linspace(0,50e-9,21)
    for state,isc in [(3,r.isc_pm_s),(4,r.isc_zero_s)]:
        rho=np.zeros((7,7),complex);rho[state,state]=1
        out=transient(s,times,rho)
        np.testing.assert_allclose(out[:,state,state].real,np.exp(-(r.radiative_s+isc)*times),atol=2e-12)


def test_driven_rate_reference_across_field_boundaries():
    for field in (5,20,50):
        for pump in (1e6,4e6):
            s=seven_state(replace(OpticalConfig(),Bz_G=field,pump_s=pump,rabi_Hz=20e3))
            np.testing.assert_allclose(np.diag(steady_state(s)),np.diag(rate_steady(s)),atol=3e-6)
