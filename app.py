"""Run: python -m streamlit run app.py"""
from dataclasses import asdict
import json
import sqlite3
import hashlib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from diamondclock.simulation import Config, METHODS, simulate, ensemble
from diamondclock.physics import Physics
from diamondclock.reporting import (ROOT,COLORS,sources,provenance,benchmarks,export_files,zip_files)

from diamondclock.reference_store import ReferenceStore, verification_label, catalog_bytes, bibtex_bytes
from diamondclock.run_provenance import capture, validate, source_fingerprint

st.set_page_config(page_title='Diamond Atomic Clock',page_icon='💎',layout='wide')
st.markdown('''<style>
.stApp {background:linear-gradient(150deg,#080b10,#101722 60%,#080b10)}
h1 {letter-spacing:-1.6px;color:#f2f5f7} h2,h3 {color:#b9e7ec}
[data-testid="stMetric"] {background:#121923;padding:18px;border:1px solid #263544;border-radius:12px}
[data-testid="stSidebar"] {background:#0d141d}
</style>''',unsafe_allow_html=True)
st.caption('QUANTUM FREQUENCY METROLOGY / RESEARCH PROTOTYPE 0.1')
st.title('Diamond Atomic Clock')
st.markdown('Explore how diamond spin transitions respond to their environment—and how compensation changes frequency stability.')
st.info('SIMULATION · Conditional results from assumed noise inputs. Published limits and theoretical projections are labeled separately. This is a frequency-reference model with residual oscillator noise, not a validated hardware clock.')

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

with st.sidebar:
    st.markdown('### Experiment controls')
    st.caption('All noise settings are assumptions; physical coefficients come from Lourette 2023.')
    with st.form('controls'):
        n=st.selectbox('Number of samples',[4096,8192,16384,32768,65536,131072],index=3)
        dt=st.selectbox('Sample interval (s)',[.1,.5,1.,2.,5.,10.],index=2)
        seed=st.number_input('Random seed',min_value=0,value=20261019,step=1)
        with st.expander('Temperature environment',expanded=True):
            temp=st.number_input('Temperature OU RMS (K)',0.,1.,.05,format='%.4f')
            corr=st.number_input('Temperature correlation time (s)',1.,100000.,300.)
            sine=st.number_input('Thermal cycle peak amplitude (K)',0.,1.,.1,format='%.4f')
            period=st.number_input('Thermal cycle period (s)',100.,1000000.,7200.)
            drift=st.number_input('Temperature drift (K/hour)',-.1,.1,.002,format='%.4f')
        with st.expander('Magnetic environment'):
            bias=st.slider('Axial bias (G)',10.,600.,475.)
            bx=st.number_input('Static transverse field (G)',-1.,1.,0.,format='%.4f')
            brms=st.number_input('Axial field OU RMS (mG)',0.,100.,1.,format='%.3f')
            bxrms=st.number_input('Transverse field OU RMS (mG)',0.,100.,.1,format='%.3f')
            bcorr=st.number_input('Field correlation time (s)',1.,100000.,100.)
        with st.expander('Readout and compensation'):
            er=st.number_input('Electronic readout σ per transition at 1 s (Hz)',0.,10000.,50.)
            nr=st.number_input('Nuclear readout σ per transition at 1 s (Hz)',0.,100.,.03,format='%.4f')
            rho=st.slider('Error correlation within each pair',-1.,1.,0.,.05)
            tr=st.number_input('External thermometer σ at 1 s (mK)',0.,1000.,1.)
            delay=st.number_input('Thermometer delay (s)',0.,1000.,0.)
            err=st.slider('Slope calibration error (%)',-20.,20.,1.,.25)
        with st.expander('Residual oscillator noise'):
            low=st.number_input('White FM ADEV at 1 s (×10⁻⁹)',0.,10000.,1.,format='%.3f')
            lorw=st.number_input('Random-walk diffusion (×10⁻¹¹ /√s)',0.,1000.,1.,format='%.3f')
            lodrift=st.number_input('Oscillator drift (×10⁻¹³ /s)',-100.,100.,0.,format='%.3f')
        st.form_submit_button('Run simulation',type='primary',width='stretch')
    c=Config(n=int(n),dt_s=dt,seed=int(seed),temp_rms_K=temp,temp_corr_s=corr,temp_sine_K=sine,
             temp_period_s=period,temp_drift_K_h=drift,Bz_G=bias,Bx_G=bx,Bz_rms_G=brms/1000,
             Bx_rms_G=bxrms/1000,B_corr_s=bcorr,electron_readout_Hz=er,nuclear_readout_Hz=nr,
             readout_rho=rho,thermometer_rms_K=tr/1000,thermometer_delay_s=delay,
             slope_error_pct=err,lo_white_adev_1s=low*1e-9,lo_rw_diffusion=lorw*1e-11,
             lo_drift_per_s=lodrift*1e-13)

