"""Scientific clock results views. Reads completed data; never starts a simulation."""
from io import BytesIO
import hashlib
import json
import zipfile

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from .clock_results import (WINDOWS, validate_saved, valid_allan, matched_allan,
                            overview_metrics, interpret, ratio_outcome)
from .resources import project_root
from .run_provenance import verify_files
from .plot_style import scientific_plot, CHART_CONFIG

ARCHIVE = 'Verified historical example'
SESSION = 'Current session run'
CASES = {'Seven-state Lindblad · drift stress test': '7',
         '21-state rate · 1000 centers': '21',
         'Lock with worse stability · quieter oscillator': 'low_drift',
         'Failed lock · excessive gain': 'high_gain',
         'Failed lock · long latency': 'latency',
         'Failed lock · insufficient photons': 'photon_starved'}
COLORS = {'unlocked': '#b8c4d4', 'locked': '#38d2bd'}
NAMES = {'unlocked': 'Free running', 'locked': 'Feedback enabled'}


def completed_clock():
    saved = st.session_state.get('clock_result')
    if saved is None:
        return None
    try:
        validate_saved(saved)
    except ValueError as exc:
        st.warning(str(exc))
        return None
    return saved


def number(value, scale=1., spec='.3g'):
    return format(value * scale, spec) if value is not None and np.isfinite(value) else 'Unavailable'


def render_summary(values, result, origin='CURRENT SESSION'):
    metrics = overview_metrics(values, result)
    summary = result['summary']
    comparison = metrics['comparison']
    tau = f"τ={comparison['tau_s']:g} s" if comparison else 'no matched τ'
    st.caption(f'CLOCK PERFORMANCE SUMMARY · {origin} · SIMULATION')
    row = st.columns(3)
    fraction = metrics['lock_fraction']
    row[0].metric('Observed lock fraction', number(fraction, 100, '.1f') + '%' if fraction is not None else 'Unavailable')
    row[1].metric('Public nominal reference (GHz)', number(metrics['nominal_Hz'], 1e-9, '.9f'))
    row[2].metric('Final feedback time error (µs)', number(metrics['final_time_errors_s'].get('locked'), 1e6, '.3f'))
    row = st.columns(3)
    row[0].metric(f'Feedback Allan deviation · {tau}', number(comparison['feedback_adev']) if comparison else 'Unavailable')
    row[1].metric(f'Free-running Allan deviation · {tau}', number(comparison['free_adev']) if comparison else 'Unavailable')
    row[2].metric(f'Feedback / free ADEV · {tau}', number(comparison['ratio']) if comparison else 'Unavailable')
    st.caption(f"{values['optical']['states']} states · {values['optical']['Bz_G']:g} G axial · "
               f"{values['optical']['temperature_K']:g} K · {values['plant_backend']} · "
               f"{values['cycles']} requested / {summary.get('completed_cycles', 'unavailable')} completed cycles · "
               f"gate {1e3*values['gate_s']:g} ms · seed {values['seed']} · "
               f"record {number(metrics['record_s'])} s. Final free-running time error: "
               f"{number(metrics['final_time_errors_s'].get('unlocked'),1e6,'.3f')} µs.")
    st.caption('Allan deviation is dimensionless fractional-frequency instability. Cards use the longest '
               'valid matched full-record τ; the conclusion considers every matched τ. '
               'Positive time error means the clock leads the nominal reference.')
    conclusion=metrics['interpretation']
    st.markdown(f"**{conclusion['lock']}.** {conclusion['stability'].capitalize()}.")
    with st.expander('Interpretation details'):
        st.write(conclusion['text'])


