"""Context page: exact archived NV arrays, qualified literature points, no solver."""
from copy import deepcopy
from pathlib import Path
import json

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from diamondclock import clock_comparison as comparison
from diamondclock.clock_results import matched_allan, valid_allan
from diamondclock.reference_store import curated_sources, catalog_bytes, bibtex_bytes, verification_label
from diamondclock.resources import project_root

APP=str(Path(__file__).resolve().parents[1]/'app.py')


@pytest.fixture(scope='module')
def data():return comparison.comparison_data()


@pytest.fixture(scope='module')
def nv(data):return comparison.saved_nv(data)


def test_reference_points_match_reviewed_values_qualifiers_and_paper_bucket(data):
    rows=data['literature_points']
    assert [(r['clock_type'],r['tau_s'],r['value'],r['relation']) for r in rows]==[
        ('Cesium beam',1.,5e-12,'approximately'),('Rubidium cell',1.,1e-11,'approximately'),
        ('Hydrogen maser',1.,1e-12,'less_than')]
    catalog={row['id']:row for row in curated_sources()}
    mapping=(project_root()/'references/clock_comparison_map.md').read_text(encoding='utf-8')
    for row in rows:
        assert row['source_id'] in catalog
        assert row['clock_type'].split()[0] in mapping
        assert row['url'].startswith('https://www.nist.gov/')
        assert 'printed p.' in row['locator'] and np.isfinite(row['value']) and row['value']>0
    source=catalog['NIST_ATOZ']
    assert source['verified']==data['reviewed_on']
    assert 'representative' in source['evidence'] and 'per-device' in source['note']
    assert 'Repository-curated' in verification_label(source)
    assert 'NIST_ATOZ' in catalog_bytes(list(catalog.values())).decode()
    assert '@misc{NIST_ATOZ' in bibtex_bytes(list(catalog.values())).decode()
    assert data['nv_example']['source_id'] in catalog


def test_nv_table_uses_the_actual_saved_example_and_matched_tau(data,nv):
    config,result=nv
    assert config['optical']['states']==7 and config['plant_backend']=='lindblad'
    assert config['optical']['Bz_G']==20 and config['seed']==410024
    point=matched_allan(result['tables']['allan']).iloc[-1]
    assert point.tau_s==3.16 and point.ratio<1
    table=comparison.table_rows(data,nv)
    assert len(table)==4
    row=table.iloc[0]
    assert 'SIMULATION' in row['Clock type'] and 'full record' in row['Metric / evidence']
    assert row['Averaging time τ (s)']==f'{point.tau_s:g}'
    assert f'{point.feedback_adev:.6g}' in row['Fractional instability (1)']
    assert f'{point.free_adev:.6g}' in row['Fractional instability (1)']
    assert 'improved at this τ' in row['Configuration / context']
    assert 'depends on averaging time' in row['Configuration / context']
    assert table.iloc[3]['Fractional instability (1)'].startswith('<')
    assert all('LITERATURE' in row for row in table['Clock type'].iloc[1:])


def test_graph_preserves_saved_points_and_has_no_fabricated_literature_curve(data,nv):
    fig=comparison.comparison_figure(data,nv)
    assert len(fig.data)==5
    actual=valid_allan(nv[1]['tables']['allan'])
    for trace,method in zip(fig.data[:2],('locked','unlocked')):
        rows=actual[actual.method==method]
        np.testing.assert_array_equal(trace.x,rows.tau_s)
        np.testing.assert_array_equal(trace.y,rows.adev)
        assert 'SIMULATION' in trace.name
    for trace,row in zip(fig.data[2:],data['literature_points']):
        assert trace.mode=='markers'
        assert list(trace.x)==[row['tau_s']] and list(trace.y)==[row['value']]
        assert row['source_id'] in str(trace.customdata) and row['locator'] in str(trace.customdata)
    assert fig.data[-1].marker.symbol=='triangle-down-open'
    assert '<' in fig.data[-1].hovertemplate
    assert fig.layout.xaxis.type==fig.layout.yaxis.type=='log'
    assert 'dimensionless' in fig.layout.yaxis.title.text
    assert fig.layout.legend.orientation=='h' and fig.layout.margin.b>=100


def test_page_navigation_rendering_state_and_paper_bucket_link_without_calculation(monkeypatch):
    from diamondclock import clock_dashboard,legacy_dashboard,odmr_dashboard,optical_dashboard
    def forbidden(*args,**kwargs):raise AssertionError('Comparison started a scientific simulation')
    for module,name in ((clock_dashboard,'calculate_clock'),(legacy_dashboard,'simulate'),
                        (legacy_dashboard,'ensemble'),(odmr_dashboard,'calculate'),(optical_dashboard,'calculate_optical')):
        monkeypatch.setattr(module,name,forbidden)
    app=AppTest.from_file(APP,default_timeout=60).run()
    result=(({},'old-source'),{'retained':'unchanged'})
    export=(result[0],'retained-catalog',b'original-prepared-export')
    app.session_state['clock_result']=result
    app.session_state['clock_export']=export
    app.session_state['nv_mw_frequency']=2.91
    app.session_state['clock_gain']=2.
    assert 'Atomic Clock Comparison' in app.sidebar.radio(key='dashboard_section').options
    app.sidebar.radio(key='dashboard_section').set_value('Atomic Clock Comparison').run()
    assert not app.exception
    assert len(app.dataframe)==1 and len(app.get('plotly_chart'))==1 and len(app.dataframe[0].value)==4
    assert app.session_state['clock_result']==result and app.session_state['clock_export']==export
    assert app.session_state['nv_mw_frequency']==2.91 and app.session_state['clock_gain']==2.
    assert not any(key in app.session_state for key in ('legacy_result','odmr_result','optical_result'))
    assert any('not a direct experimental validation' in item.value for item in app.caption)
    assert any('drift 10000 Hz/s' in item.value for item in app.caption)
    app.button(key='comparison_sources').click().run()
    assert not app.exception and app.sidebar.radio(key='dashboard_section').value=='Paper Bucket'
    assert app.selectbox(key='research_equation_map').value=='Atomic clock comparison'
    assert any('NIST_ATOZ' in item.value for item in app.markdown)
    assert app.session_state['clock_export']==export


def test_missing_nv_archive_is_explicit_without_invented_nv_values(monkeypatch,data):
    def missing(*args,**kwargs):raise FileNotFoundError('Original bundle not installed')
    monkeypatch.setattr(comparison,'saved_nv',missing)
    app=AppTest.from_file(APP,default_timeout=60).run()
    app.sidebar.radio(key='dashboard_section').set_value('Atomic Clock Comparison').run()
    assert not app.exception and len(app.dataframe)==len(app.get('plotly_chart'))==1
    assert any('NV archive unavailable' in item.value for item in app.warning)
    assert app.dataframe[0].value.iloc[0]['Fractional instability (1)']=='Unavailable'
    assert len(comparison.comparison_figure(data,None).data)==3
    assert 'clock_result' not in app.session_state


def test_changed_archive_is_rejected_and_original_reference_data_are_not_modified(data):
    changed=deepcopy(data)
    changed['nv_example']['bundle_sha256']='0'*64
    with pytest.raises(ValueError,match='differs from the reviewed'):
        comparison.saved_nv(changed)
    assert comparison.comparison_data()==data
