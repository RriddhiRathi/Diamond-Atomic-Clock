"""Navigation/archived-result tests must never launch a scientific clock run."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

from diamondclock import clock_dashboard

APP=str(Path(__file__).resolve().parents[1]/'app.py')


def test_empty_overview_navigation_and_historical_results_do_not_run_clock(monkeypatch):
    def unexpected(*args,**kwargs):
        raise AssertionError('Presentation started a clock simulation')
    monkeypatch.setattr(clock_dashboard,'calculate_clock',unexpected)
    clock_dashboard.cached_clock.clear()
    app=AppTest.from_file(APP,default_timeout=60).run()
    assert not app.exception and not app.metric
    app.button(key='nav_clock_archive').click().run()
    assert not app.exception
    assert app.sidebar.radio(key='dashboard_section').value=='Clock Performance'
    assert len(app.metric)==6
    assert len(app.get('plotly_chart'))==5
    assert 'clock_result' not in app.session_state
    app.selectbox(key='clock_archive_case').set_value('Lock with worse stability · quieter oscillator').run()
    assert not app.exception
    assert any('worsens stability' in item.value for item in app.markdown)
    app.radio(key='clock_analysis_window').set_value('Predeclared fixed window').run()
    assert not app.exception
    assert any('predeclared fixed window' in item.value.lower() for item in app.markdown)
    assert not app.exception and app.button(key='run_clock')
    assert 'clock_result' not in app.session_state
    app.sidebar.radio(key='dashboard_section').set_value('Overview').run()
    app.button(key='nav_research').click().run()
    assert app.sidebar.radio(key='dashboard_section').value=='Research Tools'
    # Select original workspace without calculating a clock on navigation.
    app.selectbox(key='research_workspace').set_value('Frequency lock').run()
    assert not app.exception and app.button(key='run_clock')


def test_incompatible_and_modified_session_results_are_retained_but_not_presented():
    app=AppTest.from_file(APP,default_timeout=60).run()
    from diamondclock.run_provenance import source_fingerprint
    app.session_state['clock_result']=(({},source_fingerprint()),{})
    app.run()
    assert not app.exception and not app.metric
    assert any('Incompatible' in item.value for item in app.warning)
    assert 'clock_result' in app.session_state


def test_archives_missing_from_installed_wheel_are_explicit(monkeypatch,tmp_path):
    from diamondclock import clock_presentation
    monkeypatch.setattr(clock_presentation,'project_root',lambda:tmp_path)
    app=AppTest.from_file(APP,default_timeout=60).run()
    app.button(key='nav_clock_archive').click().run()
    assert not app.exception and not app.metric
    assert any('not installed wheels' in item.value for item in app.info)


def test_failed_submission_preserves_last_successful_run_and_uses_saved_config(monkeypatch):
    from dataclasses import asdict
    from diamondclock.clock_parameters import ClockExperiment
    from diamondclock.clock_reporting import calculate_clock
    from diamondclock.run_provenance import source_fingerprint
    config=ClockExperiment(cycles=4,maximum_time_s=4)
    result=calculate_clock(config)
    saved=((asdict(config),source_fingerprint()),result)
    def rejected(*args,**kwargs):
        raise ValueError('Test rejected new configuration')
    monkeypatch.setattr(clock_dashboard,'calculate_clock',rejected)
    clock_dashboard.cached_clock.clear()
    app=AppTest.from_file(APP,default_timeout=60).run()
    app.session_state['clock_result']=saved
    app.sidebar.radio(key='dashboard_section').set_value('Clock Performance').run()
    assert not app.exception and len(app.metric)==6
    assert any('completed-run configuration' in item.value for item in app.warning)
    app.button(key='run_clock').click().run()
    assert not app.exception
    assert any('Test rejected' in item.value for item in app.error)
    assert app.session_state['clock_result'][1]['summary_sha256']==result['summary_sha256']
    assert app.session_state['clock_result'][0][0]==asdict(config)
    assert len(app.metric)==6
