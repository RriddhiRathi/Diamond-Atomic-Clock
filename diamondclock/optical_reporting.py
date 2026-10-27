"""Phase 3 exports through the existing source-snapshot/checksum infrastructure."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import poisson
from .physics import Physics
from .optical_parameters import OpticalExperiment, OpticalConfig, parameter_records
from .optical_dynamics import build_system
from .optical_cycle import steady_state, rate_steady, populations
from .optical_measurement import cw_scan, optical_transient
from .photon_detection import count_distribution, sample_reference
from .reporting import environment, figure_bytes, sources
from .reference_store import catalog_bytes, bibtex_bytes
from .run_provenance import capture, validate

from .resources import project_root
ROOT=project_root()


def _table_hashes(tables):
    return {k:hashlib.sha256(v.to_csv(index=False).encode()).hexdigest() for k,v in tables.items()}


def calculate_optical(experiment=OpticalExperiment(),p=Physics()):
    experiment.validate();context=capture(config=experiment,physics=p)
    scan,contrast=cw_scan(experiment,p)
    tables={'fluorescence_measurements':scan,'contrast':contrast,
            'optical_initialization':optical_transient(experiment.optical,experiment.rates,p),
            'parameter_provenance':pd.DataFrame(parameter_records(experiment))}
    # Benchmarks use the seven-electronic-state system first, independently of extension.
    c=replace(experiment.optical,states=7)
    pump_rows=[];benchmark=[]
    for pump in np.geomspace(.1e6,20e6,13):
        off=build_system(replace(c,pump_s=float(pump),rabi_Hz=0),experiment.rates,p)
        on=build_system(replace(c,pump_s=float(pump)),experiment.rates,p)
        a=steady_state(off);b=steady_state(on)
        ea=float(np.trace(off.emission_operator()@a).real)
        eb=float(np.trace(on.emission_operator()@b).real)
        pump_rows.append(dict(pump_s=pump,off_emitted_s=ea,on_emitted_s=eb,
            intrinsic_contrast=1-eb/ea,**populations(off,a)))
    for field in (5.,20.,50.):
        for pump in (1e6,4e6):
            for rabi in (0.,20e3,200e3):
                system=build_system(replace(c,Bz_G=field,pump_s=pump,rabi_Hz=rabi),experiment.rates,p)
                master=steady_state(system);rate=rate_steady(system)
                benchmark.append(dict(Bz_G=field,pump_s=pump,rabi_Hz=rabi,
                    maximum_population_error=float(np.max(abs(np.diag(master)-np.diag(rate)))),
                    master_emitted_s=float(np.trace(system.emission_operator()@master).real),
                    rate_emitted_s=float(np.trace(system.emission_operator()@rate).real),
                    interpretation='Numerical solver comparison; not experimental validation'))
    tables['pump_response']=pd.DataFrame(pump_rows);tables['solver_benchmarks']=pd.DataFrame(benchmark)
    selected=[]
    centre=scan.microwave_frequency_Hz.mean()
    for offset in (-2.2e6,0.,2.2e6):
        system=build_system(experiment.optical,experiment.rates,p,centre+offset)
        master=steady_state(system);rate=rate_steady(system)
        selected.append(dict(microwave_frequency_Hz=centre+offset,states=experiment.optical.states,
            maximum_population_error=float(np.max(abs(np.diag(master)-np.diag(rate)))),
            master_emitted_s=float(np.trace(system.emission_operator()@master).real),
            rate_emitted_s=float(np.trace(system.emission_operator()@rate).real),
            interpretation='Selected settings only; no certification of all scan frequencies'))
    tables['selected_model_comparison']=pd.DataFrame(selected)
    reference=[];trials=[];refconfig=[]
    for index,(eff,gate) in enumerate([(.01,20e-6),(1.,1e-6)]):
        rc=replace(c,rabi_Hz=0);system=build_system(rc,experiment.rates,p);rho=steady_state(system)
        prob=count_distribution(system,rho,gate,eff)
        n=np.arange(len(prob));mean=float(n@prob);var=float((n-mean)**2@prob)
        seed=int(np.random.SeedSequence([experiment.seed,9000+index]).generate_state(1)[0])
        observed=sample_reference(prob,4096,seed)
        for count,v in enumerate(prob):
            reference.append(dict(scenario=index,n=count,probability=v,poisson_probability=poisson.pmf(count,mean),
                expected_counts=mean,variance=var,efficiency=eff,gate_s=gate,
                count_model='number_resolved_lindblad',states=7,seed=seed))
        for j,count in enumerate(observed):
            trials.append(dict(scenario=index,repetition=j,expected_counts=mean,detected_counts=int(count),
                gate_s=gate,acquisition_start_s=j*gate,seed=seed,
                microwave_frequency_Hz=float(system.ground_energies_Hz.max()),microwave='off',
                count_model='number_resolved_lindblad',**populations(system,rho)))
        refconfig.append(dict(scenario=index,optical=asdict(rc),centers=1,efficiency=eff,
            gate_s=gate,background_s=0,dark_s=0,repetitions=4096,seed=seed,
            expected_counts=mean,variance=var,fano=var/mean))
    tables['photon_count_distribution']=pd.DataFrame(reference);tables['reference_photon_trials']=pd.DataFrame(trials)
    s=build_system(experiment.optical,experiment.rates,p)
    state_rows=[]
    for i in range(s.dimension):
        row=dict(index=i,manifold='ground_eigenstate' if i<s.ng else 'excited_bare' if i<2*s.ng else 'effective_singlet')
        if i<s.ng:
            row['energy_Hz']=s.ground_energies_Hz[i]
            row.update({f'bare_overlap_{j}':float(x) for j,x in enumerate(abs(s.ground_vectors[:,i])**2)})
        state_rows.append(row)
    tables['state_map']=pd.DataFrame(state_rows)
    r=experiment.rates
    summary=dict(data_kind='SIMULATION',experimental_validation=False,
        expected_maximum_grid_contrast=float(contrast.expected_detected_contrast.max()),
        grid_maximum_is_not_fitted_resonance=True,
        lifetime_zero_ns=1e9/(r.radiative_s+r.isc_zero_s),
        lifetime_pm_ns=1e9/(r.radiative_s+r.isc_pm_s),
        singlet_lifetime_ns=1e9/(r.singlet_zero_s+2*r.singlet_pm_s),
        counting_reference=refconfig,
        scope='Single NV orientation, local axial 5..50 G, E=0, nominal 297 K. No 475 G support; no clock lock.',
        rate_backend='Steady Bloch-coherence elimination; compare with Lindblad, not identical in general',
        extension='21-state independent optical channels in ground eigenbasis; excited/singlet nuclear dynamics omitted',
        preparation='CW gates begin in individual stationary states; initialization dataset is separate; preparation overhead excluded',
        uncertainty='Published rate uncertainties retained, not propagated; no fit to user apparatus or experimental dataset')
    validate(context)
    return dict(tables=tables,summary=summary,context=context,table_sha256=_table_hashes(tables),
                summary_sha256=hashlib.sha256(json.dumps(summary,sort_keys=True).encode()).hexdigest())


def optical_figures(result,experiment):
    tables=result['tables'];figs={}
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','pdf.fonttype':42,
                        'axes.spines.top':False,'axes.spines.right':False}):
        c=experiment.optical;det=experiment.detector
        foot=(f'SIMULATION | {c.states} states | B={c.Bz_G:g} G | pump={c.pump_s/1e6:g} million/s | Rabi={c.rabi_Hz/1e3:g} kHz\n'
              f'Gate={experiment.dwell_s*1e3:g} ms | N={det.centers} | efficiency={det.efficiency:g} | seed={experiment.seed} | Full config.json | No clock lock')
        data=tables['fluorescence_measurements'];on=data[data.microwave=='on'];off=data[data.microwave=='off']
        fig,(ax,bx)=plt.subplots(2,1,figsize=(8,6.5),layout='constrained',sharex=True)
        ax.plot(on.microwave_frequency_Hz/1e6,on.expected_counts,color='#149ca8',label='Optical-model mean, MW on')
        ax.plot(off.microwave_frequency_Hz/1e6,off.expected_counts,'--',color='#ed9d38',label='Optical-model mean, MW off')
        ax.scatter(on.microwave_frequency_Hz/1e6,on.detected_counts,s=9,alpha=.55,color='#2470dd',label='Synthetic detected counts')
        ax.set(ylabel='Detected photons per gate',title='Optically generated ODMR measurement');ax.legend(fontsize=8)
        part=tables['contrast'];bx.plot(part.microwave_frequency_Hz/1e6,100*part.expected_detected_contrast,color='#149ca8')
        bx.scatter(part.microwave_frequency_Hz/1e6,100*part.sampled_contrast,color='#2470dd',s=9,alpha=.5)
        bx.set(xlabel='Microwave frequency (MHz)',ylabel='Contrast (%)');fig.supxlabel(foot,fontsize=7)
        figs['optical_spectrum_SIMULATION']=fig
        fig,ax=plt.subplots(figsize=(8,4.8),layout='constrained');data=tables['optical_initialization']
        for key,label in [('ground_zero','Ground m_s=0'),('ground_pm','Ground m_s=+/-1'),('excited_zero','Excited m_s=0'),('excited_pm','Excited m_s=+/-1'),('singlet','Singlet')]:
            ax.plot(data.time_s*1e6,data[key],label=label)
        ax.set(xlabel='Time after laser turn-on (us)',ylabel='Population',title='Optical pumping and singlet shelving; MW off');ax.legend(fontsize=8)
        fig.supxlabel(f'SIMULATION | {c.states} states | B={c.Bz_G:g} G | pump={c.pump_s/1e6:g} million/s | MW off\nInitially mixed ground state | No experimental fit or clock lock | Full config.json',fontsize=7)
        figs['optical_initialization_SIMULATION']=fig
        fig,(ax,bx)=plt.subplots(1,2,figsize=(9,4.6),layout='constrained')
        for scenario,axis in enumerate((ax,bx)):
            data=tables['photon_count_distribution'];data=data[data.scenario==scenario]
            visible=(data.probability>1e-6)|(data.poisson_probability>1e-6)
            axis.plot(data.n[visible],data.probability[visible],'o-',label='Number-resolved Lindblad')
            axis.plot(data.n[visible],data.poisson_probability[visible],'s--',label='Poisson with same mean')
            axis.set(xlabel='Detected photons per gate',ylabel='Probability',title=f'7 states: efficiency {data.efficiency.iloc[0]:g}, gate {data.gate_s.iloc[0]*1e6:g} us')
            axis.legend(fontsize=7)
        fig.supxlabel('SIMULATION | Independent stationary gates; single emitter | Not an experimental histogram',fontsize=7)
        figs['optical_photon_statistics_SIMULATION']=fig
        fig,(ax,bx)=plt.subplots(1,2,figsize=(9,4.6),layout='constrained');data=tables['pump_response']
        ax.plot(data.pump_s/1e6,data.off_emitted_s/1e6,label='MW off');ax.plot(data.pump_s/1e6,data.on_emitted_s/1e6,label='MW on')
        ax.set(xlabel='Optical pump rate (million/s)',ylabel='Emitted photons (million/s)',title='Seven-state pump response');ax.legend(fontsize=8)
        bx.plot(data.pump_s/1e6,data.intrinsic_contrast*100,color='#149ca8');bx.set(xlabel='Optical pump rate (million/s)',ylabel='Predicted intrinsic contrast (%)',title='Contrast calculated from populations')
        fig.supxlabel(f'SIMULATION | B={c.Bz_G:g} G | Rabi={c.rabi_Hz/1e3:g} kHz | Tetienne NV E fitted rates\nOperating inputs assumed | No fit to this apparatus | Full config.json',fontsize=7)
        figs['optical_pump_response_SIMULATION']=fig
    return figs


def export_optical(result,experiment,p=Physics(),references=None):
    validate(result['context'])
    if result['context']['config']!=asdict(experiment) or result['context']['physics']!=asdict(p):
        raise ValueError('Optical export configuration differs from calculation.')
    if _table_hashes(result['tables'])!=result['table_sha256']:
        raise ValueError('Optical numerical results changed after calculation.')
    if hashlib.sha256(json.dumps(result['summary'],sort_keys=True).encode()).hexdigest()!=result['summary_sha256']:
        raise ValueError('Optical summary changed after calculation.')
    catalog=sources() if references is None else references;catalog_data=catalog_bytes(catalog)
    files={k+'_SIMULATION.csv':v.to_csv(index=False).encode() for k,v in result['tables'].items()}
    files['config.json']=json.dumps(asdict(experiment),indent=2).encode()
    files['summary.json']=json.dumps(result['summary'],indent=2).encode()
    files['metadata.json']=json.dumps(dict(environment=environment(),data_kind='SIMULATION',
        provenance={k:v for k,v in result['context'].items() if k!='files'},
        reference_catalog_sha256=hashlib.sha256(catalog_data).hexdigest(),numerical_table_sha256=result['table_sha256']),indent=2).encode()
    files['sources.json']=catalog_data;files['references.bib']=bibtex_bytes(catalog)
    for name in ('docs/OPTICAL_METHODS.md','docs/OPTICAL_VALIDATION.md','references/optical_equation_map.md',
                 'legacy/matlab/README.md','legacy/matlab/intern_odmr_as_supplied.m.txt'):
        files[name]=(ROOT/name).read_bytes()
    files.update({'source_snapshot/'+name:data for name,data in result['context']['files'].items()})
    figs=optical_figures(result,experiment)
    try:
        for name,fig in figs.items():
            for fmt in ('svg','pdf'):files[name+'.'+fmt]=figure_bytes(fig,fmt)
    finally:
        for fig in figs.values():plt.close(fig)
    files['SHA256SUMS.txt']=''.join(f'{hashlib.sha256(v).hexdigest()}  {name}\n' for name,v in files.items()).encode()
    return files
