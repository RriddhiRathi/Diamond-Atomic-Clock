import ast
from pathlib import Path
import numpy as np
import pytest
from diamondclock.count_observations import CountObservation
from diamondclock.frequency_estimation import fit_acquisition,estimate_detuning,dip_profile


def observations(centre,seed=4,gate=.02,points=61):
    rng=np.random.default_rng(seed);x=np.linspace(-4e6,4e6,points)
    rate=1.28e6*(1-.125/(1+4*((x-centre)/700e3)**2))
    return [CountObservation(float(f),gate,int(n)) for f,n in zip(x,rng.poisson(rate*gate))]


def test_acquisition_blind_frequency_and_profile_interval():
    for centre in (-170e3,240e3):
        cal=fit_acquisition(observations(centre))
        assert cal.valid,cal.reason
        assert abs(cal.centre_command_Hz-centre)<4*cal.centre_sigma_Hz
        assert cal.lower_Hz<cal.centre_command_Hz<cal.upper_Hz
        assert cal.width_Hz==pytest.approx(700e3,rel=.2)


def test_estimator_interface_and_no_truth_imports():
    with pytest.raises(TypeError):CountObservation(0.,.01,3,true_frequency_Hz=1.)
    for name in ('frequency_estimation.py','clock_controller.py'):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'diamondclock'/name).read_text())
        imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        assert not any(v and any(x in v for x in ('clock_plant','clock_simulation','oscillator','physics')) for v in imports)
    a=observations(80e3)
    # No simulator object or provenance/seed field is accepted by this API.
    assert fit_acquisition(a)==fit_acquisition(tuple(a))


def test_tracking_sign_zero_count_and_uncertainty():
    cal=fit_acquisition(observations(-50e3,22,gate=.05))
    rng=np.random.default_rng(88)
    for e in (-100e3,100e3):
        obs=[]
        for probe,on in [(0,False),(250e3,True),(-250e3,True),(-250e3,True),(250e3,True),(0,False)]:
            dip=dip_profile(np.array([(probe+e)/1e6]),np.log(cal.width_Hz/1e6),cal.fractions,np.array(cal.offsets_Hz)/1e6)[0] if on else 0
            obs.append(CountObservation(probe,.02,int(rng.poisson(.02*cal.baseline_per_nominal_s*(1-dip))),on))
        result=estimate_detuning(obs,cal)
        assert result.valid and np.sign(result.detuning_Hz)==np.sign(e)
        assert abs(result.detuning_Hz-e)<4*result.sigma_Hz
    empty=[CountObservation(0,.01,0,False),CountObservation(250e3,.01,0,True)]
    assert not estimate_detuning(empty,cal).valid


def test_no_signal_does_not_produce_certified_acquisition():
    assert not fit_acquisition([CountObservation(float(f),.01,0) for f in np.linspace(-4e6,4e6,41)]).valid
