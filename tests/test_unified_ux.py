"""Unified navigation, direct provenance access and screen-only plot changes."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from diamondclock import dashboard
from diamondclock.clock_presentation import read_archive, tracking_figure, allan_figure
from diamondclock.resources import project_root

APP=str(Path(__file__).resolve().parents[1]/'app.py')


@pytest.mark.parametrize('old,new',[('Clock Overview','Overview'),('NV-Center Demonstration','NV-Center & ODMR'),
                                    ('Advanced Research','Research Tools'),('Clock Performance','Clock Performance')])
def test_old_session_routes_migrate_without_changing_inputs_results_or_exports(monkeypatch,old,new):
    result=object();export=object();ensemble=object()
    state={'dashboard_section':old,'dashboard_mode':'Research Mode','clock_result':result,
           'clock_export':export,'ensemble_result':ensemble,'legacy_config':{'n':4096},
           'nv_mw_frequency':2.9,'clock_gain':2.,'odmr_B':30.,'optical_pump':3.}
    expected={k:v for k,v in state.items() if k not in ('dashboard_mode','dashboard_section')}
    monkeypatch.setattr(dashboard.st,'session_state',state)
    dashboard.migrate_navigation()
    dashboard.preserve_workspace_state()
    assert state['dashboard_section']==new and 'dashboard_mode' not in state
    for key,value in expected.items():assert state[key] is value


def test_paper_bucket_direct_access_all_mapping_models_and_original_verification(monkeypatch):
    from diamondclock import legacy_dashboard,clock_dashboard,odmr_dashboard,optical_dashboard
    def forbidden(*args,**kwargs):raise AssertionError('References triggered a scientific calculation')
    for module,name in ((legacy_dashboard,'simulate'),(legacy_dashboard,'ensemble'),
                        (clock_dashboard,'calculate_clock'),(odmr_dashboard,'calculate'),
                        (optical_dashboard,'calculate_optical')):
        monkeypatch.setattr(module,name,forbidden)
    app=AppTest.from_file(APP,default_timeout=60).run()
    app.sidebar.radio(key='dashboard_section').set_value('Paper Bucket').run()
    assert not app.exception
    assert app.title[0].value=='Paper Bucket'
    from diamondclock.research_pages import MAPS
    assert app.selectbox(key='research_equation_map').options==list(MAPS)
    for model in list(MAPS)[:4]:
        app.selectbox(key='research_parameter_model').set_value(model).run()
        assert not app.exception
        data=app.dataframe[0].value
        assert 'source' in data and 'Reference status' in data
        assert data['Reference status'].str.contains('Model assumption').any()
        assert not data['Reference status'].str.contains('Unmapped source ID').any()
    for name in MAPS:
        app.selectbox(key='research_equation_map').set_value(name).run()
        assert not app.exception
    assert any('Repository-curated' in item.value for item in app.markdown)
    assert not any('Verified source' in item.value for item in app.markdown)
    downloads=[item.proto.label for item in app.get('download_button')]
    assert 'Download Paper Bucket JSON' in downloads and 'Download Paper Bucket BibTeX' in downloads
    assert 'Download original MATLAB transcript' in downloads
    assert all(key not in app.session_state for key in ('legacy_result','clock_result','odmr_result','optical_result'))


def test_stability_open_configure_and_navigation_never_calculates_without_submit(monkeypatch):
    from diamondclock import legacy_dashboard
    legacy_dashboard.cached_run.clear()
    original=legacy_dashboard.simulate
    calls=[]
    def counted(config):
        calls.append(config)
        return original(config)
    monkeypatch.setattr(legacy_dashboard,'simulate',counted)
    app=AppTest.from_file(APP,default_timeout=120).run()
    app.button(key='nav_research').click().run()
    assert not app.exception and not calls
    assert app.button(key='run_legacy') and 'legacy_result' not in app.session_state
    app.selectbox(key='legacy_number_of_samples').set_value(4096)
    app.button(key='run_legacy').click().run()
    assert not app.exception and len(calls)==1
    result=app.session_state['legacy_result']
    for page in ('Paper Bucket','Exports & Documentation','Overview','Research Tools'):
        app.sidebar.radio(key='dashboard_section').set_value(page).run()
        assert not app.exception and len(calls)==1
        assert app.session_state['legacy_result'][0]==result[0]
        np.testing.assert_array_equal(app.session_state['legacy_result'][1][0].time_s,result[1][0].time_s)


def test_uncertainty_toggle_and_plot_style_preserve_all_values_and_invalid_gaps():
    path=project_root()/'outputs/clock_phase4_20261024/7/complete_research_bundle.zip'
    _,result,_,_=read_archive(path.read_bytes())
    result=deepcopy(result)
    result['tables']['feedback'].loc[0,'valid']=False
    plain=tracking_figure(result)
    detailed=tracking_figure(result,show_uncertainty=True)
    assert plain.data[0].error_y.visible is False and detailed.data[0].error_y.visible is True
    assert np.isnan(plain.data[0].y[0]) and np.isnan(detailed.data[0].y[0])
    for one,two in zip(plain.data,detailed.data):
        np.testing.assert_array_equal(one.x,two.x)
        np.testing.assert_array_equal(one.y,two.y)
    np.testing.assert_array_equal(plain.data[0].customdata,plain.data[0].error_y.array)
    allan=allan_figure(result)
    assert allan.layout.xaxis.type==allan.layout.yaxis.type=='log'
    assert allan.layout.yaxis.tickformat=='.1e'
    assert allan.layout.legend.orientation=='h' and allan.layout.margin.b>=90
    assert allan.data[0].line.dash!=allan.data[1].line.dash
    assert allan.data[0].marker.symbol!=allan.data[1].marker.symbol
    assert allan.layout.font.size>=12
    assert 400<=allan.layout.height<=500


def test_odmr_zoom_changes_viewport_only_and_keeps_selected_marker():
    from diamondclock.nv_spectroscopy import cached_spectrum,spectrum_figure,spectrum_view
    from diamondclock.nv_visualization import magnetic_field
    from diamondclock.run_provenance import source_fingerprint
    data,lines,config,_=cached_spectrum(tuple(magnetic_field(20)),0,source_fingerprint())
    frequency=float(data.loc[data.combined_fluorescence.idxmin(),'frequency_Hz'])
    fig=spectrum_figure(data,lines,config,0,frequency)
    arrays=[(deepcopy(trace.x),deepcopy(trace.y)) for trace in fig.data]
    spectrum_view(fig,config,frequency,True)
    lo,hi=fig.layout.xaxis.range
    assert lo<=frequency/1e9<=hi
    assert hi-lo==pytest.approx(10*config['linewidth_Hz']/1e9)
    for trace,(x,y) in zip(fig.data,arrays):
        np.testing.assert_array_equal(trace.x,x)
        np.testing.assert_array_equal(trace.y,y)
    selected=next(trace for trace in fig.data if trace.name=='Selected proxy')
    assert selected.x[0]==frequency/1e9


def test_exports_hub_retains_but_rejects_stale_prepared_bundle_without_simulation(monkeypatch):
    from diamondclock import clock_dashboard
    def forbidden(*args,**kwargs):raise AssertionError('Export navigation recalculated a clock')
    monkeypatch.setattr(clock_dashboard,'calculate_clock',forbidden)
    app=AppTest.from_file(APP,default_timeout=60).run()
    key=({},'old-source')
    app.session_state['clock_result']=(key,{})
    app.session_state['clock_export']=(key,'old-catalog',b'preserved-original-export')
    app.sidebar.radio(key='dashboard_section').set_value('Exports & Documentation').run()
    assert not app.exception
    assert app.session_state['clock_export'][2]==b'preserved-original-export'
    assert any('Source, configuration or reference catalog changed' in item.value for item in app.warning)
    assert not any(item.proto.label=='Download Photon clock research bundle' for item in app.get('download_button'))
