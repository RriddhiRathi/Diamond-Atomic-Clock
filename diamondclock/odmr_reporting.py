"""Reproducible ODMR datasets and vector figures in the existing export system."""
from dataclasses import asdict
import hashlib
import json
import matplotlib.pyplot as plt
from .physics import Physics
from .odmr import ODMRConfig, Stark, spectrum, level_sweep, odmr_parameter_provenance, transform, transition_sensitivities
from .odmr_bridge import ReadoutScenario, compare_stability
from .reporting import ROOT, figure_bytes, environment, sources, provenance
from .reference_store import catalog_bytes, bibtex_bytes
from .run_provenance import capture, validate


def calculate(c=ODMRConfig(), clock_config=None, readout=None, p=Physics()):
    """Capture all selected inputs before any numerical calculation."""
    context=capture(config=c,physics=p)
    context['clock_config']=asdict(clock_config) if clock_config is not None else None
    context['readout_scenario']=asdict(readout) if readout is not None else None
    data,lines,levels=spectrum(c,p)
    sweep=level_sweep(c,p=p)
    sensitivity=[]
    for k in range(4):
        t=transition_sensitivities(c.temperature_K,transform(c.B_lab_G,k),
            transform(c.microwave_lab,k),transform(c.E_lab_V_m,k),p)
        t['orientation']=k+1
        sensitivity.append(t)
    import pandas as pd
    result=dict(spectrum=data,transitions=lines,levels=levels,sweep=sweep,
                sensitivities=pd.concat(sensitivity,ignore_index=True),context=context)
    if clock_config is not None:
        if readout is None:
            raise ValueError('Clock comparison requires an explicit readout scenario.')
        result['comparison']=compare_stability(clock_config,readout,p)
    validate(context)
    return result


def figures(result,c):
    """All curves are simulations; paper-derived equations are documented in ZIP."""
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none',
                         'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False}):
        signature=hashlib.sha256(json.dumps(asdict(c),sort_keys=True).encode()).hexdigest()[:12]
        foot=f'SIMULATION | Assumed Lorentzian linewidth and contrast\nConfig {signature} | Full reproducible inputs: config.json'
        data=result['spectrum']; out={}
        fig,ax=plt.subplots(figsize=(8,5.2),layout='constrained')
        for k,color in enumerate(['#149ca8','#ed9d38','#aa6bd3','#2470dd'],1):
            ax.plot(data.frequency_Hz/1e6,data[f'NV{k}_fluorescence'],label=f'NV{k}',color=color,alpha=.8,lw=1)
        ax.plot(data.frequency_Hz/1e6,data.combined_fluorescence,label='Weighted ensemble',color='#20242a',lw=1.8)
        ax.set(xlabel='Microwave frequency (MHz)',ylabel='Normalized fluorescence (model)',title='Four-orientation NV ODMR simulation')
        ax.legend(ncol=3,fontsize=8);ax.grid(alpha=.15)
        fig.supxlabel(foot,fontsize=7)
        out['odmr_spectrum_SIMULATION']=fig
        fig,ax=plt.subplots(figsize=(8,5.2),layout='constrained')
        sweep=result['sweep']
        for k,color in enumerate(['#149ca8','#ed9d38','#aa6bd3','#2470dd'],1):
            for rank in range(9):
                part=sweep[(sweep.orientation==k)&(sweep.energy_rank==rank)]
                ax.plot(part.field_G,part.energy_Hz/1e6,color=color,lw=.8,alpha=.7,label=f'NV{k}' if rank==8 else None)
        ax.set(xlabel='Field magnitude along chosen lab direction (G)',ylabel='Energy / h relative to lowest level (MHz)',title='Ground-state energy ranks; not spin-state tracking')
        ax.legend();ax.grid(alpha=.15);fig.supxlabel(foot,fontsize=7)
        out['odmr_levels_SIMULATION']=fig
        fig,ax=plt.subplots(figsize=(8,5.2),layout='constrained')
        t=result['sensitivities']
        for k,color in enumerate(['#149ca8','#ed9d38','#aa6bd3','#2470dd'],1):
            part=t[(t.orientation==k)&(t.dip_weight>1e-5)&(t.frequency_Hz>1e8)]
            norm=(part[['dnu_dBx_Hz_G','dnu_dBy_Hz_G','dnu_dBz_Hz_G']]**2).sum(axis=1,min_count=3)**.5
            ax.scatter(part.frequency_Hz/1e6,norm/1e6,label=f'NV{k}',color=color,s=18)
        ax.set(xlabel='Transition frequency (MHz)',ylabel='Magnitude of local magnetic gradient (MHz/G)',title='Magnetic sensitivity of active electronic transitions')
        ax.legend();ax.grid(alpha=.15);fig.supxlabel(foot+'\nDegenerate slopes omitted',fontsize=7)
        out['odmr_sensitivity_SIMULATION']=fig
        if 'comparison' in result:
            fig,ax=plt.subplots(figsize=(8,5.2),layout='constrained')
            a=result['comparison']['allan']
            for method,color in [('single_electron','#149ca8'),('electron_average','#ed9d38'),('composite','#2470dd')]:
                for scenario,style in [('Original assumed readout','--'),('ODMR-informed ideal readout','-')]:
                    part=a[(a.method==method)&(a.scenario==scenario)&(a.adev>0)]
                    ax.loglog(part.tau_s,part.adev,style,color=color,label=method+' | '+scenario,lw=1.3)
            ax.set(xlabel='Averaging time (s)',ylabel='Overlapping Allan deviation',title='Clock readout assumptions: paired Allan-deviation comparison')
            ax.legend(fontsize=7);ax.grid(which='both',alpha=.15)
            fig.supxlabel('SIMULATION | Ideal resolved-line photon readout; no lock or accuracy validation\nFull inputs and assumptions: comparison_inputs.json',fontsize=7)
            out['odmr_stability_comparison_SIMULATION']=fig
        return out


