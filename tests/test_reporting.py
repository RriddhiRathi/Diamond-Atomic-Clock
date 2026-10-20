import io
import json
import zipfile
from pathlib import Path
from diamondclock.simulation import Config,simulate
from diamondclock.reporting import ROOT,provenance,sources,export_files,zip_files


def test_parameter_traceability_and_vector_exports():
    c=Config(n=1024)
    trace,a,d=simulate(c)
    prov=provenance(c)
    assert prov.implementation.notna().all()
    assert prov.locator.notna().all()
    assert set(prov.source)<=set(s['id'] for s in sources())
    for symbol in prov.implementation:
        assert (ROOT/symbol.split(':')[0]).exists()
    files=export_files(trace,a,c,d)
    assert files['stability_SIMULATION.pdf'].startswith(b'%PDF')
    assert b'<svg' in files['stability_SIMULATION.svg']
    assert json.loads(files['metadata.json'])['data_kind']=='SIMULATION'
    with zipfile.ZipFile(io.BytesIO(zip_files(files))) as z:
        assert 'SHA256SUMS.txt' in z.namelist()