try:
    with st.spinner('Solving the spin Hamiltonian and calculating overlapping Allan deviation…'):
        fingerprint=source_fingerprint()
        trace,a,diag,run_context=cached_run(asdict(c),fingerprint)
        validate(run_context)
except ValueError as exc:
    st.error(str(exc));st.stop()

grid=a[a.method=='composite']
target=grid.iloc[(grid.tau_s-200).abs().argmin()]
base=a[(a.method=='electron_average') & (a.tau_s==target.tau_s)].adev.iloc[0]
cols=st.columns(4)
cols[0].metric('Record duration',f'{c.n*c.dt_s/3600:.2f} h')
cols[1].metric(f'Composite ADEV at {target.tau_s:g} s',f'{target.adev:.2e}')
cols[2].metric('Electronic / composite ADEV',f'{base/target.adev:.2f}×' if target.adev>0 else 'undefined')
cols[3].metric('Composite nuclear weight',f'{diag["wQ"]:.4f}')
st.caption('Smaller Allan deviation means less change in the average ticking rate between neighboring averaging windows. A ratio below 1 means the composite is worse at the displayed averaging time.')

tabs=st.tabs(['Stability lab','Environment & transitions','Compensation study','NV center explained','Research Paper Bucket','Export & methodology','ODMR spectroscopy'])

with tabs[0]:
    st.subheader('Frequency stability across averaging time')
    show_published=st.checkbox('Show published measurement limits within this record',True)
    show_projections=st.checkbox('Show Hodges 2013 theoretical projections',False)
    selected=st.multiselect('Reference signals',list(METHODS),default=list(METHODS),format_func=METHODS.get)
    fig=go.Figure()
    for (key,label),color in zip(METHODS.items(),COLORS):
        if key in selected:
            part=a[a.method==key]
            fig.add_trace(go.Scatter(x=part.tau_s,y=part.adev,mode='lines+markers',name=label+' · simulation',line_color=color,
                                    customdata=part.overlapping_pairs,hovertemplate='τ=%{x:g} s<br>ADEV=%{y:.3e}<br>Overlapping pairs=%{customdata}<extra>%{fullData.name}</extra>'))
    if show_published:
        b=benchmarks();b=b[b.tau_s<=a.tau_s.max()]
        fig.add_trace(go.Scatter(x=b.tau_s,y=b.adev_limit,mode='markers',name='Lourette 2026 · measured upper limits (<)',
                                 marker=dict(symbol='triangle-down-open',size=14,color='black')))
    if show_projections:
        tau=np.geomspace(a.tau_s.min(),a.tau_s.max(),100)
        for level,title in [(1e-7,'Thermal projection'),(1e-12,'Ideal projection')]:
            fig.add_trace(go.Scatter(x=tau,y=level/np.sqrt(tau),name='Hodges 2013 · '+title,line=dict(dash='dot',color='#aaaaaa')))
    fig.update_layout(template='plotly_dark',height=560,xaxis_title='Averaging time τ (s)',yaxis_title='Overlapping Allan deviation σy(τ)',
                      xaxis_type='log',yaxis_type='log',legend=dict(orientation='h',y=-.2),margin=dict(t=20,b=120))
    st.plotly_chart(fig,width='stretch')
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
    st.plotly_chart(f,width='stretch')
    names=['Electronic f+','Electronic f−','Nuclear f1','Nuclear f2','Electronic half-sum Dobs','Signed nuclear half-sum Qobs']
    table=pd.DataFrame({'Observable':names,'Nominal frequency (Hz)':diag['nominal_Hz'],'Local slope (Hz/K)':diag['slope_Hz_K'],'Fractional slope (/K)':diag['lambda_per_K']})
    st.dataframe(table,hide_index=True,width='stretch')
    st.caption('Exact eigenvalues of the chosen ground-state Hamiltonian; temperature dependence uses a local quadratic approximation. Eigenstates are tracked by overlap. Transition strengths, optical pumping, and pulse sequences are not simulated.')

