"""Unified dashboard navigation; experiments run only on explicit submission."""
import streamlit as st

SECTIONS = ('Overview','NV-Center & ODMR','Clock Performance','Research Tools','Paper Bucket','Exports & Documentation')
WORKSPACES = ('Stability & compensation','ODMR spectroscopy','Optical measurement','Frequency lock')
OLD_SECTIONS = {'Clock Overview':'Overview','NV-Center Demonstration':'NV-Center & ODMR','Advanced Research':'Research Tools'}

STYLE = '''<style>
[data-testid="stMainBlockContainer"] {max-width:1600px;padding:1.25rem 2rem 3rem}
h1 {font-size:2rem!important;letter-spacing:-.035em;padding-top:0}
h2 {font-size:1.4rem!important;letter-spacing:-.02em}
h3 {font-size:1.15rem!important;letter-spacing:-.015em}
[data-testid="stMetric"] {padding:.7rem .85rem;border:1px solid #2b394b;border-radius:10px;background:#101722}
[data-testid="stMetricValue"] {font-size:1.55rem}
[data-testid="stMetricLabel"] {font-size:.82rem;line-height:1.35}
[data-testid="stSidebar"] {border-right:1px solid #263448}
[data-testid="stSidebar"] h1 {font-size:1.45rem!important}
[data-testid="stCaptionContainer"] {line-height:1.45;color:#b9c5d6}
[data-testid="stVerticalBlock"] {gap:.8rem}
[data-testid="stExpander"] {border-color:#293749}
@media(max-width:900px) {[data-testid="stMainBlockContainer"] {padding:1rem}}
</style>'''


def migrate_navigation():
    """Rename old routes and remove the mode gate without touching experiments."""
    old=st.session_state.get('dashboard_section','Overview')
    new=OLD_SECTIONS.get(old,old)
    if new not in SECTIONS:new='Overview'
    if old!=new:st.session_state['dashboard_section']=new
    st.session_state.pop('dashboard_mode',None)


def preserve_workspace_state():
    """Retain hidden inputs/results/exports; button events use separate keys."""
    for key in list(st.session_state):
        if key.startswith(('legacy_','clock_','odmr_','optical_','research_','nv_')):
            st.session_state[key]=st.session_state[key]


def reference_catalog():
    from .research_pages import catalog
    papers,error=catalog()
    if error:st.error('Persistent references unavailable: '+error)
    return papers,error


def completed_clock():
    from .clock_presentation import completed_clock as read_completed
    return read_completed()


def render_clock_summary(saved):
    from .clock_presentation import render_summary
    render_summary(saved[0][0],saved[1])


def navigate(section,workspace=None,view=None):
    st.session_state['dashboard_section']=section
    if workspace is not None:st.session_state['research_workspace']=workspace
    if view is not None:st.session_state['clock_view']=view


def render_overview():
    st.title('DiamondClock Lab')
    st.write('Explore whether photon feedback can stabilize an oscillator referenced to a diamond NV resonance.')
    st.markdown('**NV spin → ODMR → photon measurement → feedback → clock stability**')
    a,b,c=st.columns(3)
    a.button('NV center & ODMR',key='nav_nv',on_click=navigate,args=(SECTIONS[1],),width='stretch')
    b.button('Clock performance',key='nav_performance',on_click=navigate,args=(SECTIONS[2],),width='stretch')
    c.button('Research tools',key='nav_research',on_click=navigate,args=(SECTIONS[3],),width='stretch')
    saved=completed_clock()
    if saved is None:
        with st.container(border=True):
            st.subheader('Inspect a clock experiment')
            st.write('No completed clock run in this session. Open a saved experiment or configure a new run.')
            a,b=st.columns(2)
            a.button('Browse saved experiments',key='nav_clock_archive',on_click=navigate,
                     args=(SECTIONS[2],None,'Verified historical example'),type='primary',width='stretch')
            b.button('Configure a new run',key='nav_clock_run',on_click=navigate,
                     args=(SECTIONS[2],None,'Current session run'),width='stretch')
            st.caption('Saved examples include observed lock, failed lock, and lock with worse stability.')
    else:render_clock_summary(saved)
    with st.expander('Scientific scope & limitations'):
        st.write('Research simulation; no experimental clock accuracy claim. The optical clock uses local '
                 'axial 5–50 G, E=0 and 297 K. Optical, detector, oscillator and controller assumptions '
                 'remain documented in Paper Bucket and Exports & Documentation. The interactive ODMR '
                 'illustration is independent of the photon-clock experiment.')


def render_performance():
    from .clock_dashboard import render_clock
    from .run_provenance import source_fingerprint
    st.title('Clock Performance')
    papers,error=reference_catalog()
    render_clock(source_fingerprint(),papers,error)


def render_research():
    st.title('Research Tools')
    workspace=st.selectbox('Research workspace',WORKSPACES,key='research_workspace')
    if workspace==WORKSPACES[0]:
        from .legacy_dashboard import render_legacy
        render_legacy()
        return
    from .run_provenance import source_fingerprint
    papers,error=reference_catalog()
    fingerprint=source_fingerprint()
    if workspace==WORKSPACES[1]:
        from .odmr_dashboard import render_odmr
        from .simulation import Config
        render_odmr(Config(**st.session_state.get('legacy_config',{})),fingerprint,papers,error)
    elif workspace==WORKSPACES[2]:
        from .optical_dashboard import render_optical
        render_optical(fingerprint,papers,error)
    else:
        from .clock_dashboard import render_clock
        render_clock(fingerprint,papers,error)


def render_dashboard():
    migrate_navigation()
    preserve_workspace_state()
    st.markdown(STYLE,unsafe_allow_html=True)
    with st.sidebar:
        st.title('DiamondClock Lab')
        st.caption('NV-CENTER CLOCK RESEARCH')
        section=st.radio('Navigation',SECTIONS,key='dashboard_section')
        st.caption('Simulation · source-traceable research')
    if section==SECTIONS[0]:render_overview()
    elif section==SECTIONS[1]:
        from .nv_dashboard import render_nv_demonstration
        render_nv_demonstration()
    elif section==SECTIONS[2]:render_performance()
    elif section==SECTIONS[3]:render_research()
    elif section==SECTIONS[4]:
        from .research_pages import render_paper_bucket
        render_paper_bucket()
    else:
        from .research_pages import render_exports
        render_exports()
