"""ODMR tab for the existing Streamlit app; no separate application."""
from dataclasses import asdict
import hashlib
import json
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from .plot_style import scientific_plot, CHART_CONFIG
from .odmr import ODMRConfig, spherical, transform, odmr_parameter_provenance
from .odmr_bridge import ReadoutScenario
from .odmr_reporting import calculate, export_odmr
from .simulation import Config, METHODS
from .reporting import zip_files
from .run_provenance import validate


@st.cache_data(show_spinner=False)
def cached_odmr(values, clock_values, readout_values, fingerprint):
    return calculate(ODMRConfig(**values),
        Config(**clock_values) if clock_values is not None else None,
        ReadoutScenario(**readout_values) if readout_values is not None else None)


def render_odmr(clock_config, fingerprint, paper_bucket, reference_error=None):
    st.subheader('ODMR spectroscopy')
    st.caption('SIMULATION · Four NV orientations, electron + nitrogen-14 ground states. Fluorescence is a transition-strength proxy with assumed contrast and Lorentzian linewidth, not an optical pumping calculation.')
    with st.form('odmr_controls'):
        a,b,c=st.columns(3)
        field=a.number_input('ODMR magnetic magnitude (G)',0.,650.,18.,key='odmr_B')
        theta=b.slider('Magnetic polar angle (degrees)',0.,180.,65.,key='odmr_theta')
        phi=c.slider('Magnetic azimuth (degrees)',-180.,180.,25.,key='odmr_phi')
        frame=st.selectbox('Magnetic direction frame',['Lab cubic axes','NV1','NV2','NV3','NV4'],key='odmr_frame')
        temperature=a.number_input('ODMR temperature (K)',292.,302.,297.,key='odmr_T')
        width=b.number_input('ODMR FWHM (MHz)',.001,10.,.3,format='%.3f',key='odmr_width')
        contrast=c.number_input('Spectral contrast budget',0.,.2,.03,format='%.3f',key='odmr_contrast')
        with st.expander('Electric field, microwave polarization and orientation weights'):
            ec1,ec2,ec3=st.columns(3)
            ef=ec1.number_input('Lab electric magnitude (V/m)',0.,1e7,0.,key='odmr_E')
            et=ec2.slider('Electric polar angle (degrees)',0.,180.,90.,key='odmr_Etheta')
            ep=ec3.slider('Electric azimuth (degrees)',-180.,180.,45.,key='odmr_Ephi')
            mt=ec1.slider('Microwave polar angle (degrees)',0.,180.,90.,key='odmr_mtheta')
            mp=ec2.slider('Microwave azimuth (degrees)',-180.,180.,0.,key='odmr_mphi')
            st.caption('Linear microwave polarization; amplitude is normalized. No power broadening or predicted contrast from power.')
            weights=tuple(st.number_input(f'NV{k} relative population weight',0.,100.,1.,key=f'odmr_weight{k}') for k in range(1,5))
        auto=st.checkbox('Automatically cover active electronic resonances',True,key='odmr_auto')
        fmin=a.number_input('Frequency start (MHz)',1.,10000.,2750.,key='odmr_min')
        fmax=b.number_input('Frequency stop (MHz)',1.,10000.,3000.,key='odmr_max')
        points=c.selectbox('ODMR frequency points',[1001,3001,5001,10001,20001],index=2,key='odmr_points')
        compare=st.checkbox('Compare original clock with ODMR-informed readout',False,key='odmr_compare')
        st.caption('Comparison uses the clock sidebar bias and its single NV frame with E=0. Only electronic readout changes. It does not lock the clock to the ensemble spectrum.')
        rc1,rc2,rc3=st.columns(3)
        line_contrast=rc1.number_input('Contrast of each addressed clock line',.001,.1,.03,format='%.3f',key='odmr_line_contrast')
        rate=rc2.number_input('Clock detected photons per live second',1.,1e12,1e6,format='%.1f',key='odmr_photons')
        duty=rc3.number_input('Clock live-time fraction',.001,1.,1.,key='odmr_duty')
        st.caption('Clock comparison reuses the FWHM above as a separate assumed single-line clock linewidth. Half the live time is allocated to each electronic line; nuclear readout remains the sidebar assumption. Requires isolated lines and paired correlation = 0.')
        submitted=st.form_submit_button('Calculate ODMR',type='primary',key='run_odmr')
    bvec=spherical(field,theta,phi)
    if frame!='Lab cubic axes':bvec=transform(bvec,int(frame[-1])-1,inverse=True)
    values=ODMRConfig(temperature_K=temperature,B_lab_G=tuple(bvec),
        E_lab_V_m=tuple(spherical(ef,et,ep)),microwave_lab=tuple(spherical(1,mt,mp)),
        weights=weights,linewidth_Hz=width*1e6,contrast=contrast,
        start_Hz=fmin*1e6,stop_Hz=fmax*1e6,points=int(points))
    # Conservative coverage estimate uses the shared D(T), full |B|, hyperfine and E margins.
    if auto:
        from .physics import Physics, thermal_parameters
        from dataclasses import replace
        p=Physics();d=thermal_parameters(temperature,p)[0]
        margin=p.gamma_e_Hz_G*field+max(20e6,5*width*1e6)+.17*ef
        values=replace(values,start_Hz=max(1.,d-margin),stop_Hz=d+margin)
    readout=ReadoutScenario(width*1e6,line_contrast,rate,duty)
    key=(asdict(values),asdict(clock_config) if compare else None,
         asdict(readout) if compare else None,fingerprint)
    if submitted:
        try:
            with st.spinner('Calculating NV spectra and selected clock comparison…'):
                result=cached_odmr(*key)
            st.session_state['odmr_result']=(key,result)
            st.session_state.pop('odmr_export',None)
        except ValueError as exc:
            st.session_state.pop('odmr_result',None)
            st.error(str(exc))
    saved=st.session_state.get('odmr_result')
    if saved is None:
        st.caption('Choose parameters and calculate ODMR to display spectra, energy levels and exports.')
        return
    if saved[0]!=key:
        st.warning('Inputs changed. Calculate ODMR again to update results and exports.')
        return
    result=saved[1]
    try:validate(result['context'])
    except ValueError as exc:
        st.error(str(exc));return
    data=result['spectrum'];colors=['#149ca8','#ed9d38','#aa6bd3','#2470dd']
    fig=go.Figure()
    for k,color in enumerate(colors,1):
        fig.add_trace(go.Scatter(x=data.frequency_Hz/1e6,y=data[f'NV{k}_fluorescence'],name=f'NV{k}',line=dict(color=color,width=1)))
    fig.add_trace(go.Scatter(x=data.frequency_Hz/1e6,y=data.combined_fluorescence,name='Weighted ensemble',line=dict(color='#eeeeee',width=2.5)))
    fig.update_layout(template='plotly_dark',xaxis_title='Microwave frequency (MHz)',yaxis_title='Normalized fluorescence (model)',height=480)
    st.plotly_chart(scientific_plot(fig),width='stretch',config=CHART_CONFIG,key='odmr_spectrum_plot')
    if (values.stop_Hz-values.start_Hz)/(values.points-1)>values.linewidth_Hz/5:
        st.warning('Frequency grid is coarse relative to FWHM. Narrow the window or increase points; peak depth may be under-resolved.')
    selected=st.selectbox('NV orientation for level and sensitivity tables',[1,2,3,4],key='odmr_level_nv')
    sweep=result['sweep'];fig=go.Figure()
    for rank in range(9):
        part=sweep[(sweep.orientation==selected)&(sweep.energy_rank==rank)]
        fig.add_trace(go.Scatter(x=part.field_G,y=part.energy_Hz/1e6,name=f'Energy rank {rank}',mode='lines'))
    fig.update_layout(template='plotly_dark',xaxis_title='Field magnitude along selected direction (G)',yaxis_title='Energy / h above lowest level (MHz)',height=440)
    st.plotly_chart(scientific_plot(fig),width='stretch',config=CHART_CONFIG,key='odmr_levels_plot')
    st.caption('Energy ranks can exchange spin character at crossings; these curves do not claim state tracking. Degenerate transition manifolds are summed before constructing spectra.')
    st.dataframe(result['sensitivities'].query('orientation == @selected'),hide_index=True,width='stretch')
    if 'comparison' in result:
        comp=result['comparison'];a=comp['allan']
        st.markdown('#### Clock stability: original assumptions versus ideal ODMR readout')
        d=comp['bridge_diagnostics']
        st.write(f"Electronic per-line noise at 1 s: original {clock_config.electron_readout_Hz:.3g} Hz; ODMR-informed {d['per_line_sigma_at_1s_Hz']:.3g} Hz. Same seed, environment, nuclear readout, oscillator noise and compensation equations.")
        methods=st.multiselect('Clock comparison signals',list(METHODS),default=['single_electron','electron_average','composite'],format_func=METHODS.get,key='odmr_compare_methods')
        fig=go.Figure()
        for method in methods:
            for scenario,dash in [('Original assumed readout','dash'),('ODMR-informed ideal readout','solid')]:
                part=a[(a.method==method)&(a.scenario==scenario)&(a.adev>0)]
                fig.add_trace(go.Scatter(x=part.tau_s,y=part.adev,name=METHODS[method]+' · '+scenario,line=dict(dash=dash)))
        fig.update_layout(template='plotly_dark',xaxis_type='log',yaxis_type='log',xaxis_title='Averaging time (s)',yaxis_title='Overlapping Allan deviation',height=500)
        st.plotly_chart(scientific_plot(fig),width='stretch',config=CHART_CONFIG,key='odmr_comparison_plot')
        st.caption('SIMULATED paired records, not experimental confidence intervals. DRE2011 Eq. (3) supplies an ideal resolved-line photon-noise estimate; linewidth, contrast and rate are assumptions. This comparison can worsen stability and does not establish clock accuracy.')
        st.json(d,expanded=False)
    st.dataframe(odmr_parameter_provenance(values),hide_index=True,width='stretch')
    with st.expander('ODMR equations, sources and original intern attribution'):
        from .reporting import ROOT
        st.markdown((ROOT/'docs/ODMR_METHODS.md').read_text(encoding='utf-8'))
        st.markdown((ROOT/'references/odmr_equation_map.md').read_text(encoding='utf-8'))
        st.download_button('Download original MATLAB transcript',(ROOT/'legacy/matlab/intern_odmr_as_supplied.m.txt').read_bytes(),'intern_odmr_as_supplied.m.txt','text/plain',key='download_original_matlab')
    digest=hashlib.sha256(json.dumps(paper_bucket,sort_keys=True).encode()).hexdigest()
    if st.button('Prepare ODMR research export',key='prepare_odmr_export',disabled=reference_error is not None):
        try:
            with st.spinner('Preparing CSV datasets, source snapshots and vector figures…'):
                files=export_odmr(result,values,references=paper_bucket)
            st.session_state['odmr_export']=(key,digest,files)
        except ValueError as exc:st.error(str(exc))
    saved_export=st.session_state.get('odmr_export')
    if reference_error is None and saved_export and saved_export[:2]==(key,digest):
        files=saved_export[2]
        st.download_button('Download ODMR research bundle',zip_files(files),'DiamondClock_ODMR_SIMULATION.zip','application/zip',key='download_odmr')
        st.download_button('Download ODMR vector SVG',files['odmr_spectrum_SIMULATION.svg'],'odmr_spectrum_SIMULATION.svg','image/svg+xml',key='download_odmr_svg')
        st.download_button('Download ODMR vector PDF',files['odmr_spectrum_SIMULATION.pdf'],'odmr_spectrum_SIMULATION.pdf','application/pdf',key='download_odmr_pdf')