def export_odmr(result,c,p=Physics(),references=None):
    context=result['context'];validate(context)
    if context['config']!=asdict(c) or context['physics']!=asdict(p):
        raise ValueError('ODMR export inputs do not match the calculation.')
    catalog=sources() if references is None else references
    catalog_data=catalog_bytes(catalog)
    meta=dict(project='DiamondClock Lab',data_kind='SIMULATION',environment=environment(),
              provenance={k:v for k,v in context.items() if k!='files'},
              source_sha256=context['source_sha256'],stark=asdict(Stark()),
              reference_catalog_sha256=hashlib.sha256(catalog_data).hexdigest(),
              interpretation='Relative transition-strength fluorescence proxy; not a measured spectrum or validated optical model. No clock accuracy claim.')
    files={name+'_SIMULATION.csv':result[key].to_csv(index=False).encode() for name,key in
           [('odmr_spectrum','spectrum'),('odmr_transitions','transitions'),('odmr_levels','levels'),
            ('odmr_level_sweep','sweep'),('odmr_sensitivities','sensitivities')]}
    files.update({'config.json':json.dumps(asdict(c),indent=2).encode(),
        'parameter_provenance.csv':odmr_parameter_provenance(c).to_csv(index=False).encode(),
        'sources.json':catalog_data,'references.bib':bibtex_bytes(catalog),
        'ODMR_METHODS.md':(ROOT/'docs/ODMR_METHODS.md').read_bytes(),
        'odmr_equation_map.md':(ROOT/'references/odmr_equation_map.md').read_bytes(),
        'intern_odmr_as_supplied.m.txt':(ROOT/'legacy/matlab/intern_odmr_as_supplied.m.txt').read_bytes(),
        'MATLAB_ATTRIBUTION.md':(ROOT/'legacy/matlab/README.md').read_bytes()})
    files.update({'source_snapshot/'+name:data for name,data in context['files'].items()})
    if 'comparison' in result:
        comparison=result['comparison']
        if asdict(comparison['informed_config'])!={**context['clock_config'],
                'electron_readout_Hz':comparison['bridge_diagnostics']['per_line_sigma_at_1s_Hz']}:
            raise ValueError('Comparison configuration does not match its provenance.')
        inputs=dict(original_config=context['clock_config'],informed_config=asdict(comparison['informed_config']),
                    readout_scenario=context['readout_scenario'],diagnostics=comparison['bridge_diagnostics'],
                    estimator='Existing overlapping Allan deviation; no drift removal; tau <= N dt / 10',
                    interpretation='Paired stochastic realization, not ensemble confidence intervals. Only electronic readout sigma changes.')
        files['comparison_inputs.json']=json.dumps(inputs,indent=2).encode()
        files['comparison_clock_parameters.csv']=provenance(comparison['informed_config'],p).to_csv(index=False).encode()
        import pandas as pd
        readout_rows=[]
        for name,value in context['readout_scenario'].items():
            readout_rows.append(dict(parameter=name,value=value,
                unit={'linewidth_Hz':'Hz','photon_rate_per_s':'photons/s'}.get(name,'dimensionless'),
                source='MODEL',equation_source='DRE2011 Eqs. (2)-(3), p. 195204-2',
                locator='docs/ODMR_METHODS.md O5',
                implementation='diamondclock/odmr_bridge.py:ReadoutScenario.'+name,
                note='Assumed acquisition parameter; not inferred from the ensemble fluorescence proxy'))
        files['comparison_readout_parameters.csv']=pd.DataFrame(readout_rows).to_csv(index=False).encode()
        for key in ('original_trace','informed_trace','allan'):
            files['comparison_'+key+'_SIMULATION.csv']=comparison[key].to_csv(index=False).encode()
    figs=figures(result,c)
    try:
        for name,fig in figs.items():
            for fmt in ('svg','pdf'):
                files[name+'.'+fmt]=figure_bytes(fig,fmt)
    finally:
        for fig in figs.values():plt.close(fig)
    files['metadata.json']=json.dumps(meta,indent=2).encode()
    files['SHA256SUMS.txt']=''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n' for name,data in files.items()).encode()
    return files
