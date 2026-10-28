"""Part 1 dashboard shell. Navigation never starts a scientific calculation."""
import sqlite3

import streamlit as st

SECTIONS = ('Clock Overview', 'NV-Center Demonstration', 'Clock Performance', 'Advanced Research')
MODES = ('Demonstration Mode', 'Research Mode')
WORKSPACES = ('Stability & compensation', 'ODMR spectroscopy', 'Optical measurement', 'Frequency lock')

STYLE = '''<style>
[data-testid="stMainBlockContainer"] {max-width:1440px;padding-top:2.5rem}
h1 {letter-spacing:-.045em} h2,h3 {letter-spacing:-.025em}
[data-testid="stMetric"] {padding:1rem;border:1px solid #2b394b;border-radius:12px}
[data-testid="stSidebar"] {border-right:1px solid #263448}
[data-testid="stCaptionContainer"] {line-height:1.6}
</style>'''


def preserve_workspace_state():
    """Keep inputs when routes hide widgets; never retain button/submit events."""
    for key in list(st.session_state):
        if key.startswith(('legacy_', 'clock_', 'odmr_', 'optical_', 'research_')):
            st.session_state[key] = st.session_state[key]


def reference_catalog():
    from .reference_store import ReferenceStore
    from .reporting import sources

    try:
        return ReferenceStore().catalog(), None
    except (OSError, sqlite3.Error, ValueError) as exc:
        st.error('Persistent references unavailable: ' + str(exc))
        return sources(), str(exc)


def completed_clock():
    """Read only a source-validated completed run; never calculate one."""
    saved = st.session_state.get('clock_result')
    if saved is None:
        return None
    from .run_provenance import source_fingerprint, validate

    try:
        if saved[0][1] != source_fingerprint():
            raise ValueError('Source changed. Run the clock again in Research Mode.')
        validate(saved[1]['context'])
    except ValueError as exc:
        st.warning(str(exc))
        return None
    return saved


def render_clock_summary(saved):
    config, result = saved[0][0], saved[1]
    summary = result['summary']
    st.caption('LAST COMPLETED CLOCK RUN · CURRENT SESSION · SIMULATION')
    a, b, c = st.columns(3)
    a.metric('Observed lock fraction', f"{100 * summary['observed_lock_fraction']:.1f}%")
    b.metric('Clock record', f"{summary['record_s']:.3f} s")
    c.metric('Final feedback time error', f"{1e6 * summary['final_time_errors_s']['locked']:.1f} µs")
    st.caption(f"{config['optical']['states']} states · {config['optical']['Bz_G']:g} G · "
               f"{config['cycles']} cycles · seed {config['seed']} · "
               f"{config['plant_backend']} optical solver")
    st.info('Photons determine the feedback correction. An observed lock does not guarantee better '
            'stability: compare the complete feedback and free-running Allan curves before drawing a conclusion.')


def render_overview():
    st.title('A diamond defect. A measurable resonance. A clock reference.')
    st.markdown('Explore how the NV-center spin response becomes an optical signal, how photon '
                'counts guide an oscillator, and when that feedback improves clock stability.')
    left, right = st.columns([1.6, 1], gap='large')
    with left, st.container(border=True):
        st.subheader('The research question')
        st.write('Can photon-based feedback hold an oscillator near an NV resonance—and what '
                 'stability does the resulting clock output achieve under the chosen assumptions?')
        st.markdown('**Physics → ODMR resonance → photon detection → frequency lock → stability**')
        st.caption('Follow this sequence with the sidebar. Detailed models, references and exports '
                   'remain available in Research Mode.')
    with right, st.container(border=True):
        st.subheader('Start with one experiment')
        st.write('Seven-state optical model · local axial 20 G · 297 K')
        st.write('10 ms photon gates · 128 feedback cycles · seed 410024')
        st.caption('Starting settings for the Clock Performance workspace. No simulation runs on '
                   'this landing page. A completed run below retains its own configuration.')
    st.subheader('One experiment, one interpretation')
    saved = completed_clock()
    if saved is None:
        st.info('No completed clock run in this session. Choose Research Mode → Clock Performance '
                'and select “Simulate photon-based clock”. Return here for its summary.')
    else:
        render_clock_summary(saved)
    st.caption('RESEARCH SIMULATION · Model assumptions and synthetic counts; no experimental '
               'clock accuracy claim. The photon-clock model is restricted to local axial 5–50 G, E=0, 297 K.')


