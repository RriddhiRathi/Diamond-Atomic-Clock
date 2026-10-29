"""Presentation checks on actual archived outputs and one small existing-engine run."""
from copy import deepcopy
from dataclasses import asdict
import json

import numpy as np
import pandas as pd
import pytest

from diamondclock.clock_results import (matched_allan, valid_allan, interpret, ratio_outcome,
                                        overview_metrics, validate_saved)
from diamondclock.clock_presentation import (read_archive, acquisition_figure, frequency_figure,
                                             phase_figure, tracking_figure, allan_figure)
from diamondclock.resources import project_root
from diamondclock.run_provenance import source_fingerprint, verify_files


@pytest.fixture(scope='module')
def archive():
    def load(case='7'):
        path=project_root()/'outputs/clock_phase4_20261024'/case/'complete_research_bundle.zip'
        return read_archive(path.read_bytes())
    return load


@pytest.fixture(scope='module')
def saved():
    from diamondclock.clock_parameters import ClockExperiment
    from diamondclock.clock_reporting import calculate_clock
    config=ClockExperiment(cycles=4,maximum_time_s=4)
    return ((asdict(config),source_fingerprint()),calculate_clock(config))


def test_overview_uses_exact_completed_run_values_and_longest_matched_tau(archive):
    values,result,_,_=archive()
    m=overview_metrics(values,result)
    summary=result['summary']
    assert m['nominal_Hz']==summary['nominal_Hz']
    assert m['lock_fraction']==summary['observed_lock_fraction']
    assert m['record_s']==summary['record_s']
    assert m['final_time_errors_s']==summary['final_time_errors_s']
    paired=matched_allan(result['tables']['allan'])
    assert m['comparison']==paired.iloc[-1].to_dict()
    assert m['comparison']['ratio']==m['comparison']['feedback_adev']/m['comparison']['free_adev']


@pytest.mark.parametrize('case,ever,final,stability',[
    ('7',True,True,'depends on averaging time'),
    ('21',True,True,'depends on averaging time'),
    ('low_drift',True,True,'worsens stability'),
    ('high_gain',False,False,'worsens stability'),
    ('latency',False,False,'worsens stability'),
    ('photon_starved',False,False,'equal Allan deviation')])
def test_real_demonstration_conclusions_do_not_equate_lock_with_stability(archive,case,ever,final,stability):
    _,result,_,_=archive(case)
    conclusion=interpret(result)
    assert conclusion['ever_locked'] is ever
    assert conclusion['final_locked'] is final
    assert stability in conclusion['stability']
    assert 'absolute accuracy' in conclusion['text']


def test_lost_lock_unknown_and_timeout_are_distinguished(archive):
    _,original,_,_=archive()
    result=deepcopy(original)
    result['tables']['feedback'].loc[result['tables']['feedback'].index[-1],'locked']=False
    result['summary']['timed_out']=True
    assert 'lost by final cycle' in interpret(result)['text']
    assert 'time limit' in interpret(result)['text']
    result['tables']['feedback']=pd.DataFrame()
    assert interpret(result)['lock']=='Lock status unavailable'


def test_matched_allan_rejects_invalid_unmatched_and_duplicate_points():
    table=pd.DataFrame([
        ('unlocked',1,2.),('locked',1,1.),
        ('unlocked',2,3.),('locked',3,1.), # never interpolate unmatched tau
        ('unlocked',4,np.nan),('locked',4,1.),
        ('unlocked',5,0.),('locked',5,1.),
        ('unlocked',-1,2.),('locked',-1,1.),
        ('unlocked',np.inf,2.),('locked',np.inf,1.),
        ('unlocked',6,2.),('locked',6,1.),('locked',6,3.), # ambiguous duplicate
        ('unlocked',7,2.),('locked',7,np.inf),
    ],columns=['method','tau_s','adev'])
    paired=matched_allan(table)
    assert paired.tau_s.tolist()==[1.]
    assert paired.ratio.tolist()==[.5]
    assert not valid_allan(table).duplicated(['method','tau_s']).any()
    table['overlapping_pairs']=0
    assert matched_allan(table).empty
    assert matched_allan(pd.DataFrame()).empty
    assert matched_allan(None).empty


@pytest.mark.parametrize('ratio,outcome',[(.5,'improved'),(2.,'worsened'),(1.,'equal within numerical tolerance'),
                                        (1.+5e-15,'equal within numerical tolerance'),(np.nan,'unavailable'),
                                        (np.inf,'unavailable'),(0.,'unavailable')])
def test_ratio_interpretation(ratio,outcome):
    assert ratio_outcome(ratio)==outcome


