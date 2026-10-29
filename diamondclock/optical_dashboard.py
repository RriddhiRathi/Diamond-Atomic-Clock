"""Optical measurement tab in the existing app; independent of the clock sidebar."""
from dataclasses import asdict
import hashlib
import json
import streamlit as st
from .plot_style import scientific_plot, CHART_CONFIG
import plotly.graph_objects as go
from .optical_parameters import OpticalConfig, OpticalExperiment, OpticalRates, Detector
from .optical_reporting import calculate_optical, export_optical
from .reporting import zip_files
from .run_provenance import validate


@st.cache_data(show_spinner=False)
def cached_optical(values,fingerprint):
    values=dict(values)
    for key,cls in [('optical',OpticalConfig),('rates',OpticalRates),('detector',Detector)]:
        values[key]=cls(**values[key])
    return calculate_optical(OpticalExperiment(**values))


def render_optical(fingerprint,paper_bucket,reference_error=None):
    st.subheader('Optical excitation and photon measurements')
    st.caption('SIMULATION · Single local axial NV, 5–50 G, nominal 297 K. Contrast follows optical populations. These settings are independent of the 475 G clock sidebar; no frequency lock is simulated.')
    with st.form('optical_controls'):
        a,b,c=st.columns(3)
        states=a.selectbox('Optical model states',[7,21],key='optical_states')
        field=b.number_input('Optical axial field (G)',5.,50.,20.,key='optical_field')
        pump=c.number_input('Optical pump rate (million/s)',.1,20.,2.,key='optical_pump')
        rabi=a.number_input('Isolated-line Rabi frequency (kHz)',0.,1000.,200.,key='optical_rabi')
        seed=b.number_input('Optical random seed',0,2**31-1,310024,key='optical_seed')
        points=c.selectbox('Optical scan points',[41,81,161],index=1,key='optical_points')
        st.caption('Preset: published fitted Tetienne NV E optical rates. Pump, microwave, detector and ground relaxation are assumed. Fast scan counts use a labeled low-efficiency Poisson approximation; bundles include number-resolved reference distributions.')
        submitted=st.form_submit_button('Calculate optical fluorescence',key='run_optical')
    experiment=OpticalExperiment(optical=OpticalConfig(states=states,Bz_G=field,pump_s=pump*1e6,rabi_Hz=rabi*1e3),points=points,seed=int(seed))
    key=(asdict(experiment),fingerprint)
    if submitted:
        try:
            with st.spinner('Solving optical populations and photon measurements…'):
                st.session_state['optical_result']=(key,cached_optical(*key))
        except ValueError as exc:
            st.session_state.pop('optical_result',None);st.error(str(exc))
    saved=st.session_state.get('optical_result')
    if saved is None:return
    if saved[0]!=key:
        st.warning('Optical inputs changed. Calculate again to update measurements.');return
    result=saved[1]
    try:validate(result['context'])
    except ValueError as exc:st.error(str(exc));return
    data=result['tables']['fluorescence_measurements'];on=data[data.microwave=='on']
    fig=go.Figure()
    fig.add_scatter(x=on.microwave_frequency_Hz/1e6,y=on.expected_counts,name='Optical-model expected counts')
    fig.add_scatter(x=on.microwave_frequency_Hz/1e6,y=on.detected_counts,mode='markers',name='Synthetic detected counts')
    fig.update_layout(xaxis_title='Microwave frequency (MHz)',yaxis_title='Photons per gate')
    st.plotly_chart(scientific_plot(fig),width='stretch',config=CHART_CONFIG);st.dataframe(data,hide_index=True)
    st.metric('Maximum expected contrast on sampled grid',f"{100*result['summary']['expected_maximum_grid_contrast']:.2f}%")
    st.caption('Contrast shown uses generated mean counts, including background. It is not an inferred resonance or an accuracy measurement.')
    digest=hashlib.sha256(json.dumps(paper_bucket,sort_keys=True).encode()).hexdigest()
    if st.button('Prepare optical research bundle',key='export_optical',disabled=reference_error is not None):
        try:
            files=export_optical(result,experiment,references=paper_bucket)
            st.session_state['optical_export']=(key,digest,zip_files(files))
        except ValueError as exc:st.error(str(exc))
    exported=st.session_state.get('optical_export')
    if exported and exported[:2]==(key,digest):
        st.download_button('Download optical research bundle',exported[2],'DiamondClock_optical_SIMULATION.zip','application/zip')
