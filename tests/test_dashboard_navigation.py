"""Unified routing, state retention and explicit-computation regression tests."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
from diamondclock.dashboard import SECTIONS, WORKSPACES

APP=str(Path(__file__).resolve().parents[1]/'app.py')


def test_landing_and_routes_do_not_calculate(monkeypatch):
    from diamondclock import simulation, legacy_dashboard, clock_dashboard, odmr_dashboard, optical_dashboard
    def unexpected(*args,**kwargs):raise AssertionError('Navigation started a scientific calculation')
    for module,name in ((simulation,'simulate'),(simulation,'ensemble'),(legacy_dashboard,'simulate'),
                        (legacy_dashboard,'ensemble'),(clock_dashboard,'calculate_clock'),
                        (odmr_dashboard,'calculate'),(optical_dashboard,'calculate_optical')):
        monkeypatch.setattr(module,name,unexpected)
    for cached in (legacy_dashboard.cached_run,legacy_dashboard.cached_ensemble,clock_dashboard.cached_clock,
                   odmr_dashboard.cached_odmr,optical_dashboard.cached_optical):cached.clear()
    app=AppTest.from_file(APP,default_timeout=60).run()
    assert not app.exception
    assert [item.key for item in app.sidebar.radio]==['dashboard_section']
    assert app.sidebar.radio(key='dashboard_section').options==list(SECTIONS)
    assert 'dashboard_mode' not in app.session_state
    assert {button.key for button in app.button}=={'nav_nv','nav_performance','nav_research','nav_clock_run','nav_clock_archive'}
    assert not app.metric
    assert any('No completed clock run' in item.value for item in app.markdown)
    for section in SECTIONS:
        app.sidebar.radio(key='dashboard_section').set_value(section).run()
        assert not app.exception
    app.sidebar.radio(key='dashboard_section').set_value('Research Tools').run()
    for workspace in WORKSPACES:
        app.selectbox(key='research_workspace').set_value(workspace).run()
        assert not app.exception
        for result in ('legacy_result','clock_result','odmr_result','optical_result'):
            assert result not in app.session_state
    app.sidebar.radio(key='dashboard_section').set_value('Clock Performance').run()
    assert app.button(key='run_clock')


def test_clock_run_survives_modes_and_routes_without_recalculation(monkeypatch):
    # The old two-mode transition is replaced by six directly accessible pages.
    from diamondclock import clock_dashboard
    clock_dashboard.cached_clock.clear()
    original=clock_dashboard.calculate_clock
    calls=[]
    def calculate(config):
        calls.append(config)
        return original(config)
    monkeypatch.setattr(clock_dashboard,'calculate_clock',calculate)
    app=AppTest.from_file(APP,default_timeout=120).run()
    app.sidebar.radio(key='dashboard_section').set_value('Clock Performance').run()
    app.selectbox(key='clock_cycles').set_value(32)
    app.number_input(key='clock_gain').set_value(2.)
    app.button(key='run_clock').click().run()
    assert not app.exception
    result_hash=app.session_state['clock_result'][1]['summary_sha256']
    app.button(key='prepare_clock_export').click().run()
    assert not app.exception
    exported=app.session_state['clock_export'][2]
    assert exported.startswith(b'PK')
    for page in ('Overview','NV-Center & ODMR','Paper Bucket','Exports & Documentation','Clock Performance'):
        app.sidebar.radio(key='dashboard_section').set_value(page).run()
        assert not app.exception
        if page=='Overview':
            assert len(app.metric)==6 and app.metric[0].label=='Observed lock fraction'
        if page=='Exports & Documentation':
            assert any(item.proto.label=='Download Photon clock research bundle' for item in app.get('download_button'))
        assert app.session_state['clock_result'][1]['summary_sha256']==result_hash
        assert app.session_state['clock_export'][2]==exported
    assert len(app.get('plotly_chart'))==5
    assert app.selectbox(key='clock_cycles').value==32
    assert app.number_input(key='clock_gain').value==2.
    app.number_input(key='clock_gain').set_value(4.).run()
    assert not app.exception
    assert app.session_state['clock_result'][1]['summary_sha256']==result_hash
    assert app.session_state['clock_export'][2]==exported
    app.number_input(key='clock_gain').set_value(2.).run()
    app.session_state['research_workspace']='Frequency lock'
    app.sidebar.radio(key='dashboard_section').set_value('Research Tools').run()
    assert not app.exception and app.selectbox(key='clock_cycles').value==32
    assert len(calls)==1


def test_overview_rejects_a_stale_source_result():
    app=AppTest.from_file(APP,default_timeout=60).run()
    app.session_state['clock_result']=(({},'old-source'),{'context':{}})
    app.run()
    assert not app.exception and not app.metric
    assert any('Source changed' in item.value for item in app.warning)
