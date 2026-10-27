from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_existing_app_clock_controls_feedback_and_recalculation():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=120).run()
    assert not app.exception
    assert any(t.label=='Frequency lock' for t in app.tabs)
    app.selectbox(key='clock_cycles').set_value(32)
    app.button(key='run_clock').click().run()
    assert not app.exception
    assert 'clock_result' in app.session_state
    result=app.session_state['clock_result'][1]
    assert len(result['tables']['feedback'])==32
    assert any('Observed lock fraction' in v.label for v in app.metric)
    app.number_input(key='clock_gain').set_value(0.)
    app.button(key='run_clock').click().run()
    assert not app.exception
    assert app.session_state['clock_result'][0][0]['controller']['integral_per_s']==0