def acquisition_figure(result, index=0):
    tables = result['tables']
    fits, counts = tables['acquisition'], tables['photon_observations']
    fig = go.Figure()
    if fits.empty or counts.empty:
        return fig
    fit = fits.iloc[index]
    data = counts[(counts.stage == 'acquisition') & (counts.cycle == fit.cycle)]
    for enabled, label in ((True, 'Simulated detected counts · MW on'),
                           (False, 'Simulated detected counts · MW off reference')):
        part = data[data.microwave_on == enabled]
        fig.add_scatter(x=part.probe_offset_Hz / 1e6, y=part.detected_counts,
                        mode='markers', name=label,
                        customdata=part.nominal_gate_s,
                        hovertemplate='%{x:.6f} MHz<br>%{y} counts<br>Gate %{customdata:g} s<extra>%{fullData.name}</extra>')
    if bool(fit.valid) and np.isfinite(fit.centre_command_Hz):
        fig.add_vline(x=fit.centre_command_Hz / 1e6, line_color='#16a6a1')
        if np.isfinite([fit.lower_Hz, fit.upper_Hz]).all():
            fig.add_vrect(x0=fit.lower_Hz / 1e6, x1=fit.upper_Hz / 1e6,
                          fillcolor='#16a6a1', opacity=.15, line_width=0)
    fig.update_layout(title=f'SIMULATION · photon-only acquisition · attempt {int(fit.attempt)}',
                      xaxis_title='Commanded probe offset from controlled carrier (MHz)',
                      yaxis_title='Detected photons per programmed gate (counts)',
                      legend=dict(orientation='h', y=-.25), margin=dict(t=55,b=100))
    return scientific_plot(fig,height=420)


def frequency_figure(result):
    out = result['tables']['clock_output']
    fig = go.Figure()
    for name in ('unlocked', 'locked'):
        fig.add_scatter(x=out.time_s, y=out[name+'_deviation_Hz']/1e3,
                        name=NAMES[name], line=dict(color=COLORS[name], width=1.7,dash='dash' if name=='unlocked' else 'solid'))
    fig.add_hline(y=0, line_dash='dot', annotation_text='Public nominal frequency')
    fig.update_layout(title='SIMULATION · actual oscillator output; probe dither excluded',
                      xaxis_title='True simulation time (s)',
                      yaxis_title='Frequency minus public nominal (kHz)')
    return scientific_plot(fig,height=400)


def tracking_figure(result, show_uncertainty=False):
    fb = result['tables']['feedback']
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=.14)
    if {'measurement_midpoint_local_s', 'detuning_Hz', 'sigma_Hz', 'valid'}.issubset(fb):
        good = fb.valid & np.isfinite(fb.sigma_Hz) & np.isfinite(fb.detuning_Hz)
        fig.add_scatter(x=fb.measurement_midpoint_local_s, y=fb.detuning_Hz.where(good)/1e3,
                        error_y=dict(type='data', array=fb.sigma_Hz.where(good)/1e3, visible=show_uncertainty,thickness=.6,width=1),
                        name='Accepted count-derived estimate (1σ in hover)', customdata=fb.sigma_Hz.where(good)/1e3, hovertemplate='%{x:.4f} s<br>%{y:.3f} kHz<br>Reported 1σ: %{customdata:.3f} kHz<extra>Count-derived estimate</extra>', connectgaps=False, row=1,col=1)
    if {'local_end_s', 'locked'}.issubset(fb):
        fig.add_scatter(x=fb.local_end_s, y=fb.locked.astype(int),
                        mode='lines', line_shape='hv', name='Observed lock flag', row=2,col=1)
    fig.update_yaxes(title_text='Estimated detuning (kHz)', row=1,col=1)
    fig.update_yaxes(title_text='Lock flag (0/1)', tickvals=[0,1], row=2,col=1)
    fig.update_xaxes(title_text='Local-clock time (s)', row=2,col=1)
    fig.update_layout(title='SIMULATION · photon estimator and observed lock detector',height=480)
    return scientific_plot(fig,height=500)


