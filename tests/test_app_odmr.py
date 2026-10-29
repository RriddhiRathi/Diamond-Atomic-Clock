def test_integrated_odmr_interaction_clock_comparison_and_export(research_app):
    at=research_app('ODMR spectroscopy')
    assert not at.exception
    assert any(t.value=='ODMR spectroscopy' for t in at.subheader)
    # Configure the preserved baseline before the optional paired ODMR comparison.
    at.selectbox(key='research_workspace').set_value('Stability & compensation').run()
    at.selectbox(key='legacy_number_of_samples').set_value(4096)
    at.button(key='run_legacy').click().run()
    at.selectbox(key='research_workspace').set_value('ODMR spectroscopy').run()
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
    at.selectbox(key='research_workspace').set_value('Optical measurement').run()
    at.selectbox(key='research_workspace').set_value('ODMR spectroscopy').run()
    assert not at.exception
    assert at.checkbox(key='odmr_compare').value is True
    assert at.session_state['odmr_export'][2] == files
    at.number_input(key='odmr_B').set_value(30.)
    at.button(key='run_odmr').click().run()
    assert not at.exception
    assert 'odmr_export' not in at.session_state
    assert at.session_state['odmr_result'][0][0]['B_lab_G']!=result['context']['config']['B_lab_G']


def test_odmr_invalid_overlapping_clock_lines_shows_error(research_app):
    at=research_app('ODMR spectroscopy')
    at.checkbox(key='odmr_compare').set_value(True)
    at.number_input(key='odmr_width').set_value(2.)
    at.button(key='run_odmr').click().run()
    assert not at.exception
    assert any('isolated' in error.value for error in at.error)
    assert 'odmr_result' not in at.session_state
