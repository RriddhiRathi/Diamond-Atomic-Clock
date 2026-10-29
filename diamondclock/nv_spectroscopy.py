"""Recovered Part 3 adapter for the existing ODMR engine; no new physics."""
from dataclasses import asdict
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from .odmr import ODMRConfig, spectrum, transform, vector
from .physics import Physics, thermal_parameters
from .optical_parameters import OpticalConfig
from .run_provenance import capture, validate


@st.cache_data(show_spinner=False, max_entries=16)
def cached_spectrum(field, orientation, fingerprint):
    """Cache only physical configuration and source identity, never view controls."""
    field = vector(field)
    if isinstance(orientation, bool) or orientation not in range(4) or np.linalg.norm(field) > 50 + 1e-10:
        raise ValueError('Demonstration supports four NV orientations and B=0..50 G.')
    p = Physics()
    d = thermal_parameters(297., p)[0]
    # Same conservative GHz window as the existing ODMR dashboard. This defines
    # coverage only: resonance centers are calculated by spectrum(), not this bound.
    margin = p.gamma_e_Hz_G * np.linalg.norm(field) + 20e6
    weights = tuple(float(i == orientation) for i in range(4))
    c = ODMRConfig(B_lab_G=tuple(field),
        microwave_lab=tuple(transform((1, 0, 0), orientation, inverse=True)),
        weights=weights, start_Hz=d-margin, stop_Hz=d+margin, points=10001)
    context = capture(config=c, physics=p)
    data, lines, _ = spectrum(c, p)
    validate(context)
    return data, lines, asdict(c), context


def bounded_frequency(data, frequency_Hz):
    """Accept floating-point endpoint round trips, reject real extrapolation."""
    x = data.frequency_Hz.to_numpy()
    tolerance = 8 * np.spacing(max(abs(x[0]), abs(x[-1])))
    if not np.isfinite(frequency_Hz) or frequency_Hz < x[0]-tolerance or frequency_Hz > x[-1]+tolerance:
        raise ValueError('Frequency outside calculated spectrum')
    return float(np.clip(frequency_Hz, x[0], x[-1]))


def fluorescence(data, frequency_Hz):
    """Piecewise-linear interpolation; no fit, extrapolation or new line model."""
    frequency_Hz = bounded_frequency(data, frequency_Hz)
    return float(np.interp(frequency_Hz, data.frequency_Hz, data.combined_fluorescence))


def emission_signal(response, laser=True, microwave=True):
    # Laser-off dynamics are outside this proxy, not an inferred zero count rate.
    return None if not laser else float(response) if microwave else 1.


def optical_scope(field, orientation, states=7):
    """Domain check only; never invoke an optical solver or infer photon counts."""
    local = transform(field, orientation)
    if np.linalg.norm(local[:2]) > 1e-9:
        return False, 'Detailed optical readout unsupported for this off-axis field.'
    axial = float(local[2])
    # Orthogonal frame round trips can shift an exact UI boundary by a few ULPs.
    # Snap only numerical roundoff; do not extend the optical model's domain.
    for boundary in (5., 50.):
        if abs(axial-boundary) <= 8*np.spacing(boundary):
            axial = boundary
    try:
        OpticalConfig(states=states, Bz_G=axial, temperature_K=297.).validate()
    except ValueError:
        return False, 'Detailed optical readout requires positive local axial B=5–50 G at 297 K; zero/reversed fields are outside its validated domain.'
    return True, 'Field is within the separate optical model’s axial domain; its photon counts and contrast are not mapped to this ODMR proxy.'


