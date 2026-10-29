"""Dashboard shell. Clock/optical experiments retain their explicit run controls."""
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
        if key.startswith(('legacy_', 'clock_', 'odmr_', 'optical_', 'research_', 'nv_')):
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
    """Read only a source/configuration/hash-validated completed run."""
    from .clock_presentation import completed_clock as read_completed
    return read_completed()


def render_clock_summary(saved):
    from .clock_presentation import render_summary
    render_summary(saved[0][0],saved[1])


def navigate(section, mode=None, view=None):
    st.session_state['dashboard_section'] = section
    if mode is not None:
        st.session_state['dashboard_mode'] = mode
    if view is not None:
        st.session_state['clock_view'] = view


def render_overview():
    st.title('DiamondClock Lab')
    st.write('Can photon measurements hold an oscillator near a diamond NV resonance—and does '
             'that feedback improve its simulated frequency stability? Follow the evidence from spin to clock output.')
    st.markdown('**NV spin system → ODMR → photon measurement → frequency feedback → Allan deviation**')
    a,b,c = st.columns(3)
    a.button('Explore NV physics & ODMR',key='nav_nv',on_click=navigate,args=(SECTIONS[1],))
    b.button('Inspect clock evidence',key='nav_performance',on_click=navigate,args=(SECTIONS[2],))
    c.button('Open research tools',key='nav_research',on_click=navigate,args=(SECTIONS[3],MODES[1]))
    st.divider()
    saved = completed_clock()
    if saved is None:
        st.subheader('Follow one clock experiment')
        st.info('No completed clock run in this session. Run a configured experiment or inspect a verified '
                'historical example. Results appear here after a successful session run.')
        a,b = st.columns(2)
        a.button('Configure a clock run',key='nav_clock_run',on_click=navigate,
                 args=(SECTIONS[2],MODES[1],'Current session run'))
        b.button('Browse saved experiments',key='nav_clock_archive',on_click=navigate,
                 args=(SECTIONS[2],None,'Verified historical example'))
        st.caption('Examples include seven/21-state lock, failed acquisition or feedback, and observed lock '
                   'with worse stability. Opening a saved example reads original data; it does not rerun the experiment.')
    else:
        render_clock_summary(saved)
    st.caption('RESEARCH SIMULATION · Model assumptions and synthetic counts; no experimental '
               'clock accuracy claim. The photon-clock model is restricted to local axial 5–50 G, E=0, 297 K.')


def render_demonstration():
    from .nv_dashboard import render_nv_demonstration

    render_nv_demonstration()


def render_performance(mode):
    st.title('Clock Performance')
    st.write('Use detected photons to acquire a resonance, apply feedback, and assess the resulting clock output.')
    if mode == MODES[1]:
        from .clock_dashboard import render_clock
        from .run_provenance import source_fingerprint

        papers, error = reference_catalog()
        render_clock(source_fingerprint(), papers, error)
        return
    from .clock_presentation import render_workspace
    render_workspace()
    st.caption('Configure new runs and prepare current-source research bundles in Research Mode. '
               'Existing archived figures and bundles retain their original metadata.')


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
