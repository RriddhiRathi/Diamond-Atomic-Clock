from streamlit.testing.v1 import AppTest
from pathlib import Path


def test_existing_dashboard_optical_measurement_and_resubmission():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=90).run()
    assert not app.exception
    assert any(t.label=='Optical measurement' for t in app.tabs)
    app.selectbox(key='optical_points').set_value(41)
    app.button(key='run_optical').click().run()
    assert not app.exception
    assert 'optical_result' in app.session_state
    assert any('Maximum expected contrast' in m.label for m in app.metric)
    previous=app.session_state['optical_result'][0]
    app.number_input(key='optical_pump').set_value(3.)
    app.button(key='run_optical').click().run()
    assert not app.exception
    assert app.session_state['optical_result'][0]!=previous
    assert app.session_state['optical_result'][0][0]['optical']['pump_s']==3e6
