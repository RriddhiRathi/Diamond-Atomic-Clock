def test_dashboard_default_and_parameter_change(research_app):
    at=research_app('Stability & compensation')
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
    at.sidebar.radio(key='dashboard_section').set_value('Clock Overview').run()
    at.sidebar.radio(key='dashboard_section').set_value('Advanced Research').run()
    assert not at.exception
    assert at.sidebar.selectbox[0].value==4096
    assert 'ensemble_result' in at.session_state
    assert 'export' in at.session_state