def phase_figure(result):
    # N+1 boundaries include the actual endpoint; interval-start values omit it.
    data = result['tables']['clock_phase_boundaries']
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=.13)
    for name in ('unlocked', 'locked'):
        for row, suffix, scale in ((1, 'phase_error_rad', 1.), (2, 'time_error_s', 1e6)):
            fig.add_scatter(x=data.time_s, y=data[name+'_'+suffix]*scale,
                            name=NAMES[name], legendgroup=name, showlegend=row==1,
                            line=dict(color=COLORS[name],width=1.7,dash='dash' if name=='unlocked' else 'solid'), row=row,col=1)
    fig.update_yaxes(title_text='Phase deviation (rad)',row=1,col=1)
    fig.update_yaxes(title_text='Time error (µs)',row=2,col=1)
    fig.update_xaxes(title_text='True simulation time (s)',row=2,col=1)
    fig.update_layout(title='SIMULATION · continuous phase and accumulated time error',height=500)
    return scientific_plot(fig,height=510)


def allan_figure(result, window='allan'):
    data = valid_allan(result['tables'].get(window))
    fig = go.Figure()
    label = 'full record' if window == 'allan' else 'predeclared fixed window'
    for name in ('unlocked', 'locked'):
        part = data[data.method == name]
        fig.add_scatter(x=part.tau_s, y=part.adev, mode='lines+markers',
                        name=f'{NAMES[name]} · {label}', line=dict(color=COLORS[name],width=2,dash='dash' if name=='unlocked' else 'solid'),marker=dict(size=6,symbol='circle' if name=='unlocked' else 'diamond'))
    fig.update_layout(title=f'SIMULATION · overlapping Allan deviation · {label}',
                      xaxis_type='log',yaxis_type='log',xaxis_title='Averaging time τ (s)',
                      yaxis_title='Overlapping Allan deviation σᵧ(τ) (dimensionless)')
    return scientific_plot(fig,height=450)


