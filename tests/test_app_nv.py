"""The 3D page remains educational and cannot trigger the scientific experiments."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_nv_page_controls_reset_and_navigation_without_simulation(monkeypatch):
    from diamondclock import clock_dashboard, odmr_dashboard, optical_dashboard, simulation

    def forbidden(*args, **kwargs):
        raise AssertionError('3D geometry requested a scientific calculation')

    for module, name in ((clock_dashboard, 'calculate_clock'), (odmr_dashboard, 'calculate'),
                         (optical_dashboard, 'calculate_optical'), (simulation, 'simulate'),
                         (simulation, 'ensemble')):
        monkeypatch.setattr(module, name, forbidden)
    for cached in (clock_dashboard.cached_clock, odmr_dashboard.cached_odmr, optical_dashboard.cached_optical):
        cached.clear()
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=60).run()
    app.sidebar.radio(key='dashboard_section').set_value('NV-Center Demonstration').run()
    assert not app.exception
    assert len(app.get('plotly_chart')) == 1
    assert any('do not run ODMR' in item.value for item in app.info)
    assert not any('reserved for later' in item.value for item in app.info)
    app.selectbox(key='nv_orientation').set_value(1)
    app.slider(key='nv_angle').set_value(60.)
    app.slider(key='nv_azimuth').set_value(45.)
    app.checkbox(key='nv_orientations').set_value(True)
    app.checkbox(key='nv_context').set_value(True).run()
    assert not app.exception
    assert any('Axial B∥ = 10.000 G' in item.value for item in app.markdown)
    app.button(key='reset_nv_camera').click().run()
    assert not app.exception
    assert app.session_state['nv_camera_revision'] == 1
    app.sidebar.radio(key='dashboard_section').set_value('Clock Overview').run()
    app.sidebar.radio(key='dashboard_mode').set_value('Research Mode').run()
    app.sidebar.radio(key='dashboard_section').set_value('NV-Center Demonstration').run()
    assert not app.exception
    assert app.selectbox(key='nv_orientation').value == 1
    assert app.slider(key='nv_angle').value == 60.
    assert app.slider(key='nv_azimuth').value == 45.
    assert app.checkbox(key='nv_orientations').value
    assert app.checkbox(key='nv_context').value
    assert app.session_state['nv_camera_revision'] == 1
    assert 'clock_result' not in app.session_state
    assert 'odmr_result' not in app.session_state
    assert 'optical_result' not in app.session_state
    app.slider(key='nv_field').set_value(0.).run()
    assert not app.exception
    assert any('undefined at zero field' in item.value for item in app.markdown)
    app.checkbox(key='nv_bonds').set_value(False).run()
    assert not app.exception
    assert app.checkbox(key='nv_bond_labels').disabled