def test_window_isolation_and_insufficient_evidence(archive):
    _,original,_,_=archive()
    result=deepcopy(original)
    result['tables']['allan']=pd.DataFrame(columns=['tau_s','adev','method'])
    assert interpret(result)['paired'].empty
    assert 'insufficient' in interpret(result)['text'].lower()
    fixed=interpret(result,'allan_fixed_window')
    assert not fixed['paired'].empty
    assert 'predeclared fixed window' in fixed['text']
    assert 'not selected by lock quality' in fixed['text']


def test_plots_preserve_engine_coordinates_units_gaps_and_phase_endpoint(archive):
    _,result,_,_=archive('7')
    t=result['tables']
    acq=acquisition_figure(result)
    on=t['photon_observations'].query("stage == 'acquisition' and cycle == 0 and microwave_on")
    np.testing.assert_array_equal(acq.data[0].x,on.probe_offset_Hz/1e6)
    np.testing.assert_array_equal(acq.data[0].y,on.detected_counts)
    assert acq.layout.shapes[0].x0==t['acquisition'].iloc[0].centre_command_Hz/1e6
    assert 'offset' in acq.layout.xaxis.title.text and 'counts' in acq.layout.yaxis.title.text
    fig=frequency_figure(result)
    np.testing.assert_array_equal(fig.data[0].y,t['clock_output'].unlocked_deviation_Hz/1e3)
    np.testing.assert_array_equal(fig.data[1].y,t['clock_output'].locked_deviation_Hz/1e3)
    assert 'True simulation time (s)'==fig.layout.xaxis.title.text
    assert 'minus public nominal (kHz)' in fig.layout.yaxis.title.text
    phase=phase_figure(result)
    assert phase.data[1].x[-1]==result['summary']['record_s']
    assert phase.data[1].y[-1]==pytest.approx(1e6*result['summary']['final_time_errors_s']['unlocked'])
    assert phase.data[3].y[-1]==pytest.approx(1e6*result['summary']['final_time_errors_s']['locked'])
    assert 'rad' in phase.layout.yaxis.title.text and 'µs' in phase.layout.yaxis2.title.text
    track=tracking_figure(result)
    assert track.data[0].connectgaps is False
    np.testing.assert_array_equal(track.data[1].y,t['feedback'].locked.astype(int))
    rejected=deepcopy(result)
    rejected['tables']['feedback'].loc[0,'valid']=False
    assert np.isnan(tracking_figure(rejected).data[0].y[0])
    for key in ('allan','allan_fixed_window'):
        stability=allan_figure(result,key)
        assert stability.layout.xaxis.type==stability.layout.yaxis.type=='log'
        assert 'dimensionless' in stability.layout.yaxis.title.text
        assert ('full record' if key=='allan' else 'fixed window') in stability.data[0].name
        np.testing.assert_array_equal(stability.data[0].y,valid_allan(t[key]).query("method == 'unlocked'").adev)


def test_saved_validation_checks_source_schema_configuration_and_content(saved):
    config,result=validate_saved(saved)
    assert asdict(config)==saved[0][0] and result is saved[1]
    with pytest.raises(ValueError,match='Source changed'):
        validate_saved(((saved[0][0],'old'),saved[1]))
    with pytest.raises(ValueError,match='Incompatible'):
        validate_saved(((saved[0][0],saved[0][1]),{}))
    changed=deepcopy(saved)
    changed[0][0]['seed']+=1
    with pytest.raises(ValueError,match='configuration'):
        validate_saved(changed)
    changed=deepcopy(saved)
    changed[1]['tables']['allan'].iloc[0,1]+=1
    with pytest.raises(ValueError,match='tables changed'):
        validate_saved(changed)
    changed=deepcopy(saved)
    changed[1]['summary']['observed_lock_fraction']=1.
    with pytest.raises(ValueError,match='summary changed'):
        validate_saved(changed)


def test_original_archive_bytes_exports_and_provenance_preserved(archive):
    values,result,metadata,files=archive()
    verify_files(files)
    assert values==metadata['provenance']['config']
    assert metadata['provenance']['source_sha256']
    assert metadata['data_kind']=='SIMULATION'
    for stem in ('clock_acquisition','clock_frequency_feedback','clock_phase_time','clock_stability'):
        assert files[stem+'_SIMULATION.pdf'].startswith(b'%PDF')
        assert b'<svg' in files[stem+'_SIMULATION.svg']
    assert 'legacy/matlab/intern_odmr_as_supplied.m.txt' in files
    assert 'photon_observations_SIMULATION.csv' in files
    assert json.loads(files['summary.json'])==result['summary']
