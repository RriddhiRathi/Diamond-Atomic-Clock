from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_integrated_odmr_interaction_clock_comparison_and_export():
    app=str(Path(__file__).resolve().parents[1]/'app.py')
    at=AppTest.from_file(app,default_timeout=90).run()
    assert not at.exception
    assert any(tab.label=='ODMR spectroscopy' for tab in at.tabs)
    # Existing clock controls and metrics are present; new functionality is in the same app.
    assert len(at.metric)==4
    at.sidebar.selectbox[0].set_value(4096)
    at.sidebar.button[0].click().run()
    at.checkbox(key='odmr_compare').set_value(True)
    at.button(key='run_odmr').click().run()
    assert not at.exception
    result=at.session_state['odmr_result'][1]
    assert 'comparison' in result
    assert len(result['spectrum'])==5001
    assert set(result['transitions'].orientation)=={1,2,3,4}
    at.button(key='prepare_odmr_export').click().run()
    assert not at.exception
    files=at.session_state['odmr_export'][2]
    assert 'odmr_stability_comparison_SIMULATION.pdf' in files
    at.number_input(key='odmr_B').set_value(30.)
    at.button(key='run_odmr').click().run()
    assert not at.exception
    assert 'odmr_export' not in at.session_state
    assert at.session_state['odmr_result'][0][0]['B_lab_G']!=result['context']['config']['B_lab_G']


def test_odmr_invalid_overlapping_clock_lines_shows_error():
    at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=90).run()
    at.checkbox(key='odmr_compare').set_value(True)
    at.number_input(key='odmr_width').set_value(2.)
    at.button(key='run_odmr').click().run()
    assert not at.exception
    assert any('isolated' in error.value for error in at.error)
    assert 'odmr_result' not in at.session_state