def render_evidence(values, result):
    st.subheader('1 · Resonance acquisition')
    fits = result['tables']['acquisition']
    if fits.empty:
        st.info('No acquisition observations are available for this run.')
    else:
        if st.session_state.get('clock_acquisition_view',0) not in range(len(fits)):
            st.session_state['clock_acquisition_view'] = 0
        index = st.selectbox('Acquisition attempt', list(range(len(fits))),
                             format_func=lambda i:f"Attempt {int(fits.iloc[i].attempt)} · cycle {int(fits.iloc[i].cycle)}",
                             key='clock_acquisition_view') if len(fits)>1 else 0
        fit = fits.iloc[index]
        st.plotly_chart(acquisition_figure(result,index),width='stretch',config=CHART_CONFIG)
        if bool(fit.valid):
            st.caption(f"Count-fitted centre: {fit.centre_command_Hz/1e3:.3f} kHz relative to the controlled carrier; "
                       f"reported σ: {fit.centre_sigma_Hz/1e3:.3f} kHz; nominal 95% profile interval "
                       f"[{fit.lower_Hz/1e3:.3f}, {fit.upper_Hz/1e3:.3f}] kHz. Not an absolute SI frequency measurement.")
        else:
            st.warning('Acquisition rejected: '+str(fit.reason))
    st.caption('Photons and programmed commands/times determine this fit. The local oscillator moves during '
               'the scan; a static spectral minimum is not hidden truth supplied to the estimator.')
    with st.expander('Public reference and offline validation truth'):
        s = result['summary']
        st.write(f"Public nominal reference: {number(s.get('nominal_Hz'),1,'.3f')} Hz. "
                 f"Hamiltonian target: {number(s.get('evaluation_hamiltonian_reference_Hz'),1,'.3f')} Hz "
                 '(offline validation only; not supplied to the controller).')
        st.caption('The nominal reference and target are absolute simulated frequencies; the acquisition centre '
                   'above uses commanded-probe offsets. They cannot be overlaid as the same coordinate.')
    st.subheader('2 · Closed-loop frequency correction')
    st.plotly_chart(frequency_figure(result),width='stretch',config=CHART_CONFIG)
    uncertainty=st.checkbox('Show tracking uncertainty bars (reported 1σ)',key='clock_show_uncertainty')
    st.plotly_chart(tracking_figure(result,uncertainty),width='stretch',config=CHART_CONFIG)
    st.caption('Paired branches share the same free oscillator. Hover for reported 1σ; rejected cycles remain gaps. '
               'Output uses true simulation time; estimates and observed lock flags use local-clock timestamps. '
               '“Feedback enabled” is not certification of lock.')
    st.subheader('3 · Phase and accumulated time error')
    st.plotly_chart(phase_figure(result),width='stretch',config=CHART_CONFIG)
    st.caption('Integrated frequency deviation relative to the public nominal reference; positive time error means '
               'the clock leads. Endpoints include acquisition, latency and failures. Probe dither is excluded.')
    st.subheader('4 · Allan deviation')
    window_label = st.radio('Analysis window',list(WINDOWS),key='clock_analysis_window',horizontal=True)
    window = WINDOWS[window_label]
    if window == 'allan_fixed_window':
        st.caption(f"Secondary contiguous window: true simulation t ≥ {values['fixed_analysis_start_s']:g} s, declared "
                   'before the run. No selection using observed lock or hidden truth.')
    else:
        st.caption('Primary comparison: full record, retaining acquisition, drift and failures.')
    data = valid_allan(result['tables'].get(window))
    if data.empty:
        st.info('Insufficient valid positive Allan data in this window. No stability ratio is available.')
    else:
        st.plotly_chart(allan_figure(result,window),width='stretch',config=CHART_CONFIG)
        st.markdown(interpret(result,window)['text'])
    paired = matched_allan(result['tables'].get(window))
    if len(paired):
        options = paired.tau_s.tolist()
        if st.session_state.get('clock_comparison_tau') not in options:
            st.session_state['clock_comparison_tau'] = options[-1]
        tau = st.selectbox('Compare at matched τ (s)',options,key='clock_comparison_tau',format_func=lambda v:f'{v:g}')
        point = paired.loc[paired.tau_s == tau].iloc[0]
        st.write(f"At τ={tau:g} s: feedback σᵧ={point.feedback_adev:.6g}, free σᵧ={point.free_adev:.6g}; "
                 f"R(τ)=feedback/free={point.ratio:.6g} — {ratio_outcome(point.ratio)} simulated frequency stability.")
        with st.expander('All matched averaging times and ratios'):
            st.dataframe(paired.rename(columns={'tau_s':'τ (s)','feedback_adev':'Feedback σᵧ (1)',
                                                'free_adev':'Free σᵧ (1)','ratio':'Feedback / free (1)'}),hide_index=True)
    elif not data.empty:
        st.info('The available curves have no valid matching τ; no ratio or stability comparison is inferred.')
    st.caption('Only positive finite, unambiguous samples are plotted. Comparisons use exact matched τ within '
               'the same window, without interpolation or extrapolation. Drift remains. Zero/invalid values '
               'cannot support a positive stability ratio. Pair counts are not confidence intervals.')
    st.subheader('5 · Time-error summary & limitations')
    errors = result['summary'].get('final_time_errors_s',{})
    st.write(f"Final accumulated time error over the full record: feedback {number(errors.get('locked'),1e6,'.3f')} µs; "
             f"free running {number(errors.get('unlocked'),1e6,'.3f')} µs. These offsets and Allan deviation answer different questions.")
    with st.expander('Model assumptions & scientific limitations'):
        st.caption('Photon noise can enter through the sampled controller and worsen stability or produce servo '
                   'peaking. This finite conditional simulation assumes optical rates, oscillator noise/drift, '
                   'detector response and an ideal queued actuator. Laser/field/temperature drift, apparatus '
                   'systematics and SI calibration are not validated. Long records use approximate Poisson counts; '
                   'the 21-state rate backend is an approximation benchmarked against Lindblad. The independent '
                   '3D ODMR slider neither controls this run nor establishes lock. No experimental performance is claimed.')


