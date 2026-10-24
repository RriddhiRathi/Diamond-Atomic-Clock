from dataclasses import asdict, replace
import numpy as np
import pandas as pd
import pytest
from diamondclock.odmr_bridge import ReadoutScenario,readout_eta,resolved_clock_readout,compare_stability
from diamondclock.simulation import Config,simulate
from diamondclock.physics import calibration
from diamondclock.stability import overlapping_adev


def test_readout_formula_scaling_and_half_time_penalty():
    s=ReadoutScenario();eta=readout_eta(s)
    assert eta==pytest.approx(10886.621079036348)
    assert readout_eta(replace(s,linewidth_Hz=2*s.linewidth_Hz))==pytest.approx(2*eta)
    assert readout_eta(replace(s,photon_rate_per_s=4*s.photon_rate_per_s))==pytest.approx(eta/2)
    assert readout_eta(replace(s,duty_fraction=.25))==pytest.approx(2*eta)
    one_line=4/(3*np.sqrt(3))*s.linewidth_Hz/(s.line_contrast*np.sqrt(s.photon_rate_per_s))
    assert eta==pytest.approx(one_line*np.sqrt(2))


def test_comparison_preserves_original_engine_and_all_other_inputs():
    c=Config(n=1024);result=compare_stability(c)
    trace,a,d=simulate(c)
    pd.testing.assert_frame_equal(trace,result['original_trace'])
    pd.testing.assert_frame_equal(a,result['allan'].query("scenario == 'Original assumed readout'").drop(columns='scenario').reset_index(drop=True))
    actual=asdict(result['informed_config']);original=asdict(c)
    assert [k for k in actual if actual[k]!=original[k]]==['electron_readout_Hz']
    for name in ('temperature_K','Bz_G','Bx_G','lo_total_y','f_plus_Hz','f1_Hz','y_nuclear_average'):
        np.testing.assert_array_equal(trace[name],result['informed_trace'][name])
    assert len(result['bridge_diagnostics']['isolation_checks'])==2
    # Same readout setting gives identical results: bridge does not smuggle in other changes.
    equal=replace(c,electron_readout_Hz=readout_eta())
    same=compare_stability(equal)
    pd.testing.assert_frame_equal(same['original_trace'],same['informed_trace'])


def test_photon_readout_white_fm_allan_limit():
    eta=readout_eta();c=Config(n=32768,temp_rms_K=0,temp_sine_K=0,temp_drift_K_h=0,
        Bz_rms_G=0,Bx_rms_G=0,nuclear_readout_Hz=0,lo_white_adev_1s=0,lo_rw_diffusion=0)
    informed,_=resolved_clock_readout(c)
    trace,_,_=simulate(informed)
    nu=calibration()['nominal_Hz'][0]
    av=overlapping_adev(trace.y_single_electron.to_numpy(),c.dt_s,factors=[1,4,16])
    np.testing.assert_allclose(av.adev,eta/(nu*np.sqrt(av.tau_s)),rtol=.08)


def test_unsupported_correlations_overlap_and_invalid_readout_rejected():
    with pytest.raises(ValueError,match='correlation'):resolved_clock_readout(replace(Config(),readout_rho=.5))
    with pytest.raises(ValueError,match='isolated'):resolved_clock_readout(s=ReadoutScenario(linewidth_Hz=1e6))
    for s in (ReadoutScenario(photon_rate_per_s=0),ReadoutScenario(duty_fraction=0),ReadoutScenario(line_contrast=.5)):
        with pytest.raises(ValueError):readout_eta(s)
