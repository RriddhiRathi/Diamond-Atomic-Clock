import numpy as np
from dataclasses import replace
from diamondclock.clock_controller import PhotonController
from diamondclock.clock_parameters import ControllerConfig
from diamondclock.count_observations import FrequencyEstimate


def estimate(error=0.,sigma=1.,valid=True):return FrequencyEstimate(error,sigma,0.,0.,0.,0.,valid,'test',1.)


def test_controller_sign_integral_gain_and_antiwindup():
    c=PhotonController(ControllerConfig(integral_per_s=1,proportional=0,correction_limit_Hz=1000))
    assert c.update(estimate(100),.1)==-10
    for _ in range(100):c.update(estimate(1e6),1.)
    assert abs(c.integrator)<=1000
    assert c.update(estimate(-100),.1)>-1000


def test_deterministic_zero_delay_integrator_stability_and_failure():
    for gain,should_shrink in [(.3,True),(2.5,False)]:
        ctl=PhotonController(ControllerConfig(integral_per_s=gain))
        u=0.;errors=[]
        for _ in range(8):
            error=100+u;errors.append(abs(error));u=ctl.update(estimate(error),1.)
        assert (errors[-1]<errors[0])==should_shrink


def test_lock_uses_uncertainty_validity_and_consecutive_observations():
    c=PhotonController(ControllerConfig(consecutive_good=3,consecutive_bad=2))
    c.update(estimate(),.1);c.update(estimate(),.1);assert not c.locked
    c.update(estimate(),.1);assert c.locked
    assert c.update(estimate(valid=False),.1) is None
    assert c.locked
    c.update(estimate(valid=False),.1);assert not c.locked
    for _ in range(8):c.update(estimate(sigma=1e6),.1)
    assert not c.locked