@st.cache_data(show_spinner=False,max_entries=6)
def read_archive(data):
    """Existing verified export format, read-only; never turn old context into a live run."""
    with zipfile.ZipFile(BytesIO(data)) as archive:
        files = {name:archive.read(name) for name in archive.namelist()}
    verify_files(files)
    metadata = json.loads(files['metadata.json'])
    summary = json.loads(files['summary.json'])
    if metadata['data_kind'] != 'SIMULATION' or summary['experimental_validation'] is not False:
        raise ValueError('Archive is not an identified simulated run.')
    tables = {}
    for key in ('acquisition','photon_observations','feedback','clock_output','clock_phase_boundaries',
                'allan','allan_fixed_window','actuation'):
        content = files[key+'_SIMULATION.csv']
        if hashlib.sha256(content).hexdigest() != metadata['numerical_sha256'][key]:
            raise ValueError('Archived numerical table checksum mismatch: '+key)
        tables[key] = pd.read_csv(BytesIO(content))
    values = json.loads(files['config.json'])
    if metadata['provenance']['config'] != values:
        raise ValueError('Archived configuration differs from captured configuration.')
    return values, dict(tables=tables,summary=summary), metadata, files


def render_archived():
    name = st.selectbox('Stored simulation example',list(CASES),key='clock_archive_case')
    path = project_root()/'outputs/clock_phase4_20261024'/CASES[name]/'complete_research_bundle.zip'
    if not path.is_file():
        st.info('Historical output bundles are available in the Git checkout, not installed wheels. '
                'Open outputs/clock_phase4_20261024 in the repository to inspect these experiments.')
        return
    data = path.read_bytes()
    try:
        values, result, metadata, files = read_archive(data)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        st.error('Archived result could not be verified: '+str(exc))
        return
    st.caption('VERIFIED HISTORICAL SIMULATION · original source snapshot and configuration · not a new current-source run')
    render_summary(values,result,'HISTORICAL ARCHIVE')
    render_evidence(values,result)
    st.subheader('Original research outputs')
    st.download_button('Download original verified research bundle',data,
                       f'DiamondClock_{CASES[name]}_HISTORICAL_SIMULATION.zip','application/zip')
    # Offer exact archived vector bytes, without regenerating any historical figure.
    render_vector_downloads(files)
    with st.expander('Archived configuration and provenance'):
        st.json(values)
        st.json(metadata)
        st.download_button('Download original configuration',files['config.json'],'config.json','application/json')
        st.download_button('Download original metadata',files['metadata.json'],'metadata.json','application/json')
    st.caption('The complete ZIP contains all CSVs, configuration, references, MATLAB attribution, original source '
               'snapshot and SHA256SUMS.txt. It is not passed to the current-source exporter or substituted '
               'for a session result. Reproduction commands: docs/CLOCK_PERFORMANCE.md.')


def render_vector_downloads(files):
    with st.expander('Publication figures · original SVG / PDF'):
        for stem, label in (('clock_acquisition','Photon acquisition'),('clock_frequency_feedback','Oscillator correction'),
                            ('clock_phase_time','Phase and time error'),('clock_stability','Allan deviation')):
            a,b = st.columns(2)
            for column,fmt,mime in ((a,'svg','image/svg+xml'),(b,'pdf','application/pdf')):
                name = stem+'_SIMULATION.'+fmt
                column.download_button(f'{label} · {fmt.upper()}',files[name],name,mime)


def render_workspace():
    view = st.radio('Results source',[SESSION,ARCHIVE],key='clock_view',horizontal=True)
    if view == ARCHIVE:
        render_archived()
        return None
    saved = completed_clock()
    if saved is None:
        st.info('No completed clock run is available. Open the configuration and select '
                '“Simulate photon-based clock”, or choose a verified historical example above. A simulation runs only when submitted.')
        return None
    render_summary(saved[0][0],saved[1])
    render_evidence(saved[0][0],saved[1])
    return saved