def render_demonstration():
    st.title('From an NV center to a clock signal')
    st.write('A nitrogen atom beside a vacant carbon site creates the NV defect in diamond. '
             'Its spin transitions respond to the magnetic field and temperature.')
    for column, title, text in zip(st.columns(3),
            ('01 · Prepare & probe', '02 · Detect photons', '03 · Correct & compare'),
            ('Optical excitation prepares and reads the spin. Scanning the microwave frequency reveals the ODMR response.',
             'Spin-dependent fluorescence changes the detected counts. Photon statistics limit frequency estimation.',
             'The count-based estimate drives oscillator feedback. Phase, time error and Allan deviation describe the output.')):
        with column, st.container(border=True):
            st.subheader(title)
            st.write(text)
    st.info('Part 1 establishes the guided workspace. The rotatable lattice, field geometry and '
            'schematic optical animation are reserved for later parts of the redesign.')
    st.caption('For the implemented quantitative models, open Advanced Research in Research Mode: '
               'ODMR spectroscopy or Optical measurement. Clock Performance provides the existing feedback experiment.')


def render_performance(mode):
    st.title('Clock Performance')
    st.write('Use detected photons to acquire a resonance, apply feedback, and assess the resulting clock output.')
    if mode == MODES[1]:
        from .clock_dashboard import render_clock
        from .run_provenance import source_fingerprint

        papers, error = reference_catalog()
        render_clock(source_fingerprint(), papers, error)
        return
    saved = completed_clock()
    if saved is None:
        st.info('Choose Research Mode to configure and run the photon-clock experiment. '
                'Demonstration Mode displays its completed results without changing inputs or calculating again.')
        return
    render_clock_summary(saved)
    from .clock_dashboard import render_clock_stability

    render_clock_stability(saved[1])
    st.caption('Full record, with acquisition and failures retained. Focused acquisition, correction '
               'and time-error presentation will be added in a later redesign part; their existing exports remain available in Research Mode.')


def render_advanced(mode):
    st.title('Advanced Research')
    st.write('The existing scientific workspaces, with their original models, controls and reproducible exports.')
    if mode == MODES[0]:
        st.info('Select Research Mode in the sidebar to open all scientific controls, references and exports.')
        return
    workspace = st.selectbox('Research workspace', WORKSPACES, key='research_workspace')
    if workspace == WORKSPACES[0]:
        from .legacy_dashboard import render_legacy

        render_legacy()
        return
    from .run_provenance import source_fingerprint

    papers, error = reference_catalog()
    fingerprint = source_fingerprint()
    if workspace == WORKSPACES[1]:
        from .odmr_dashboard import render_odmr
        from .simulation import Config

        config = Config(**st.session_state.get('legacy_config', {}))
        st.caption('The optional clock comparison uses the last Stability & compensation settings '
                   '(or the original defaults). Configure that workspace first to change them.')
        render_odmr(config, fingerprint, papers, error)
    elif workspace == WORKSPACES[2]:
        from .optical_dashboard import render_optical

        render_optical(fingerprint, papers, error)
    else:
        from .clock_dashboard import render_clock

        render_clock(fingerprint, papers, error)


def render_dashboard():
    preserve_workspace_state()
    st.markdown(STYLE, unsafe_allow_html=True)
    with st.sidebar:
        st.title('DiamondClock Lab')
        st.caption('NV-CENTER CLOCK RESEARCH')
        mode = st.radio('Workspace mode', MODES, key='dashboard_mode')
        st.caption('A guided results view.' if mode == MODES[0] else 'Full scientific controls and exports.')
        st.divider()
        section = st.radio('Navigate', SECTIONS, key='dashboard_section')
        st.divider()
        st.caption('Simulation · Python / Streamlit\n\nPhysics → photons → feedback → stability')
    st.caption(f'DIAMONDCLOCK LAB / {mode.upper()} / {section.upper()}')
    if section == SECTIONS[0]:
        render_overview()
    elif section == SECTIONS[1]:
        render_demonstration()
    elif section == SECTIONS[2]:
        render_performance(mode)
    else:
        render_advanced(mode)
