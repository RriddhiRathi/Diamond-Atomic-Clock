"""Routing, state retention and explicit-computation regression tests."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from diamondclock.dashboard import MODES, SECTIONS


APP = str(Path(__file__).resolve().parents[1] / 'app.py')


def test_landing_and_routes_do_not_calculate(monkeypatch):
    from diamondclock import simulation, clock_dashboard, odmr_dashboard, optical_dashboard

    def unexpected(*args, **kwargs):
        raise AssertionError('Navigation started a scientific calculation')

    for module, name in ((simulation, 'simulate'), (simulation, 'ensemble'),
                         (clock_dashboard, 'calculate_clock'), (odmr_dashboard, 'calculate'),
                         (optical_dashboard, 'calculate_optical')):
        monkeypatch.setattr(module, name, unexpected)
    for cached in (clock_dashboard.cached_clock, odmr_dashboard.cached_odmr,
                   optical_dashboard.cached_optical):
        cached.clear()
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception
    assert app.sidebar.radio(key='dashboard_mode').value == MODES[0]
    assert app.sidebar.radio(key='dashboard_section').options == list(SECTIONS)
    assert not app.button and not app.metric
    assert any('No completed clock run' in v.value for v in app.info)
    for section in SECTIONS:
        app.sidebar.radio(key='dashboard_section').set_value(section).run()
        assert not app.exception
        assert not app.button
    app.sidebar.radio(key='dashboard_section').set_value('Clock Performance').run()
    app.sidebar.radio(key='dashboard_mode').set_value('Research Mode').run()
    assert not app.exception
    assert app.button(key='run_clock')
    assert 'clock_result' not in app.session_state


def test_clock_run_survives_modes_and_routes_without_recalculation(monkeypatch):
    from diamondclock import clock_dashboard

    clock_dashboard.cached_clock.clear()
    original = clock_dashboard.calculate_clock
    calls = []

    def calculate(config):
        calls.append(config)
        return original(config)

    monkeypatch.setattr(clock_dashboard, 'calculate_clock', calculate)
    app = AppTest.from_file(APP, default_timeout=120).run()
    app.sidebar.radio(key='dashboard_mode').set_value('Research Mode').run()
    app.sidebar.radio(key='dashboard_section').set_value('Clock Performance').run()
    app.selectbox(key='clock_cycles').set_value(32)
    app.number_input(key='clock_gain').set_value(2.)
    app.button(key='run_clock').click().run()
    assert not app.exception
    result_hash = app.session_state['clock_result'][1]['summary_sha256']
    app.button(key='prepare_clock_export').click().run()
    assert not app.exception
    exported = app.session_state['clock_export'][2]
    assert exported.startswith(b'PK')
    app.sidebar.radio(key='dashboard_section').set_value('Clock Overview').run()
    assert not app.exception
    assert len(app.metric) == 3
    assert app.metric[0].label == 'Observed lock fraction'
    app.sidebar.radio(key='dashboard_mode').set_value('Demonstration Mode').run()
    app.sidebar.radio(key='dashboard_section').set_value('NV-Center Demonstration').run()
    app.sidebar.radio(key='dashboard_section').set_value('Clock Performance').run()
    assert not app.exception
    assert len(app.metric) == 3
    assert not app.button
    app.sidebar.radio(key='dashboard_mode').set_value('Research Mode').run()
    assert not app.exception
    assert app.selectbox(key='clock_cycles').value == 32
    assert app.number_input(key='clock_gain').value == 2.
    assert app.session_state['clock_result'][1]['summary_sha256'] == result_hash
    assert app.session_state['clock_export'][2] == exported
    # The same clock tool is reachable from Advanced Research without another run.
    app.session_state['research_workspace'] = 'Frequency lock'
    app.sidebar.radio(key='dashboard_section').set_value('Advanced Research').run()
    assert not app.exception
    assert app.selectbox(key='clock_cycles').value == 32
    assert len(calls) == 1


def test_overview_rejects_a_stale_source_result():
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.session_state['clock_result'] = (({}, 'old-source'), {'context': {}})
    app.run()
    assert not app.exception
    assert not app.metric
    assert any('Source changed' in item.value for item in app.warning)
