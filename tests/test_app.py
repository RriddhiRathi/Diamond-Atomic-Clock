from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_dashboard_default_and_parameter_change():
    app=Path(__file__).resolve().parents[1]/'app.py'
    at=AppTest.from_file(str(app),default_timeout=60).run()
    assert not at.exception
    assert len(at.metric)==4
    at.sidebar.selectbox[0].set_value(4096)
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert at.metric[0].value=='1.14 h'
    at.select_slider[0].set_value(3)
    at.button(key='run_ensemble').click().run()
    assert not at.exception
    assert 'ensemble_result' in at.session_state
    at.button(key='prepare_export').click().run()
    assert not at.exception
    assert 'export' in at.session_state
