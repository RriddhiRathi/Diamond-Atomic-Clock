from dataclasses import replace
import numpy as np
import pytest
from diamondclock.clock_parameters import ClockExperiment,ControllerConfig
from diamondclock.clock_simulation import run_clock,_ExperimentClock
from diamondclock.clock_validation import physical_estimator_cases,counting_cases
from diamondclock.clock_plant import OpticalClockPlant
from diamondclock.optical_parameters import OpticalConfig,OpticalRates,Detector
from diamondclock.oscillator import OscillatorConfig,free_frequency,phase_and_time
from diamondclock.stability import overlapping_adev


def test_no_feedback_is_exact_free_running_output():
    c=ClockExperiment(cycles=8,maximum_time_s=4,controller=ControllerConfig(proportional=0,integral_per_s=0))
    tables,_=run_clock(c);out=tables['clock_output']
    np.testing.assert_allclose(out.locked_deviation_Hz,out.unlocked_deviation_Hz,atol=2e-6,rtol=0)
    np.testing.assert_allclose(out.mean_correction_Hz,0,atol=0)


def test_local_clock_gate_time_and_causal_latency():
    c=ClockExperiment(cycles=4,oscillator=OscillatorConfig(offset_Hz=200e3,drift_Hz_s=0,white_fm_Hz_at_1s=0,random_walk_Hz_sqrt_s=0,phase_noise_rad=0))
    f0=2926.346e6;plant=OpticalClockPlant(c.optical,c.rates,f0)
    engine=_ExperimentClock(c,plant,f0,np.full(2000,200e3),71)
    obs=engine.measure(0,False,'test',0)
    truth=engine.truth[0]
    assert truth['actual_duration_s']==pytest.approx(c.gate_s/(1+200e3/f0),abs=1e-12)
    assert obs.nominal_gate_s==c.gate_s and not hasattr(obs,'actual_duration_s')
    engine.request(-100e3,0);deadline=engine.local+c.controller.latency_s
    engine.advance(c.controller.latency_s/2,0,False);assert engine.u==0
    engine.advance(c.controller.latency_s,0,False)
    assert engine.u==-100e3 and engine.events[0]['applied_local_s']>=deadline-1e-12
    assert all(e['applied_local_s']>=e['deadline_local_s']-1e-12 for e in engine.events)


def test_actual_clock_phase_drives_allan_and_keeps_offset():
    tables,_=run_clock(ClockExperiment(cycles=12,maximum_time_s=4))
    out=tables['clock_output'];f0=2926.346e6;dt=.002
    for label in ('locked','unlocked'):
        y=out[label+'_deviation_Hz'].to_numpy()/f0
        expected=overlapping_adev(y,dt)
        actual=tables['allan'][tables['allan'].method==label]
        np.testing.assert_allclose(actual.adev,expected.adev,atol=0,rtol=0)
        phase=out[label+'_phase_error_rad'].to_numpy()
        np.testing.assert_allclose(np.diff(phase)/(2*np.pi*dt*f0),y[:-1],atol=1e-14)
    # Constant frequency error is visible in time error even though its ADEV is zero.
    phase,x=phase_and_time(np.full(200,100.),.1,1e6)
    assert x[-1]==pytest.approx(.002)
    assert overlapping_adev(np.full(200,1e-4),.1).adev.max()==0


def test_white_fm_and_phase_noise_normalization():
    c=OscillatorConfig(offset_Hz=0,drift_Hz_s=0,white_fm_Hz_at_1s=10,random_walk_Hz_sqrt_s=0,phase_noise_rad=0)
    f=free_frequency(c,.01,1000,88)
    a=overlapping_adev(f,.01,[1,10,100])
    np.testing.assert_allclose(a.adev,10/np.sqrt(a.tau_s),rtol=.05)
    pm=free_frequency(replace(c,white_fm_Hz_at_1s=0,phase_noise_rad=.1),.01,100,44)
    phase,_=phase_and_time(pm,.01,1e6)
    # Node phase is white; differencing it must not be treated as independent FM.
    assert np.corrcoef(pm[:-1],pm[1:])[0,1]<-.45
    assert .08<np.std(phase)<.12


