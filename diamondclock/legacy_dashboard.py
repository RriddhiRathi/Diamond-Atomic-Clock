"""Original stability workspaces, rendered only when explicitly selected."""
from dataclasses import asdict
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from .plot_style import scientific_plot, CHART_CONFIG
from diamondclock.simulation import Config, METHODS, simulate, ensemble
from diamondclock.physics import Physics
from diamondclock.reporting import (ROOT,COLORS,benchmarks,export_files,zip_files)

from diamondclock.run_provenance import capture, validate, source_fingerprint

@st.cache_data(show_spinner=False)
def cached_run(values,fingerprint):
    context=capture(config=Config(**values),physics=Physics())
    result=simulate(Config(**values))
    validate(context)
    return (*result,context)

@st.cache_data(show_spinner=False)
def cached_ensemble(values,count,fingerprint):
    context=capture(config=Config(**values),physics=Physics())
    result=ensemble(Config(**values),count)
    validate(context)
    return result


def render_legacy():
    with st.expander('Configure stability experiment',expanded=False):
        st.markdown('**Experiment controls**')
        st.caption('All noise settings are assumptions; physical coefficients come from Lourette 2023.')
        with st.form('controls'):
            n=st.selectbox('Number of samples',[4096,8192,16384,32768,65536,131072],index=3,key='legacy_number_of_samples')
            dt=st.selectbox('Sample interval (s)',[.1,.5,1.,2.,5.,10.],index=2,key='legacy_sample_interval_s')
            seed=st.number_input('Random seed',min_value=0,value=20261019,step=1,key='legacy_random_seed')
            with st.expander('Temperature environment',expanded=True):
                temp=st.number_input('Temperature OU RMS (K)',0.,1.,.05,format='%.4f',key='legacy_temperature_ou_rms_k')
                corr=st.number_input('Temperature correlation time (s)',1.,100000.,300.,key='legacy_temperature_correlation_time_s')
                sine=st.number_input('Thermal cycle peak amplitude (K)',0.,1.,.1,format='%.4f',key='legacy_thermal_cycle_peak_amplitude_k')
                period=st.number_input('Thermal cycle period (s)',100.,1000000.,7200.,key='legacy_thermal_cycle_period_s')
                drift=st.number_input('Temperature drift (K/hour)',-.1,.1,.002,format='%.4f',key='legacy_temperature_drift_k_hour')
            with st.expander('Magnetic environment'):
                bias=st.slider('Axial bias (G)',10.,600.,475.,key='legacy_axial_bias_g')
                bx=st.number_input('Static transverse field (G)',-1.,1.,0.,format='%.4f',key='legacy_static_transverse_field_g')
                brms=st.number_input('Axial field OU RMS (mG)',0.,100.,1.,format='%.3f',key='legacy_axial_field_ou_rms_mg')
                bxrms=st.number_input('Transverse field OU RMS (mG)',0.,100.,.1,format='%.3f',key='legacy_transverse_field_ou_rms_mg')
                bcorr=st.number_input('Field correlation time (s)',1.,100000.,100.,key='legacy_field_correlation_time_s')
            with st.expander('Readout and compensation'):
                er=st.number_input('Electronic readout σ per transition at 1 s (Hz)',0.,10000.,50.,key='legacy_electronic_readout_per_transition_at_1_s_hz')
                nr=st.number_input('Nuclear readout σ per transition at 1 s (Hz)',0.,100.,.03,format='%.4f',key='legacy_nuclear_readout_per_transition_at_1_s_hz')
                rho=st.slider('Error correlation within each pair',-1.,1.,0.,.05,key='legacy_error_correlation_within_each_pair')
                tr=st.number_input('External thermometer σ at 1 s (mK)',0.,1000.,1.,key='legacy_external_thermometer_at_1_s_mk')
                delay=st.number_input('Thermometer delay (s)',0.,1000.,0.,key='legacy_thermometer_delay_s')
                err=st.slider('Slope calibration error (%)',-20.,20.,1.,.25,key='legacy_slope_calibration_error')
            with st.expander('Residual oscillator noise'):
                low=st.number_input('White FM ADEV at 1 s (×10⁻⁹)',0.,10000.,1.,format='%.3f',key='legacy_white_fm_adev_at_1_s_10')
                lorw=st.number_input('Random-walk diffusion (×10⁻¹¹ /√s)',0.,1000.,1.,format='%.3f',key='legacy_random_walk_diffusion_10_s')
                lodrift=st.number_input('Oscillator drift (×10⁻¹³ /s)',-100.,100.,0.,format='%.3f',key='legacy_oscillator_drift_10_s')
            submitted=st.form_submit_button('Run simulation',type='primary',width='stretch',key='run_legacy')
        c=Config(n=int(n),dt_s=dt,seed=int(seed),temp_rms_K=temp,temp_corr_s=corr,temp_sine_K=sine,
                 temp_period_s=period,temp_drift_K_h=drift,Bz_G=bias,Bx_G=bx,Bz_rms_G=brms/1000,
                 Bx_rms_G=bxrms/1000,B_corr_s=bcorr,electron_readout_Hz=er,nuclear_readout_Hz=nr,
                 readout_rho=rho,thermometer_rms_K=tr/1000,thermometer_delay_s=delay,
                 slope_error_pct=err,lo_white_adev_1s=low*1e-9,lo_rw_diffusion=lorw*1e-11,
                 lo_drift_per_s=lodrift*1e-13)
        st.session_state['legacy_config']=asdict(c)

    fingerprint=source_fingerprint()
    if submitted:
        try:
            with st.spinner('Calculating stability and compensation…'):
                value=cached_run(asdict(c),fingerprint)
                validate(value[3])
                st.session_state['legacy_result']=((asdict(c),fingerprint),value)
        except ValueError as exc:st.error(str(exc))
    saved_run=st.session_state.get('legacy_result')
    if saved_run is None:
        st.caption('Configure the experiment and select Run simulation. Opening this workspace does not calculate a record.')
        return
    try:
        saved_key,(trace,a,diag,run_context)=saved_run
        validate(run_context)
        if run_context['config']!=saved_key[0] or run_context['physics']!=asdict(Physics()):
            raise ValueError('Completed stability configuration differs from captured calculation.')
        if saved_key[1]!=fingerprint:raise ValueError('Source changed. Run the stability experiment again.')
    except (ValueError,KeyError,TypeError) as exc:
        st.warning(str(exc));return
    if saved_key!=(asdict(c),fingerprint):
        st.warning('Controls differ from the completed stability run. Results and exports retain that run’s configuration.')
    c=Config(**saved_key[0])

    grid=a[a.method=='composite']
    target=grid.iloc[(grid.tau_s-200).abs().argmin()]
    base=a[(a.method=='electron_average') & (a.tau_s==target.tau_s)].adev.iloc[0]
    cols=st.columns(4)
    cols[0].metric('Record duration',f'{c.n*c.dt_s/3600:.2f} h')
    cols[1].metric(f'Composite ADEV at {target.tau_s:g} s',f'{target.adev:.2e}')
    cols[2].metric('Electronic / composite ADEV',f'{base/target.adev:.2f}×' if target.adev>0 else 'undefined')
    cols[3].metric('Composite nuclear weight',f'{diag["wQ"]:.4f}')
    st.caption('Smaller Allan deviation means less change in the average ticking rate between neighboring averaging windows. A ratio below 1 means the composite is worse at the displayed averaging time.')

    tabs=st.tabs(['Stability lab','Environment & transitions','Compensation study','NV center explained','Research Paper Bucket','Export & methodology'])

    with tabs[0]:
        st.subheader('Frequency stability across averaging time')
        show_published=st.checkbox('Show published measurement limits within this record',True,key='legacy_show_published_measurement_limits_within_this_record')
        show_projections=st.checkbox('Show Hodges 2013 theoretical projections',False,key='legacy_show_hodges_2013_theoretical_projections')
        selected=st.multiselect('Reference signals',list(METHODS),default=list(METHODS),format_func=METHODS.get,key='legacy_reference_signals')
        fig=go.Figure()
        for (key,label),color in zip(METHODS.items(),COLORS):
            if key in selected:
                part=a[a.method==key]
                fig.add_trace(go.Scatter(x=part.tau_s,y=part.adev,mode='lines+markers',name=label+' · simulation',line=dict(color=color,dash=['solid','dash','dot','dashdot','longdash'][list(METHODS).index(key)]),marker_symbol=['circle','diamond','square','triangle-up','cross'][list(METHODS).index(key)],
                                        customdata=part.overlapping_pairs,hovertemplate='τ=%{x:g} s<br>ADEV=%{y:.3e}<br>Overlapping pairs=%{customdata}<extra>%{fullData.name}</extra>'))
        if show_published:
            b=benchmarks();b=b[b.tau_s<=a.tau_s.max()]
            fig.add_trace(go.Scatter(x=b.tau_s,y=b.adev_limit,mode='markers',name='Lourette 2026 · measured upper limits (<)',
                                     marker=dict(symbol='triangle-down-open',size=12,color='#f2f5f7')))
        if show_projections:
            tau=np.geomspace(a.tau_s.min(),a.tau_s.max(),100)
            for level,title in [(1e-7,'Thermal projection'),(1e-12,'Ideal projection')]:
                fig.add_trace(go.Scatter(x=tau,y=level/np.sqrt(tau),name='Hodges 2013 · '+title,line=dict(dash='dot',color='#aaaaaa')))
        fig.update_layout(template='plotly_dark',height=560,xaxis_title='Averaging time τ (s)',yaxis_title='Overlapping Allan deviation σy(τ)',
                          xaxis_type='log',yaxis_type='log',legend=dict(orientation='h',y=-.2),margin=dict(t=20,b=120))
        st.plotly_chart(scientific_plot(fig,height=460),width='stretch',config=CHART_CONFIG)
        st.caption('No detrending. τ is capped at record duration / 10. Overlapping pairs are correlated and are not independent sample counts. A perfectly constant simulated signal has zero ADEV and is absent from a logarithmic plot.')
        st.dataframe(a,hide_index=True,width='stretch')

    with tabs[1]:
        st.subheader('What drives the frequency changes?')
        small=trace.iloc[::max(1,c.n//3000)]
        f=make_subplots(rows=3,cols=1,shared_xaxes=True,vertical_spacing=.08)
        for row,col,label in [(1,'temperature_K','Temperature (K)'),(2,'Bz_G','Axial field (G)'),(3,'lo_total_y','Residual oscillator y')]:
            f.add_trace(go.Scatter(x=small.time_s,y=small[col],name=label,line_width=1),row=row,col=1)
            f.update_yaxes(title_text=label,row=row,col=1)
        f.update_layout(template='plotly_dark',height=640,showlegend=False)
        f.update_xaxes(title_text='Elapsed time (s)',row=3,col=1)
        st.plotly_chart(scientific_plot(f,height=550),width='stretch',config=CHART_CONFIG)
        names=['Electronic f+','Electronic f−','Nuclear f1','Nuclear f2','Electronic half-sum Dobs','Signed nuclear half-sum Qobs']
        table=pd.DataFrame({'Observable':names,'Nominal frequency (Hz)':diag['nominal_Hz'],'Local slope (Hz/K)':diag['slope_Hz_K'],'Fractional slope (/K)':diag['lambda_per_K']})
        st.dataframe(table,hide_index=True,width='stretch')
        st.caption('Exact eigenvalues of the chosen ground-state Hamiltonian; temperature dependence uses a local quadratic approximation. Eigenstates are tracked by overlap. Transition strengths, optical pumping, and pulse sequences are not simulated.')

    with tabs[2]:
        st.subheader('Can compensation survive readout noise?')
        st.latex(r'y_C=w_Dy_D+w_Qy_Q,\quad w_Q=\frac{\lambda_D}{\lambda_D-\lambda_Q},\quad w_D=1-w_Q')
        st.markdown('The weighted sum cancels the calibrated linear temperature response. It preserves a common fractional oscillator term because the weights add to one. Nuclear readout noise is amplified by its weight. [L2026, Eq. (5)]')
        st.write(f"Actual residual first-order temperature response: {diag['thermal_sensitivity_composite_per_K']:.3e} /K.")
        count=st.select_slider('Independent model realizations',[3,5,10,20,40],value=10,key='legacy_independent_model_realizations')
        if st.button('Calculate ensemble variability',key='run_ensemble'):
            with st.spinner(f'Calculating {count} independent realizations…'):
                raw,q=cached_ensemble(asdict(c),count,fingerprint)
            st.session_state['ensemble_result']=((asdict(c),fingerprint),raw,q)
            st.session_state.pop('export',None)
        saved=st.session_state.get('ensemble_result')
        if saved is not None and saved[0]==(asdict(c),fingerprint):
            raw,q=saved[1:]
            ef=go.Figure()
            for (key,label),color in zip(METHODS.items(),COLORS):
                v=q[q.method==key]
                ef.add_trace(go.Scatter(x=v.tau_s,y=v.p95,line=dict(width=0),showlegend=False))
                ef.add_trace(go.Scatter(x=v.tau_s,y=v.p05,line=dict(width=0),fill='tonexty',opacity=.18,fillcolor=color,showlegend=False))
                ef.add_trace(go.Scatter(x=v.tau_s,y=v['median'],name=label,line_color=color))
            ef.update_layout(template='plotly_dark',xaxis_type='log',yaxis_type='log',xaxis_title='τ (s)',yaxis_title='ADEV',height=500)
            st.plotly_chart(scientific_plot(ef,height=460),width='stretch',config=CHART_CONFIG)
            st.caption('Shading is the 5th–95th percentile across simulated records. It is conditional on the model and is not a confidence interval for an experimental clock. Small ensembles give rough tail estimates.')
        st.markdown('Try increasing nuclear readout noise or slope error, then compare the curves. Set all environment and oscillator noise to zero to isolate readout. Set slope error to zero to inspect ideal local calibration; quadratic temperature effects remain.')

    with tabs[3]:
        st.subheader('A tiny defect with several useful ticking rates')
        st.markdown('An NV center is a nitrogen atom next to a missing carbon atom in diamond. The negatively charged defect has an electron spin with three ground-state levels. The intrinsic nitrogen-14 nucleus also has three spin levels, giving nine combined states. A green laser prepares and reads the spins; microwave and radio-frequency fields probe transitions. [L2023, Sec. II–III]')
        st.latex(r'H/h=D S_z^2+Q I_z^2+A_\parallel S_z I_z+A_\perp(S_x I_x+S_y I_y)+\gamma_e\mathbf{B}\cdot\mathbf{S}-\gamma_n\mathbf{B}\cdot\mathbf{I}')
        st.caption('Cyclic frequencies in Hz; dimensionless spin operators. L2023 Eq. (1). No 2π factor. Only nitrogen-14 is implemented.')
        st.markdown('Temperature moves the spin energy levels. A magnetic field shifts electronic transitions in opposite directions, so their average rejects much of that shift. It does not remove temperature sensitivity. Combining electronic and nuclear signals can cancel first-order temperature dependence because their fractional thermal slopes differ. [L2026, Eqs. (4)–(5)]')
        st.markdown('**Reading stability:** choose an averaging time τ, such as 100 s. Average the fractional ticking-rate error over a window of that length and compare it with the next window. Allan deviation summarizes those changes across the record. Smaller is more stable; stability alone does not establish accuracy.')
        st.latex(r'\sigma_y^2(m\Delta t)=\frac{1}{2(N-2m+1)}\sum_{j=0}^{N-2m}(\bar y_{j+m,m}-\bar y_{j,m})^2')
        st.caption('NIST SP 1065, Eq. (10), printed p.16. Samples are treated as contiguous rectangular interval averages.')

    with tabs[4]:
        from .research_pages import render_paper_bucket
        paper_bucket,catalog_digest,reference_error=render_paper_bucket(c,standalone=False)

    with tabs[5]:
        st.subheader('A reproducible record for your manuscript')
        st.markdown('Export the full time series, Allan results, configuration, source and parameter provenance, environment versions, checksums, and vector SVG/PDF figure. The export figure includes all five signals, irrespective of visibility selections above.')
        saved=st.session_state.get('ensemble_result')
        q=raw=None
        if saved is not None and saved[0]==(asdict(c),fingerprint):raw,q=saved[1:]
        if st.button('Prepare reproducible export',type='primary',key='prepare_export',disabled=reference_error is not None):
            with st.spinner('Building dataset and vector figures…'):
                try:
                    files=export_files(trace,a,c,diag,quantiles=q,ensemble_raw=raw,
                                       run_provenance=run_context,references=paper_bucket)
                except ValueError as exc:
                    st.error(str(exc));st.stop()
            st.session_state['export']=((asdict(c),fingerprint,catalog_digest),files)
        saved_export=st.session_state.get('export')
        if saved_export is not None and saved_export[0]==(asdict(c),fingerprint,catalog_digest):
            files=saved_export[1]
            st.download_button('Download complete run (.zip)',zip_files(files),'DiamondAtomicClock_run_SIMULATION.zip','application/zip')
            left,right=st.columns(2)
            left.download_button('Download vector SVG',files['stability_SIMULATION.svg'],'stability_SIMULATION.svg','image/svg+xml')
            right.download_button('Download vector PDF',files['stability_SIMULATION.pdf'],'stability_SIMULATION.pdf','application/pdf')
        st.download_button('Download active configuration',json.dumps(asdict(c),indent=2),'config.json','application/json')
        st.markdown((ROOT/'docs/METHODOLOGY.md').read_text(encoding='utf-8'))
