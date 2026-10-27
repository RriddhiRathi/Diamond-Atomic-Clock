from dataclasses import replace
import json,subprocess,sys
from pathlib import Path
import pytest
from diamondclock.clock_parameters import ClockExperiment
from diamondclock.clock_reporting import calculate_clock,export_clock
from diamondclock.run_provenance import verify_files
from diamondclock.reference_store import ReferenceStore


def test_clock_bundle_binds_config_tables_sources_and_user_references(tmp_path,monkeypatch):
    c=ClockExperiment(cycles=8,maximum_time_s=4)
    result=calculate_clock(c)
    store=ReferenceStore(tmp_path/'papers.sqlite3')
    paper=store.add(dict(title='Independent reference',authors='Example',year=2026,journal='User note',url='https://example.org/clock'))
    files=export_clock(result,c,references=store.catalog());verify_files(files)
    for name in ('clock_output_SIMULATION.csv','clock_phase_boundaries_SIMULATION.csv','photon_observations_SIMULATION.csv',
                 'feedback_SIMULATION.csv','evaluation_measurement_truth_SIMULATION.csv','clock_stability_SIMULATION.pdf','clock_acquisition_SIMULATION.pdf',
                 'clock_phase_time_SIMULATION.svg','source_snapshot/diamondclock/frequency_estimation.py','legacy/matlab/intern_odmr_as_supplied.m.txt'):
        assert name in files
    metadata=json.loads(files['metadata.json'])
    assert 'expected_counts' not in metadata['estimator_allowed_inputs']
    assert paper['id'] in files['sources.json'].decode()
    with pytest.raises(ValueError,match='configuration'):export_clock(result,replace(c,seed=0))
    result['tables']['clock_output'].iloc[0,1]+=1
    with pytest.raises(ValueError,match='tables changed'):export_clock(result,c)
    result['tables']['clock_output'].iloc[0,1]-=1
    result['summary']['experimental_validation']=True
    with pytest.raises(ValueError,match='summary changed'):export_clock(result,c)
    result['summary']['experimental_validation']=False
    import diamondclock.run_provenance as rp
    original=rp.source_files
    monkeypatch.setattr(rp,'source_files',lambda *args,**kwargs:{**original(*args,**kwargs),'changed.py':b'changed'})
    with pytest.raises(ValueError,match='Source files changed'):export_clock(result,c)


def test_clock_cli_overwrite_and_provenance(tmp_path):
    root=Path(__file__).resolve().parents[1];out=tmp_path/'clock'
    command=[sys.executable,str(root/'scripts/run_clock.py'),'--cycles','4','--out',str(out)]
    a=subprocess.run(command,cwd=tmp_path,capture_output=True,text=True,timeout=120)
    assert a.returncode==0,a.stderr
    before=(out/'metadata.json').read_bytes()
    b=subprocess.run(command,cwd=tmp_path,capture_output=True,text=True,timeout=30)
    assert b.returncode!=0 and 'already exists' in b.stderr
    assert (out/'metadata.json').read_bytes()==before
