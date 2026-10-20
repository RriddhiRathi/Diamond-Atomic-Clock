from dataclasses import replace
import numpy as np
import pytest
from diamondclock.simulation import Config,simulate,ou


def quiet_config(**kw):
    c=Config(n=4096,temp_rms_K=0,temp_sine_K=0,temp_drift_K_h=0,Bz_rms_G=0,Bx_rms_G=0,
             electron_readout_Hz=0,nuclear_readout_Hz=0,thermometer_rms_K=0,
             lo_white_adev_1s=0,lo_rw_diffusion=0,slope_error_pct=0)
    return replace(c,**kw)


def test_seed_reproducibility_and_zero_noise():
    c=Config(n=1024)
    t,a,d=simulate(c)
    t2,a2,d2=simulate(c)
    np.testing.assert_array_equal(t.values,t2.values)
    np.testing.assert_array_equal(a.adev,a2.adev)
    _,q,_=simulate(quiet_config())
    assert q.adev.max()==0


def test_temperature_compensation_in_noise_free_model():
    t,_,_=simulate(quiet_config(temp_sine_K=.01,temp_period_s=1000))
    assert t.y_composite.std()<t.y_electron_average.std()*1e-3


def test_common_lo_is_preserved():
    t,_,_=simulate(quiet_config(lo_white_adev_1s=1e-8))
    for col in t.columns:
        if col.startswith('y_'):np.testing.assert_array_equal(t[col],t.lo_total_y)


def test_stationary_ou_statistics():
    x=ou(200000,1.,.1,10.,np.random.default_rng(9))
    assert abs(x.std()-.1)<.004
    assert abs(np.corrcoef(x[:-1],x[1:])[0,1]-np.exp(-.1))<.01


def test_readout_interval_scaling():
    # Same random stream: readout-only fractional sigma scales as dt^-1/2.
    t,_,_=simulate(quiet_config(electron_readout_Hz=100,dt_s=1))
    t2,_,_=simulate(quiet_config(electron_readout_Hz=100,dt_s=4))
    np.testing.assert_allclose(t.y_electron_average,2*t2.y_electron_average,rtol=1e-14)


def test_invalid_scope_rejected():
    for c in [Config(n=2),Config(dt_s=0),Config(readout_rho=2),Config(Bz_G=1000),Config(temp_drift_K_h=100)]:
        with pytest.raises(ValueError):simulate(c)
