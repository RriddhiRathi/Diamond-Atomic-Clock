"""Traceable export bundles and Matplotlib vector figures (no Kaleido needed)."""
import hashlib
import io
import json
import platform
import zipfile
from pathlib import Path
from dataclasses import asdict
from importlib.metadata import version, PackageNotFoundError
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from . import __version__
from .physics import Physics, parameter_rows
from .simulation import Config, METHODS
from .reference_store import curated_sources, catalog_bytes, bibtex_bytes
from .run_provenance import capture, validate

ROOT=Path(__file__).resolve().parent.parent
COLORS=['#7c8598','#149ca8','#ed9d38','#aa6bd3','#2470dd']


def sources():
    return curated_sources()


def provenance(c=Config(),p=Physics()):
    lookup={s['id']:s for s in sources()}
    rows=[]
    for obj,location in [(p,'diamondclock/physics.py:Physics'),(c,'diamondclock/simulation.py:Config')]:
        for row in parameter_rows(obj):
            row['implementation']=location+'.'+row['parameter']
            row['doi']=lookup[row['source']]['doi']
            rows.append(row)
    return pd.DataFrame(rows)


def benchmarks():
    return pd.read_csv(ROOT/'references/benchmarks.csv')


def stability_figure(a, quantiles=None, projection=False, published=True,run_label=''):
    """M7: vector plot of simulated curves; published limits use downward markers."""
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none',
                         'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False}):
        fig,ax=plt.subplots(figsize=(8.2,5.9),layout='constrained')
        for (key,label),color in zip(METHODS.items(),COLORS):
            part=a[a.method==key]
            # Log axes cannot show a mathematically zero instability.
            valid=part.adev>0
            ax.loglog(part.tau_s[valid],part.adev[valid],color=color,lw=1.6,label=label.replace('–','-')+' (sim.)')
            if quantiles is not None:
                q=quantiles[quantiles.method==key]
                ax.fill_between(q.tau_s,q.p05,q.p95,color=color,alpha=.12,lw=0)
        if published:
            b=benchmarks()
            within=b[b.tau_s<=a.tau_s.max()]
            if len(within):
                ax.scatter(within.tau_s,within.adev_limit,marker='v',facecolors='none',edgecolors='black',s=55,
                           label='Published upper limit: Lourette 2026')
        if projection:
            tau=np.geomspace(a.tau_s.min(),a.tau_s.max(),100)
            ax.loglog(tau,1e-7/np.sqrt(tau),':',color='#a5a5a5',label='Hodges 2013 thermal projection')
            ax.loglog(tau,1e-12/np.sqrt(tau),'--',color='#c0c0c0',label='Hodges 2013 ideal projection')
        ax.set(xlabel=r'Averaging time $\tau$ (s)',ylabel=r'Overlapping Allan deviation $\sigma_y(\tau)$',
               title='Diamond Atomic Clock | Conditional simulation')
        ax.grid(True,which='both',alpha=.16)
        ax.legend(fontsize=8,loc='best')
        fig.get_layout_engine().set(rect=(0,.11,1,.89))
        foot='SIMULATED DATA | No experimental fit | Drift retained | Maximum averaging time = record / 10'
        if quantiles is not None:
            foot+='\nShading: 5th-95th model ensemble quantiles; not measurement confidence intervals'
        if run_label:
            foot+='\n'+run_label
        fig.text(.5,.025,foot,ha='center',va='bottom',fontsize=7,color='#444444')
        return fig


def figure_bytes(fig,fmt='svg'):
    b=io.BytesIO()
    fig.savefig(b,format=fmt,metadata={'Creator':'Diamond Atomic Clock conditional simulation'})
    return b.getvalue()


def environment():
    pkgs={}
    for name in ['numpy','scipy','pandas','matplotlib','plotly','streamlit','allantools','pytest']:
        try:pkgs[name]=version(name)
        except PackageNotFoundError:pass
    return dict(python=platform.python_version(),platform=platform.platform(),packages=pkgs)


def run_metadata(c,p,diagnostics,run_provenance=None):
    context=run_provenance or capture(stage='export_only')
    validate(context)
    if context.get('config') is not None and context['config']!=asdict(c):
        raise ValueError('Run provenance configuration does not match this result.')
    if context.get('physics') is not None and context['physics']!=asdict(p):
        raise ValueError('Run provenance physics does not match this result.')
    inputs=context['source_sha256']
    return dict(project='Diamond Atomic Clock',version=__version__,data_kind='SIMULATION',config=asdict(c),
                physics=asdict(p),diagnostics=diagnostics,environment=environment(),source_sha256=inputs,
                run_provenance={k:v for k,v in context.items() if k!='files'},
                computation_source_verified=context['capture_stage']=='before_calculation' and context.get('config')==asdict(c) and context.get('physics')==asdict(p),
                estimator='overlapping Allan deviation, no drift removal; tau <= N*dt/10',
                sample_convention='Effective contiguous rectangular interval averages; environmental Hamiltonian evaluated at one representative value per interval',
                scope='Conditional frequency-reference simulation with additive residual LO; no servo, Dick effect, or experimental apparatus fitted',
                uncertainty='Any ensemble band represents only the assumed stochastic processes; parameter uncertainty not propagated')


def export_files(trace,a,c,diagnostics,p=Physics(),quantiles=None,ensemble_raw=None,
                 run_provenance=None,references=None):
    context=run_provenance or capture(stage='export_only')
    meta=run_metadata(c,p,diagnostics,context)
    catalog=sources() if references is None else references
    paper_bytes=catalog_bytes(catalog)
    meta['reference_catalog_sha256']=hashlib.sha256(paper_bytes).hexdigest()
    meta['reference_catalog_scope']='Includes unverified user entries; these do not change equation or parameter mappings.'
    fig=stability_figure(a,quantiles,run_label=f'N={c.n:,}; dt={c.dt_s:g} s; seed={c.seed}; bias={c.Bz_G:g} G; full assumptions in config.json')
    files={
        'timeseries_SIMULATION.csv':trace.to_csv(index=False).encode(),
        'allan_SIMULATION.csv':a.to_csv(index=False).encode(),
        'config.json':json.dumps(asdict(c),indent=2).encode(),
        'metadata.json':json.dumps(meta,indent=2).encode(),
        'parameter_provenance.csv':provenance(c,p).to_csv(index=False).encode(),
        'stability_SIMULATION.svg':figure_bytes(fig,'svg'),
        'stability_SIMULATION.pdf':figure_bytes(fig,'pdf'),
        'sources.json':paper_bytes,
        'equation_map.md':(ROOT/'references/equation_map.md').read_bytes(),
        'references.bib':bibtex_bytes(catalog),
        'published_benchmark_limits.csv':(ROOT/'references/benchmarks.csv').read_bytes(),
        'METHODOLOGY.md':(ROOT/'docs/METHODOLOGY.md').read_bytes(),
    }
    plt.close(fig)
    files.update({'source_snapshot/'+name:data for name,data in context['files'].items()})
    if quantiles is not None:
        files['ensemble_quantiles_SIMULATION.csv']=quantiles.to_csv(index=False).encode()
    if ensemble_raw is not None:
        files['ensemble_allan_SIMULATION.csv']=ensemble_raw.to_csv(index=False).encode()
    files['SHA256SUMS.txt']=''.join(f'{hashlib.sha256(v).hexdigest()}  {k}\n' for k,v in files.items()).encode()
    return files


def zip_files(files):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(name,data)
    return b.getvalue()
