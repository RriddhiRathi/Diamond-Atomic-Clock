"""Phase 4 within the existing Streamlit application; no deployment action."""
from dataclasses import asdict
import hashlib,json
import streamlit as st
from .clock_parameters import ClockExperiment,ControllerConfig
from .optical_parameters import OpticalConfig,Detector
from .oscillator import OscillatorConfig
from .clock_reporting import calculate_clock,export_clock
from .reporting import zip_files
from .clock_results import experiment
from .clock_presentation import render_workspace, render_vector_downloads, allan_figure


@st.cache_data(show_spinner=False)
def cached_clock(values,fingerprint):
    values=dict(values)
    from .optical_parameters import OpticalRates
    for name,cls in [('optical',OpticalConfig),('rates',OpticalRates),('detector',Detector),('controller',ControllerConfig),('oscillator',OscillatorConfig)]:
        values[name]=cls(**values[name])
    return calculate_clock(ClockExperiment(**values))


def render_clock(fingerprint,paper_bucket,reference_error=None):
    st.caption('Photon-based NV reference · SIMULATION · local axial 5–50 G, E=0, 297 K. Lock and stability improvement are evaluated separately.')
    with st.expander('Configure a photon-clock experiment',expanded=st.session_state.get('clock_result') is None and st.session_state.get('clock_view','Current session run')=='Current session run'), st.form('clock_controls'):
        a,b,c=st.columns(3)
        states=a.selectbox('Clock optical states',[7,21],key='clock_states')
        field=b.number_input('Clock local axial field (G)',5.,50.,20.,key='clock_field')
        centers=c.number_input('Independent detected NV centers',1,10000,100,key='clock_centers')
        cycles=a.selectbox('Feedback cycles',[32,128,512,1024],index=1,key='clock_cycles')
        gain=b.number_input('Integral gain (1/s)',0.,100.,3.,key='clock_gain')
        latency=c.number_input('Correction latency (ms)',0.,1000.,10.,key='clock_latency')
        drift=a.number_input('Free oscillator drift (Hz/s)',-1e5,1e5,1e4,key='clock_drift')
        gate=b.number_input('Photon gate (ms)',1.,100.,10.,key='clock_gate')
        seed=c.number_input('Clock random seed',0,2**31-1,410024,key='clock_seed')
        st.caption('The 21-state long-run option uses the benchmarked rate reduction; seven states use the Lindblad reference. Gates and latency use local-clock ticks. Probe dither is on a separate branch from the clock output.')
        submitted=st.form_submit_button('Simulate photon-based clock',key='run_clock')
    cfg=ClockExperiment(optical=OpticalConfig(states=states,Bz_G=field),detector=Detector(centers=int(centers)),cycles=int(cycles),
        gate_s=gate/1000,native_dt_s=min(.002,gate/1000),controller=ControllerConfig(integral_per_s=gain,latency_s=latency/1000),
        oscillator=OscillatorConfig(drift_Hz_s=drift),seed=int(seed),plant_backend='lindblad' if states==7 else 'rate')
    key=(asdict(cfg),fingerprint)
    if submitted:
        try:
            with st.spinner('Acquiring a resonance and running causal photon feedback…'):
                st.session_state['clock_result']=(key,cached_clock(*key))
            st.session_state['clock_view']='Current session run'
        except ValueError as exc:st.error(str(exc))
    saved=render_workspace()
    if saved is None:return
    saved_key,result=saved
    if saved_key!=key:
        st.warning('Clock inputs changed. The displayed result retains its completed-run configuration. Simulate again for matching results.')
    saved_config=experiment(saved_key[0])
    with st.expander('Research diagnostics and completed configuration'):
        st.json(saved_key[0])
        table=st.selectbox('Diagnostic table',list(result['tables']),index=list(result['tables']).index('feedback'),key='clock_table_view')
        st.dataframe(result['tables'][table],hide_index=True)
        st.caption('evaluation_* tables are offline truth diagnostics, never controller inputs. All raw tables are retained in the research bundle.')
        st.json({k:v for k,v in result['context'].items() if k!='files'})
    st.subheader('Reproducible research outputs')
    st.caption('CSV tables, SVG/PDF figures, configuration, references and captured sources for this completed run. Also available in Exports & Documentation once prepared.')
    digest=hashlib.sha256(json.dumps(paper_bucket,sort_keys=True).encode()).hexdigest()
    if st.button('Prepare clock research bundle',key='prepare_clock_export',disabled=reference_error is not None):
        try:
            files=export_clock(result,saved_config,references=paper_bucket)
            st.session_state['clock_export']=(saved_key,digest,zip_files(files))
            st.session_state['clock_export_figures']=(saved_key,digest,{k:v for k,v in files.items() if k.endswith(('.svg','.pdf'))})
        except ValueError as exc:st.error(str(exc))
    value=st.session_state.get('clock_export')
    if value and value[:2]==(saved_key,digest):
        st.download_button('Download complete clock run',value[2],'DiamondClock_phase4_SIMULATION.zip','application/zip')
    figures=st.session_state.get('clock_export_figures')
    if figures and figures[:2]==(saved_key,digest):
        render_vector_downloads(figures[2])


def render_clock_stability(result):
    """Compatibility entry point for the original shared full-record chart."""
    st.plotly_chart(allan_figure(result),width='stretch')
