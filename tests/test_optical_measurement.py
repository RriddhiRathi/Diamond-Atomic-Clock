from dataclasses import replace
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import pytest
from diamondclock.optical_parameters import OpticalExperiment, OpticalConfig, Detector, OpticalRates, parameter_records
from diamondclock.optical_measurement import cw_scan
from diamondclock.optical_reporting import calculate_optical, export_optical
from diamondclock.run_provenance import verify_files


def test_counts_contrast_timing_seed_and_nuclear_populations():
    c=OpticalExperiment(optical=OpticalConfig(states=21),points=9)
    data,contrast=cw_scan(c);again,other=cw_scan(c)
    assert data.to_csv(index=False)==again.to_csv(index=False)
    on=data[data.microwave=='on'].reset_index(drop=True);off=data[data.microwave=='off'].reset_index(drop=True)
    np.testing.assert_allclose(contrast.expected_detected_contrast,1-on.expected_counts/off.expected_counts)
    assert contrast.expected_detected_contrast.max()>.005
    pop=data[[x for x in data if x.startswith('population_')]]
    assert pop.shape[1]==21
    np.testing.assert_allclose(pop.sum(axis=1),1,atol=1e-9)
    np.testing.assert_allclose(data.acquisition_start_s,np.arange(18)*c.dwell_s)
    dark,_=cw_scan(replace(c,detector=replace(c.detector,efficiency=0)))
    np.testing.assert_allclose(dark.expected_counts,(1000+100)*c.dwell_s)


def test_power_broadening_without_assumed_width_or_contrast():
    widths=[]
    for rabi in (50e3,500e3):
        c=OpticalExperiment(optical=replace(OpticalConfig(),rabi_Hz=rabi,pump_s=1e6),points=161,span_Hz=2e6)
        _,a=cw_scan(c);depth=a.expected_intrinsic_contrast.to_numpy()
        above=np.flatnonzero(depth>=depth.max()/2)
        widths.append(a.microwave_frequency_Hz.iloc[above[-1]]-a.microwave_frequency_Hz.iloc[above[0]])
    assert widths[1]>1.5*widths[0]


def test_bundle_integrity_binding_references_and_tampering(tmp_path):
    c=OpticalExperiment(points=5);result=calculate_optical(c)
    files=export_optical(result,c);verify_files(files)
    for member in ('fluorescence_measurements_SIMULATION.csv','state_map_SIMULATION.csv',
                   'reference_photon_trials_SIMULATION.csv','optical_spectrum_SIMULATION.svg',
                   'optical_spectrum_SIMULATION.pdf','source_snapshot/diamondclock/optical_cycle.py',
                   'legacy/matlab/intern_odmr_as_supplied.m.txt','references.bib'):
        assert member in files
    assert {r['id'] for r in json.loads(files['sources.json'])}>={'TET2012','ROB2011','HIN2018','PAN2024'}
    with pytest.raises(ValueError):export_optical(result,replace(c,seed=3))
    result['tables']['contrast'].iloc[0,1]=.9
    with pytest.raises(ValueError,match='changed after'):export_optical(result,c)


def test_classification_preserves_fitted_value_uncertainty_and_override():
    rows=parameter_records(OpticalExperiment())
    r=next(x for x in rows if x['parameter']=='radiative_s')
    assert r['classification']=='published_fitted_value' and r['published_standard_deviation']==4.5e6
    rows=parameter_records(OpticalExperiment(rates=replace(OpticalRates(),radiative_s=60e6)))
    assert rows[0]['classification']=='simulation_assumption_override'
    assert rows[0]['published_value']==63.7e6


@pytest.mark.parametrize('kwargs',[{'points':2},{'seed':-2},{'span_Hz':float('nan')},
    {'dwell_s':1e-6},{'backend':'unknown'},{'detector':Detector(efficiency=.9)}])
def test_experiment_guard(kwargs):
    with pytest.raises(ValueError):replace(OpticalExperiment(),**kwargs).validate()


def test_cli_and_overwrite_refusal(tmp_path):
    root=Path(__file__).resolve().parents[1];out=tmp_path/'run'
    command=[sys.executable,str(root/'scripts/run_optical.py'),'--points','5','--out',str(out)]
    first=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=90)
    assert first.returncode==0,first.stderr
    before=(out/'metadata.json').read_bytes()
    second=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=30)
    assert second.returncode!=0 and 'already exists' in second.stderr
    assert (out/'metadata.json').read_bytes()==before


def test_summary_stale_source_and_persistent_paper_binding(tmp_path,monkeypatch):
    from diamondclock.reference_store import ReferenceStore
    import diamondclock.run_provenance as provenance
    c=OpticalExperiment(points=5);result=calculate_optical(c)
    store=ReferenceStore(tmp_path/'papers.sqlite')
    paper=store.add(dict(title='User supplied optical reference',authors='Example',year=2026,
                         journal='User note',url='https://example.org/optical',doi=''))
    files=export_optical(result,c,references=store.catalog())
    rows=json.loads(files['sources.json'])
    assert any(r['id']==paper['id'] and r['verification_status']=='unverified' for r in rows)
    result['summary']['experimental_validation']=True
    with pytest.raises(ValueError,match='summary changed'):export_optical(result,c)
    result['summary']['experimental_validation']=False
    original=provenance.source_files
    monkeypatch.setattr(provenance,'source_files',lambda *args,**kwargs:{**original(*args,**kwargs),'changed.py':b'changed'})
    with pytest.raises(ValueError,match='Source files changed'):export_optical(result,c)
