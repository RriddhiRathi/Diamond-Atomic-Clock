from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import numpy as np
import pytest
from diamondclock.odmr import ODMRConfig,odmr_parameter_provenance
from diamondclock.odmr_reporting import calculate,export_odmr
from diamondclock.odmr_bridge import ReadoutScenario
from diamondclock.physics import Physics
from diamondclock.simulation import Config
from diamondclock.reference_store import ReferenceStore,curated_sources,verification_label
from diamondclock.reporting import zip_files
from diamondclock.run_provenance import verify_files


def test_odmr_bundle_provenance_references_vectors_and_comparison():
    c=ODMRConfig(points=1001)
    result=calculate(c,Config(n=1024),ReadoutScenario())
    store=ReferenceStore()
    added=store.add(dict(title='Unverified ODMR fixture',authors='A',year=2026,
                        journal='Fixture',url='https://example.org/odmr'))
    files=export_odmr(result,c,references=store.catalog())
    verify_files(files)
    meta=json.loads(files['metadata.json'])
    assert meta['data_kind']=='SIMULATION'
    assert meta['provenance']['capture_stage']=='before_calculation'
    assert meta['provenance']['physics']==Physics().__dict__
    assert meta['reference_catalog_sha256']==hashlib.sha256(files['sources.json']).hexdigest()
    assert added['id'] in files['sources.json'].decode()
    assert added['id'] in files['references.bib'].decode()
    for name,digest in meta['source_sha256'].items():
        assert hashlib.sha256(files['source_snapshot/'+name]).hexdigest()==digest
    assert 'source_snapshot/legacy/matlab/intern_odmr_as_supplied.m.txt' in files
    inputs=json.loads(files['comparison_inputs.json'])
    changed=[k for k in inputs['original_config'] if inputs['original_config'][k]!=inputs['informed_config'][k]]
    assert changed==['electron_readout_Hz']
    for name in ('odmr_spectrum','odmr_levels','odmr_sensitivity','odmr_stability_comparison'):
        assert files[name+'_SIMULATION.pdf'].startswith(b'%PDF')
        assert b'<svg' in files[name+'_SIMULATION.svg']
        assert b'SIMULATION' in files[name+'_SIMULATION.svg']
    with zipfile.ZipFile(io.BytesIO(zip_files(files))) as z:
        assert set(z.namelist())==set(files)
    with pytest.raises(ValueError,match='do not match'):
        export_odmr(result,replace(c,contrast=.02))
    result['context']['files']['app.py']=b'changed'
    with pytest.raises(ValueError,match='snapshot'):
        export_odmr(result,c)


def test_every_odmr_constant_and_input_has_traceable_evidence():
    rows=odmr_parameter_provenance()
    sources={r['id']:r for r in curated_sources()}
    assert set(rows.source)<=set(sources)
    assert rows.locator.str.len().min()>0
    for implementation in rows.implementation:
        assert Path(implementation.split(':')[0]).exists()
    assert 'not peer-reviewed' in verification_label(sources['MATLAB_INTERN'])
    assert 'not independently verified' in verification_label(sources['V1990'])
    assert sources['MATLAB_INTERN']['verified'] is None
    assert sources['D2012']['doi']=='10.1103/PhysRevB.85.205203'


def test_cli_odmr_reproduction_and_overwrite_protection(tmp_path):
    root=Path(__file__).resolve().parents[1]
    out=tmp_path/'odmr-run'
    command=[sys.executable,str(root/'scripts/run_odmr.py'),'--out',str(out),'--compare','--samples','1024']
    run=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=90)
    assert run.returncode==0,run.stderr
    files={p.relative_to(out).as_posix():p.read_bytes() for p in out.rglob('*') if p.is_file()}
    verify_files(files)
    again=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=90)
    assert again.returncode!=0 and 'already exists' in again.stderr
    assert (out/'metadata.json').read_bytes()==files['metadata.json']
