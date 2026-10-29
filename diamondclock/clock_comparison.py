"""One contextual comparison of existing archived NV data and cited guide values.

No model is calculated, fitted or extrapolated. Guide stability estimates retain
reported qualifiers and are not silently certified as identical ADEV estimators.
"""
import hashlib
import json
import zipfile

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .clock_presentation import read_archive
from .clock_results import matched_allan, valid_allan, ratio_outcome, interpret
from .plot_style import scientific_plot, CHART_CONFIG
from .resources import project_root


def comparison_data():
    return json.loads((project_root()/'references/clock_comparison.json').read_text(encoding='utf-8'))


def saved_nv(data, root=None):
    """Read only the named, checksum-pinned original bundle; never calculate a fallback."""
    entry=data['nv_example']
    raw=((root or project_root())/entry['bundle']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=entry['bundle_sha256']:
        raise ValueError('Saved NV example differs from the reviewed comparison bundle.')
    values,result,_,_=read_archive(raw)
    if matched_allan(result['tables']['allan']).empty:
        raise ValueError('Saved NV example has no comparable positive full-record Allan data.')
    return values,result


def table_rows(data, nv=None):
    rows=[]
    if nv is not None:
        config,result=nv
        point=matched_allan(result['tables']['allan']).iloc[-1]
        note=(f"Feedback {ratio_outcome(point.ratio)} at this τ (R={point.ratio:.3g}); "
              +interpret(result)['stability']+'.')
        nvrow={'Clock type':'DiamondClock Lab · SIMULATION',
               'Platform / transition':f"NV− electronic-spin reference; nominal {result['summary']['nominal_Hz']/1e9:.6f} GHz",
               'Metric / evidence':'Overlapping Allan deviation · saved simulation, full record',
               'Fractional instability (1)':f"Feedback {point.feedback_adev:.6g}; free {point.free_adev:.6g}",
               'Averaging time τ (s)':f'{point.tau_s:g}',
               'Configuration / context':note,'Source / locator':'MODEL · DC7 verified archive'}
    else:
        nvrow={'Clock type':'DiamondClock Lab · SIMULATION','Platform / transition':'NV− electronic-spin reference',
               'Metric / evidence':'Saved example unavailable; no simulation run',
               'Fractional instability (1)':'Unavailable','Averaging time τ (s)':'Unavailable',
               'Configuration / context':'DC7 requires the original research bundle in the Git checkout',
               'Source / locator':'MODEL · DC7 archive'}
    rows.append(nvrow)
    for row in data['literature_points']:
        sign='<' if row['relation']=='less_than' else '≈'
        rows.append({'Clock type':row['clock_type']+' · LITERATURE',
                     'Platform / transition':row['platform'],'Metric / evidence':row['metric'],
                     'Fractional instability (1)':f"{sign} {row['value']:.3g}",
                     'Averaging time τ (s)':f"{row['tau_s']:g}",
                     'Configuration / context':row['note'],
                     'Source / locator':row['source_id']+' · '+row['locator']})
    return pd.DataFrame(rows)


def comparison_figure(data, nv=None):
    fig=go.Figure()
    if nv is not None:
        _,result=nv
        allan=valid_allan(result['tables']['allan'])
        for name,label,dash,symbol,color in (
            ('locked','NV feedback · SIMULATION','solid','diamond','#38d2bd'),
            ('unlocked','NV free running · SIMULATION','dash','circle','#b8c4d4')):
            points=allan[allan.method==name]
            fig.add_scatter(x=points.tau_s,y=points.adev,mode='lines+markers',name=label,
                line=dict(color=color,dash=dash,width=2),marker=dict(size=5,symbol=symbol),
                hovertemplate='DC7 · MODEL · full-record simulation<br>τ=%{x:g} s<br>Overlapping ADEV=%{y:.6e}<extra>%{fullData.name}</extra>')
    for row,color,symbol in zip(data['literature_points'],('#94baff','#f5bb65','#c5a0ff'),('square-open','cross','triangle-down-open')):
        qualifier='<' if row['relation']=='less_than' else '≈'
        fig.add_scatter(x=[row['tau_s']],y=[row['value']],mode='markers',
            name=row['clock_type']+(' · upper bound' if row['relation']=='less_than' else ' · typical'),
            marker=dict(color=color,size=11,symbol=symbol,line_width=2),
            customdata=[[row['source_id'],row['locator'],row['url'],row['metric']]],
            hovertemplate=(f"LITERATURE context · {qualifier} %{{y:.3e}} at τ=%{{x:g}} s<br>"
                           '%{customdata[0]} · %{customdata[1]}<br>%{customdata[3]}<br>%{customdata[2]}<extra>%{fullData.name}</extra>'))
    fig.update_layout(xaxis_type='log',yaxis_type='log',
        xaxis_title='Averaging time τ (s)',yaxis_title='Fractional frequency instability (dimensionless)',
        meta=dict(comparison='Literature/context; not experimental NV validation',
                  literature_geometry='isolated reference points; no interpolation or extrapolation'))
    return scientific_plot(fig,height=460)


def open_paper_bucket():
    st.session_state['dashboard_section']='Paper Bucket'
    st.session_state['research_equation_map']='Atomic clock comparison'


def render_comparison():
    st.title('Atomic Clock Comparison')
    st.caption('LITERATURE / CONTEXT COMPARISON · not a direct experimental validation of the simulated NV-center clock')
    data=comparison_data()
    try:
        nv=saved_nv(data)
    except (OSError,ValueError,KeyError,zipfile.BadZipFile) as exc:
        nv=None
        st.warning('NV archive unavailable or invalid; literature context remains available. '+str(exc))
    st.dataframe(table_rows(data,nv),hide_index=True,width='stretch',row_height=95)
    if nv is not None:
        config,result=nv
        o=config['optical']
        st.caption(f"DC7 saved drift-stress simulation: {o['states']}-state {config['plant_backend']}; {o['Bz_G']:g} G, "
                   f"{o['temperature_K']:g} K; {config['detector']['centers']} centers; gate {1e3*config['gate_s']:g} ms; "
                   f"{config['cycles']} cycles; seed {config['seed']}; full record {result['summary']['record_s']:g} s; "
                   f"assumed free-oscillator drift {config['oscillator']['drift_Hz_s']:g} Hz/s (not typical hardware).")
    st.plotly_chart(comparison_figure(data,nv),width='stretch',config=CHART_CONFIG)
    st.caption('Lines connect recorded NV simulation samples only. Literature symbols are isolated rounded guide values at 1 s; the downward open triangle is a “less than” bound, not an exact measurement.')
    st.markdown('**Interpretation & limits.** This locates one simulated NV reference in a broader stability landscape. '
                'Hardware, environments, bandwidths and measurement protocols differ. NIST’s glossary gives '
                'representative conventional-clock stability, without per-device estimator/confidence details; '
                'these are not precision matched-ADEV experiments. The finite NV result follows this project’s '
                'optical, photon-noise and oscillator/controller assumptions. No apples-to-apples ranking, '
                'experimental NV validation or absolute-accuracy claim follows.')
    st.caption('Source: [NIST_ATOZ — NIST glossary](https://tf.nist.gov/general/pdf/1548.pdf), '
               'printed pp. 8, 25 and 41. NV: MODEL / DC7, original seven-state bundle. '
               'Detailed value-to-source mappings and original verification labels are available in Paper Bucket.')
    st.button('View comparison sources in Paper Bucket',key='comparison_sources',on_click=open_paper_bucket)