def test_lindblad_count_variance_and_gate_correlations_are_quantified():
    df=counting_cases(ClockExperiment(gate_s=.001))
    assert np.all(df.variance>0)
    assert np.max(abs(df.fano-1))<.05
    assert np.max(abs(df.covariance))>1e-12
    assert np.max(abs(df.covariance)/np.sqrt(df.first_mean*df.second_mean))<.02


def test_physical_optical_model_frequency_bias_is_measured_not_corrected():
    df=physical_estimator_cases(7,trials=12,seed=39)
    assert df.valid.sum()>=10
    good=df[df.valid]
    assert abs(good.error_Hz.mean())<4*good.error_Hz.std()/np.sqrt(len(good))


def test_physical_validation_uses_the_requested_sample_and_field():
    c=ClockExperiment(optical=OpticalConfig(Bz_G=5),reference_offset_Hz=120e3)
    df=physical_estimator_cases(7,trials=2,seed=39,experiment=c)
    np.testing.assert_allclose(df.evaluation_hamiltonian_command_Hz,120e3,atol=1)
    assert df.valid.all()


def test_bad_gains_latency_and_photon_counts_can_fail():
    baseline=ClockExperiment(cycles=96,maximum_time_s=15)
    normal,diag=run_clock(baseline)
    cases=[replace(baseline,controller=replace(baseline.controller,integral_per_s=70,max_reacquisitions=0)),
           replace(baseline,controller=replace(baseline.controller,integral_per_s=12,latency_s=.3,max_reacquisitions=0)),
           replace(baseline,detector=Detector(centers=1),controller=replace(baseline.controller,max_reacquisitions=0))]
    assert diag['observed_lock_fraction']>.6
    for c in cases:
        tables,d=run_clock(c)
        assert d['observed_lock_fraction']<diag['observed_lock_fraction']
        assert len(tables['clock_output'])>=20  # failure does not erase clock-output records


@pytest.mark.parametrize('changes',[{'optical':OpticalConfig(Bz_G=475)},{'optical':OpticalConfig(temperature_K=298)},
    {'native_dt_s':0},{'gate_s':float('nan')},{'seed':-1}])
def test_clock_scope_rejection(changes):
    with pytest.raises(ValueError):replace(ClockExperiment(),**changes).validate()


def test_oracle_evaluation_is_separate_and_count_api_has_no_extra_fields():
    from dataclasses import fields
    from diamondclock.count_observations import CountObservation
    assert {v.name for v in fields(CountObservation)}=={'probe_offset_Hz','nominal_gate_s','detected_counts','microwave_on','local_start_s'}
    tables,diag=run_clock(ClockExperiment(cycles=16,maximum_time_s=4,fixed_analysis_start_s=0))
    assert 'mean_carrier_deviation_Hz' not in tables['photon_observations']
    evaluated=tables['evaluation_tracking_error']
    assert len(evaluated)==16 and evaluated.valid.any()
    assert diag['fixed_window_tracking_evaluation']['accepted']>0
    good=evaluated[evaluated.valid]
    assert np.isfinite(good.estimator_error_Hz).all()


def test_locking_can_worsen_a_quieter_oscillator():
    c=ClockExperiment(cycles=128,maximum_time_s=15,oscillator=replace(OscillatorConfig(),drift_Hz_s=100))
    tables,diag=run_clock(c)
    assert diag['observed_lock_fraction']>.8
    a=tables['allan_fixed_window']
    free=a[a.method=='unlocked'].adev.to_numpy();controlled=a[a.method=='locked'].adev.to_numpy()
    assert controlled[-1]>free[-1]  # not a universal feedback-improvement assertion
