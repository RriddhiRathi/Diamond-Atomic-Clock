"""Phase 4 within the existing Streamlit application; no deployment action."""
from dataclasses import asdict
import hashlib,json
import streamlit as st
import plotly.graph_objects as go
from .clock_parameters import ClockExperiment,ControllerConfig
from .optical_parameters import OpticalConfig,Detector
from .oscillator import OscillatorConfig
from .clock_reporting import calculate_clock,export_clock
from .reporting import zip_files
from .run_provenance import validate


@st.cache_data(show_spinner=False)
def cached_clock(values,fingerprint):
    values=dict(values)
    from .optical_parameters import OpticalRates
    for name,cls in [('optical',OpticalConfig),('rates',OpticalRates),('detector',Detector),('controller',ControllerConfig),('oscillator',OscillatorConfig)]:
        values[name]=cls(**values[name])
    return calculate_clock(ClockExperiment(**values))


def render_clock(fingerprint,paper_bucket,reference_error=None):
    st.subheader('Photon-based frequency lock')
    st.info('SIMULATION · Low-field NV-referenced oscillator, 5–50 G, E=0, 297 K. Counts drive acquisition and feedback. Locking and improved stability are not guaranteed. No SI accuracy or 475 G optical claim.')
    with st.form('clock_controls'):
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
        except ValueError as exc:st.session_state.pop('clock_result',None);st.error(str(exc))
    saved=st.session_state.get('clock_result')
    if saved is None:return
    if saved[0]!=key:st.warning('Clock inputs changed. Simulate again for matching results.');return
    result=saved[1]
    try:validate(result['context'])
    except ValueError as exc:st.error(str(exc));return
    st.metric('Observed lock fraction',f"{100*result['summary']['observed_lock_fraction']:.1f}%")
    st.caption('Lock detection uses counts and reported uncertainty. Hidden truth is reserved for offline error evaluation.')
    fig=go.Figure();data=result['tables']['allan']
    for method in ('unlocked','locked'):
        a=data[(data.method==method)&(data.adev>0)]
        fig.add_scatter(x=a.tau_s,y=a.adev,name=('feedback enabled' if method=='locked' else 'free running')+', full record')
    fig.update_layout(xaxis_type='log',yaxis_type='log',xaxis_title='Averaging time (s)',yaxis_title='Allan deviation')
    st.plotly_chart(fig,width='stretch');st.dataframe(result['tables']['feedback'],hide_index=True)
    digest=hashlib.sha256(json.dumps(paper_bucket,sort_keys=True).encode()).hexdigest()
    if st.button('Prepare clock research bundle',key='prepare_clock_export',disabled=reference_error is not None):
        try:st.session_state['clock_export']=(key,digest,zip_files(export_clock(result,cfg,references=paper_bucket)))
        except ValueError as exc:st.error(str(exc))
    value=st.session_state.get('clock_export')
    if value and value[:2]==(key,digest):
        st.download_button('Download complete clock run',value[2],'DiamondClock_phase4_SIMULATION.zip','application/zip')