with tabs[2]:
    st.subheader('Can compensation survive readout noise?')
    st.latex(r'y_C=w_Dy_D+w_Qy_Q,\quad w_Q=\frac{\lambda_D}{\lambda_D-\lambda_Q},\quad w_D=1-w_Q')
    st.markdown('The weighted sum cancels the calibrated linear temperature response. It preserves a common fractional oscillator term because the weights add to one. Nuclear readout noise is amplified by its weight. [L2026, Eq. (5)]')
    st.write(f"Actual residual first-order temperature response: {diag['thermal_sensitivity_composite_per_K']:.3e} /K.")
    count=st.select_slider('Independent model realizations',[3,5,10,20,40],value=10)
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
        st.plotly_chart(ef,width='stretch')
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
    st.subheader('Research Paper Bucket')
    reference_store=None
    reference_error=None
    try:
        reference_store=ReferenceStore()
        paper_bucket=reference_store.catalog()
    except (OSError,sqlite3.Error,ValueError) as exc:
        reference_error=str(exc)
        paper_bucket=sources()
        st.error('Persistent references unavailable: '+reference_error)
    query=st.text_input('Search papers, equations, parameters, or implementation')
    with st.expander('Add a paper'):
        st.caption('Added papers are saved to this installation and exported as unverified references. A DOI does not verify a paper or map it to the scientific model.')
        with st.form('add_paper'):
            title=st.text_input('Title')
            authors=st.text_input('Authors')
            year=st.number_input('Publication year',min_value=1800,max_value=2100,value=2026,step=1)
            journal=st.text_input('Journal or publication')
            doi=st.text_input('DOI (optional)')
            url=st.text_input('Paper URL')
            note=st.text_area('Note (optional)')
            submitted=st.form_submit_button('Add paper',type='primary')
        if submitted:
            try:
                if reference_store is None:
                    raise ValueError('Persistent storage is unavailable. Reference was not saved.')
                reference_store.add(dict(title=title,authors=authors,year=year,journal=journal,
                                         doi=doi,url=url,note=note))
                paper_bucket=reference_store.catalog()
                st.session_state.pop('export',None)
                st.success(f'Added "{title.strip()}". Saved as unverified.')
            except (ValueError,OSError,sqlite3.Error) as exc:
                st.error(str(exc))
    paper_count=sum(source['id']!='MODEL' and source.get('record_type')!='implementation_archive' for source in paper_bucket)
    st.info(f'{paper_count} papers/research references and {len(paper_bucket)} total references are currently in the bucket.')
    catalog_data=catalog_bytes(paper_bucket)
    catalog_digest=hashlib.sha256(catalog_data).hexdigest()
    st.download_button('Download Paper Bucket JSON',catalog_data,'sources.json','application/json',
                       disabled=reference_error is not None)
    st.download_button('Download Paper Bucket BibTeX',bibtex_bytes(paper_bucket),
                       'references.bib','application/x-bibtex',disabled=reference_error is not None)
    visible_papers=sorted(paper_bucket,key=lambda source:(source['year'],source['title'].lower()))
    for source in visible_papers:
        if query and query.lower() not in json.dumps(source).lower():continue
        with st.expander(f"[{source['id']}] {source['title']} ({source['year']})"):
            st.write(source['authors']+' · '+source['journal'])
            st.write('Verification: '+verification_label(source))
            st.write('Evidence: '+source['evidence'])
            st.write('Location: '+source['locator'])
            st.code(source['implementation'],language=None)
            st.write(source['note'])
            if source.get('doi'):
                st.link_button('DOI: '+source['doi'],'https://doi.org/'+source['doi'])
            if source.get('url','').startswith(('https://','http://')):
                st.link_button('Source link',source['url'])
    st.markdown('#### Every active parameter')
    active_parameters=provenance(c)
    if query:
        active_parameters=active_parameters[active_parameters.astype(str).apply(lambda col:col.str.contains(query,case=False,regex=False)).any(axis=1)]
    st.dataframe(active_parameters,hide_index=True,width='stretch')
    st.markdown('#### Published measurement limits')
    st.dataframe(benchmarks(),hide_index=True,width='stretch')
    st.caption('These are reported upper bounds, not imported raw measurements. No published curve has been digitized. The 200000 s limit is not plotted unless the simulated record supports that averaging time.')
    st.markdown('#### Equation-to-code map')
    st.markdown((ROOT/'references/equation_map.md').read_text(encoding='utf-8'))

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


with tabs[6]:
    from diamondclock.odmr_dashboard import render_odmr
    render_odmr(c,fingerprint,paper_bucket,reference_error)
