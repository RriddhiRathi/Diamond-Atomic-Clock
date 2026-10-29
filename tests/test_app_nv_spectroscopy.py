"""One engine evaluation across marker, overlay and navigation changes."""
from pathlib import Path
import numpy as np
from streamlit.testing.v1 import AppTest
from diamondclock import nv_spectroscopy as demo


def test_marker_and_view_changes_reuse_spectrum_and_preserve_state(monkeypatch):
    demo.cached_spectrum.clear()
    original = demo.spectrum
    calls = []
    def counted(config, physics):
        calls.append(config)
        return original(config, physics)
    monkeypatch.setattr(demo, 'spectrum', counted)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=90).run()
    app.sidebar.radio(key='dashboard_section').set_value('NV-Center Demonstration').run()
    assert not app.exception
    assert len(calls)==1
    slider = app.slider(key='nv_mw_frequency')
    selected = slider.min
    slider.set_value(selected).run()
    app.checkbox(key='nv_context').set_value(True).run()
    app.checkbox(key='nv_overlays').set_value(False).run()
    app.checkbox(key='nv_microwave').set_value(False).run()
    assert not app.exception
    assert len(calls)==1
    assert app.metric[0].value=='1.000000'
    app.checkbox(key='nv_laser').set_value(False).run()
    assert app.metric[0].value=='Not modeled · laser off'
    app.sidebar.radio(key='dashboard_section').set_value('Clock Overview').run()
    app.sidebar.radio(key='dashboard_section').set_value('NV-Center Demonstration').run()
    assert not app.exception
    assert app.slider(key='nv_mw_frequency').value==selected
    assert not app.checkbox(key='nv_overlays').value
    assert len(calls)==1
    app.slider(key='nv_field').set_value(30.).run()
    assert not app.exception
    assert len(calls)==2
    from diamondclock.nv_visualization import magnetic_field
    assert np.allclose(app.session_state['nv_spectrum_config']['B_lab_G'],magnetic_field(30))
    app.slider(key='nv_field').set_value(0.).run()
    assert not app.exception
    assert len(calls)==3
    assert 'clock_result' not in app.session_state
    assert 'optical_result' not in app.session_state