def spectrum_figure(data, lines, config, orientation, frequency_Hz, *, laser=True,
                    microwave=True, other_orientations=False):
    frequency_Hz = bounded_frequency(data, frequency_Hz)
    response = fluorescence(data, frequency_Hz)
    signal = emission_signal(response, laser, microwave)
    fig = go.Figure()
    if other_orientations:
        for k in range(4):
            if k != orientation:
                fig.add_scatter(x=data.frequency_Hz/1e9, y=data[f'NV{k+1}_fluorescence'],
                    name=f'NV{k+1} · comparison', line=dict(width=1), opacity=.45)
    fig.add_scatter(x=data.frequency_Hz/1e9, y=data.combined_fluorescence,
        name=f'NV{orientation+1} · simulated MW-on proxy', line=dict(color='#30d5c8', width=2))
    fig.add_vline(x=frequency_Hz/1e9, line_color='#ffb454')
    if signal is not None:
        fig.add_scatter(x=[frequency_Hz/1e9], y=[signal], mode='markers',
            marker=dict(color='#ffb454', size=9),
            name='Selected proxy' if microwave else 'MW-off reference = 1')
    active = lines[(lines.orientation == orientation+1) & (lines.dip_weight > 1e-8)
                   & lines.frequency_Hz.between(config['start_Hz'], config['stop_Hz'])]
    fig.add_scatter(x=active.frequency_Hz/1e9,
        y=[float(data.combined_fluorescence.min())]*len(active), mode='markers',
        marker=dict(symbol='line-ns', color='#c7d8e8'),
        name='Calculated transition centers (may overlap)',
        hovertemplate='%{x:.9f} GHz<extra>Hamiltonian transition, not a fitted dip minimum</extra>')
    fig.update_layout(height=370, template='plotly_dark', xaxis_title='Microwave frequency (GHz)',
        yaxis_title='Normalized fluorescence proxy', margin=dict(t=10, b=30),
        legend=dict(orientation='h', font=dict(size=10)),
        meta=dict(model='odmr.spectrum', field_G=config['B_lab_G'], orientation=orientation,
                  frequency_Hz=frequency_Hz, interpolated_response=response, displayed_signal=signal))
    return fig


def render_spectrum(field, orientation):
    from .run_provenance import source_fingerprint
    import json
    fingerprint = source_fingerprint()
    data, lines, config, context = cached_spectrum(tuple(field), orientation, fingerprint)
    validate(context)
    st.session_state['nv_spectrum_config'] = config
    lo, hi = float(data.frequency_Hz.iloc[0]/1e9), float(data.frequency_Hz.iloc[-1]/1e9)
    key = 'nv_mw_frequency'
    default = float(data.loc[data.combined_fluorescence.idxmin(), 'frequency_Hz']/1e9)
    value = float(np.clip(st.session_state.get(key, default), lo, hi))
    if key not in st.session_state or st.session_state[key] != value:
        st.session_state[key] = value
    st.markdown('**Simulated ODMR · selected NV**')
    frequency = st.slider('Microwave frequency (GHz)', lo, hi, step=1e-7, format='%.7f', key=key)
    frequency_Hz = bounded_frequency(data, frequency*1e9)
    response = fluorescence(data, frequency_Hz)
    a, b = st.columns(2)
    laser = a.checkbox('Schematic laser enabled', True, key='nv_laser')
    microwave = b.checkbox('Schematic microwave enabled', True, key='nv_microwave')
    signal = emission_signal(response, laser, microwave)
    fig = spectrum_figure(data, lines, config, orientation, frequency_Hz,
        laser=laser, microwave=microwave,
        other_orientations=st.session_state.get('nv_other_spectra', False))
    st.plotly_chart(fig, width='stretch', key='nv_odmr_plot')
    st.metric('Normalized fluorescence', 'Not modeled · laser off' if signal is None else f'{signal:.6f}')
    if signal is not None:
        st.caption(f'Relative decrease from the model MW-off reference: {100*(1-signal):.3f}%')
    st.caption('MW-on curve is a conditional model prediction; MW-off reference = 1. '
               'Fluorescence indication uses linear grid interpolation, not photon counts. '
               'An ODMR dip does not establish clock lock.')
    with st.expander('Model parameters, optical domain and provenance'):
        supported, note = optical_scope(field, orientation)
        st.info(note)
        st.write('Seven/21-state Lindblad/rate calculations remain separate in Advanced Research → Optical measurement. '
                 'No automatic detailed readout is performed, even within the supported domain. '
                 'Laser-off emission is undefined here; no zero photon rate is claimed.')
        st.caption('Existing nine-state ground Hamiltonian and Lorentzian transition-strength proxy '
                   '[L2023, D2012, DRE2011]. Fixed 297 K, E=0; assumed 0.3 MHz FWHM and 0.03 contrast budget. '
                   'Polarization is the selected NV local +x, not calibrated microwave power. '
                   'Overlapping transition centers need not coincide with dip minima.')
        st.json(config)
        record = dict(model='odmr.spectrum / selected-NV proxy', config=config,
            selected_frequency_Hz=frequency_Hz, interpolated_fluorescence=response,
            laser_enabled=laser, microwave_enabled=microwave, displayed_signal=signal,
            optical_domain_supported=supported, optical_coupling='Not implemented; use separate optical workspace',
            source_fingerprint=fingerprint, source_sha256=context['source_sha256'], git=context['git'])
        st.download_button('Download demonstration parameters', json.dumps(record, indent=2),
            'NV_ODMR_demonstration_SIMULATION.json', 'application/json', key='download_nv_parameters')
    return laser, microwave, signal
