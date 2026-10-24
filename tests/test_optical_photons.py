from dataclasses import replace
import numpy as np
import pytest
from diamondclock.optical_parameters import OpticalConfig
from diamondclock.optical_dynamics import build_system
from diamondclock.optical_cycle import steady_state
from diamondclock.photon_detection import count_distribution, poisson_counts, sample_reference


def test_counting_mean_losses_variance_and_seed():
    system=build_system(replace(OpticalConfig(),rabi_Hz=0));rho=steady_state(system)
    rate=np.trace(system.emission_operator()@rho).real
    for efficiency in (.01,1.):
        gate=2e-6 if efficiency==.01 else .2e-6
        p=count_distribution(system,rho,gate,efficiency)
        n=np.arange(len(p));mean=n@p;variance=((n-mean)**2)@p
        np.testing.assert_allclose(mean,efficiency*gate*rate,rtol=1e-9)
        if efficiency==.01:assert abs(variance/mean-1)<.02
        else:assert abs(variance/mean-1)>.01  # single-emitter counts are not exactly Poisson
        a=sample_reference(p,20000,31);b=sample_reference(p,20000,31)
        np.testing.assert_array_equal(a,b)
        assert abs(a.mean()-mean)<6*np.sqrt(variance/len(a))
        fourth=((n-mean)**4)@p
        assert abs(a.var()-variance)<6*np.sqrt((fourth-variance**2)/len(a))


def test_coherent_count_distribution_and_probability_cutoff():
    system=build_system(OpticalConfig());rho=steady_state(system)
    p=count_distribution(system,rho,.2e-6,.01)
    n=np.arange(len(p));expected=np.trace(system.emission_operator()@rho).real*.01*.2e-6
    np.testing.assert_allclose(n@p,expected,rtol=2e-9)
    assert p.sum()==pytest.approx(1)
    zero=count_distribution(system,rho,.1e-6,0)
    np.testing.assert_allclose(zero[0],1,atol=1e-12)


def test_short_time_antibunching_and_dark_counts():
    # Prepare an excited g0-related bare level: at most one emission at first order in dt.
    system=build_system(replace(OpticalConfig(),pump_s=0,rabi_Hz=0,ground_pair_s=0))
    rho=np.zeros((7,7),complex);rho[4,4]=1
    p=count_distribution(system,rho,1e-9,1)
    assert p[2:].sum()<1e-12
    assert p[1]==pytest.approx(63.7e6/(63.7e6+9.3e6)*(1-np.exp(-73e6*1e-9)),rel=1e-10)
    samples=sample_reference([1.],30000,919,background_mean=3.)
    assert abs(samples.mean()-3)<.04
    assert abs(samples.var()-3)<.1


def test_poisson_mean_variance_and_input_rejection():
    a=poisson_counts(np.full(30000,15.),44)
    assert abs(a.mean()-15)<.15 and abs(a.var()-15)<.5
    with pytest.raises(ValueError):poisson_counts([-1],4)
    s=build_system();rho=steady_state(s)
    for gate,eff in [(0,.1),(1e-3,.1),(1e-6,2),(1e-6,float('nan'))]:
        with pytest.raises(ValueError):count_distribution(s,rho,gate,eff)
