from dataclasses import replace
import numpy as np
import pytest
from diamondclock.clock_parameters import ClockExperiment
from diamondclock.optical_parameters import OpticalConfig
from diamondclock.clock_validation import optical_model_comparison,estimator_monte_carlo
from diamondclock.clock_simulation import run_clock


def test_21_state_sequential_optical_reduction_and_closed_loop():
    c=ClockExperiment(optical=OpticalConfig(states=21),cycles=16,acquisition_points=61,
                      maximum_time_s=5,plant_backend='rate')
    table=optical_model_comparison(c)
    assert table.mean_difference_in_count_sigma.abs().max()<.1
    tables,diag=run_clock(c)
    assert tables['acquisition'].valid.iloc[0]
    assert tables['acquisition'].fractions.iloc[0].__len__()==3
    assert diag['record_s']>1
    assert tables['clock_output'].evaluation_error_to_hamiltonian_Hz.tail(100).abs().mean()<150e3


def test_matched_count_statistics_and_uncertainty_coverage():
    for states in (7,21):
        df=estimator_monte_carlo(states,trials=48,seed=431+states)
        valid=df[df.valid]
        assert len(valid)>=40
        standard_error=valid.error_Hz.std(ddof=1)/np.sqrt(len(valid))
        assert abs(valid.error_Hz.mean())<4*standard_error
        assert valid.covered.mean()>=.85
        tracking=df[df.tracking_valid]
        assert len(tracking)>=40 and tracking.tracking_covered.mean()>=.85
