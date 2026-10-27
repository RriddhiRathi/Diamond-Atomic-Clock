from dataclasses import replace
import numpy as np
from scipy.linalg import expm
from diamondclock.clock_parameters import ClockExperiment,ControllerConfig
from diamondclock.clock_simulation import run_clock
from diamondclock.clock_plant import OpticalClockPlant
from diamondclock.optical_cycle import liouvillian
from diamondclock.optical_parameters import OpticalConfig,OpticalRates
from diamondclock.oscillator import OscillatorConfig,free_frequency,phase_and_time


def test_restricted_lindblad_matches_full_and_counts():
    plant=OpticalClockPlant(OpticalConfig(),OpticalRates(),2926.33e6)
    start=plant.system.initial()
    full=liouvillian(plant.system).toarray();d=7
    for dt in (2e-8,2e-7,2e-6):
        expected=expm(full*dt)@start.ravel(order='F')
        plant.step(plant.nominal_Hz,dt)
        np.testing.assert_allclose(plant.density(),expected.reshape((d,d),order='F'),atol=2e-10)
        start=plant.density()


def test_phase_frequency_identity_and_drift():
    c=OscillatorConfig(offset_Hz=100,drift_Hz_s=2,white_fm_Hz_at_1s=0,random_walk_Hz_sqrt_s=0,phase_noise_rad=0)
    f=free_frequency(c,.01,10,12);phase,x=phase_and_time(f,.01,1e6)
    t=np.arange(len(x))*.01
    np.testing.assert_allclose(x,(100*t+t*t)/1e6,atol=1e-15)
    np.testing.assert_allclose(np.diff(phase)/(2*np.pi*.01),f,atol=1e-9)


def test_seven_state_photon_loop_smoke_and_reproducibility():
    c=ClockExperiment(cycles=12,acquisition_points=41,maximum_time_s=5,gate_s=.005)
    a,diag=run_clock(c);b,other=run_clock(c)
    assert diag==other
    assert a['clock_output'].to_csv(index=False)==b['clock_output'].to_csv(index=False)
    assert a['acquisition'].valid.iloc[0]
    assert len(a['feedback'])==12
    assert len(a['photon_observations'])>41
    assert set(a['allan'].method)=={'locked','unlocked'}
    assert a['clock_output'].evaluation_error_to_hamiltonian_Hz.abs().iloc[-100:].mean()<150e3
