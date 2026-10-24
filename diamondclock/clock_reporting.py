"""Traceable Phase 4 runs: observed data, output clocks and offline oracle evaluation."""
from dataclasses import asdict
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from .clock_parameters import ClockExperiment
from .clock_simulation import run_clock
from .clock_validation import estimator_monte_carlo,physical_estimator_cases,optical_model_comparison,counting_cases
from .physics import Physics
from .optical_parameters import OpticalExperiment,parameter_records
from .reporting import environment,figure_bytes,sources,ROOT
from .reference_store import catalog_bytes,bibtex_bytes
from .run_provenance import capture,validate


def table_bytes(table):
    table=table.copy()
    for key in table.select_dtypes(include='object'):
        table[key]=table[key].map(lambda v:json.dumps(v) if isinstance(v,(tuple,list,dict)) else v)
    return table.to_csv(index=False).encode()


def table_hashes(tables):return {k:hashlib.sha256(table_bytes(v)).hexdigest() for k,v in tables.items()}


def clock_parameters(c):
    records=parameter_records(OpticalExperiment(optical=c.optical,rates=c.rates,detector=c.detector))
    records=[r for r in records if r['parameter'].startswith(('optical.','detector.')) or r.get('published_value') is not None]
    units=dict(offset_Hz='Hz',drift_Hz_s='Hz/s',white_fm_Hz_at_1s='Hz sqrt(s)',
        random_walk_Hz_sqrt_s='Hz/sqrt(s)',phase_noise_rad='rad',proportional='1',
        integral_per_s='1/s',latency_s='s',correction_limit_Hz='Hz',capture_Hz='Hz',
        lock_error_Hz='Hz',lock_sigma_Hz='Hz',consecutive_good='cycles',consecutive_bad='cycles',
        max_reacquisitions='scans',native_dt_s='s',gate_s='s',settling_s='s',cycles='cycles',
        acquisition_points='points',acquisition_span_Hz='Hz',dither_Hz='Hz',maximum_time_s='s',
        fixed_analysis_start_s='s',seed='integer seed',reference_offset_Hz='Hz',plant_backend='categorical')
    for group,obj in [('oscillator',c.oscillator),('controller',c.controller)]:
        for name,value in asdict(obj).items():
            records.append(dict(parameter=group+'.'+name,value=value,classification='simulation_assumption',
                source='MODEL',locator='docs/CLOCK_METHODS.md',experimental_validation='None',
                unit=units[name]))
    for name,value in asdict(c).items():
        if isinstance(value,dict):continue
        records.append(dict(parameter=name,value=value,classification='plant_only_assumption' if name=='reference_offset_Hz' else 'numerical_protocol',
            source='MODEL',locator='docs/CLOCK_METHODS.md',experimental_validation='None',unit=units[name]))
    return pd.DataFrame(records)


def calculate_clock(c=ClockExperiment(),validation_trials=0,physical_trials=0,p=Physics()):
    c.validate()
    if not isinstance(validation_trials,int) or not 0<=validation_trials<=2000 or not isinstance(physical_trials,int) or not 0<=physical_trials<=500:
        raise ValueError('Validation limits: matched 0..2000 and physical 0..500 trials.')
    context=capture(config=c,physics=p)
    protocol=dict(matched_trials=validation_trials,physical_trials=physical_trials,
        matched_seed=411,physical_seed=412,gate_s=c.gate_s,centers=c.detector.centers,
        efficiency=c.detector.efficiency,reference='Sequential driven gates and joint counting moments')
    context['validation_protocol']=dict(protocol)
    tables,summary=run_clock(c,p)
    tables['parameter_provenance']=clock_parameters(c)
    tables['optical_backend_comparison']=optical_model_comparison(c,p)
    tables['driven_counting_reference']=counting_cases(c,p)
    if validation_trials:tables['matched_estimator_validation']=estimator_monte_carlo(c.optical.states,validation_trials,411,c.gate_s,1.28e6*c.detector.centers*c.detector.efficiency)
    if physical_trials:tables['physical_estimator_validation']=physical_estimator_cases(c.optical.states,physical_trials,412,
        c.detector.centers,c.detector.efficiency,c.detector.background_s+c.detector.dark_s,c.gate_s,
        experiment=c,physics=p)
    validation=[]
    for key in ('matched_estimator_validation','physical_estimator_validation'):
        if key not in tables:continue
        frame=tables[key];good=frame[frame.valid]
        validation.append(dict(dataset=key,trials=len(frame),accepted=len(good),
            bias_Hz=float(good.error_Hz.mean()),rmse_Hz=float(np.sqrt(np.mean(good.error_Hz**2))),
            interval_coverage=float(good.covered.mean()),
            unconditional_interval_coverage=float((frame.valid & frame.covered).mean()),
            interpretation='Offline Monte Carlo numerical validation, not measured apparatus performance'))
    summary['estimator_validation']=validation
    summary['validation_protocol']=protocol
    summary['count_model']='Poisson gate approximation; driven Lindblad variance/covariance reference exported'
    summary['optical_backend']=c.plant_backend
    summary['absolute_frequency']='Acquisition is in commanded-frequency coordinates; photons constrain oscillator-reference detuning, not an SI calibration'
    summary['timing']='Gate and actuator deadlines use the local oscillator timebase; true simulation timestamps are evaluator-only'
    validate(context)
    return dict(tables=tables,summary=summary,context=context,validation_protocol=protocol,
        table_sha256=table_hashes(tables),summary_sha256=hashlib.sha256(json.dumps(summary,sort_keys=True).encode()).hexdigest())


def clock_figures(result,c):
    tables=result['tables'];out=tables['clock_output'];figures={}
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','pdf.fonttype':42,
                        'axes.spines.top':False,'axes.spines.right':False}):
        foot=(f'SIMULATION | {c.optical.states} states | B={c.optical.Bz_G:g} G | seed={c.seed} | {c.plant_backend} optical dynamics\n'
              f'Gate={c.gate_s*1e3:g} ms | Ki={c.controller.integral_per_s:g}/s | latency={c.controller.latency_s*1e3:g} ms | observed lock={100*result["summary"]["observed_lock_fraction"]:.1f}% | No accuracy claim')
        stride=max(1,len(out)//3000);part=out.iloc[::stride]
        fig,(ax,bx)=plt.subplots(2,1,figsize=(8.5,6.4),layout='constrained',sharex=True)
        for name,color in [('unlocked','#999999'),('locked','#149ca8')]:
            ax.plot(part.time_s,part[name+'_deviation_Hz']/1e3,label='feedback enabled' if name=='locked' else 'free running',color=color,lw=1)
        ax.set(ylabel='Frequency minus nominal (kHz)',title='Actual oscillator output; probe dither excluded');ax.legend(fontsize=8)
        fb=tables['feedback']
        if 'detuning_Hz' in fb:
            good=fb[fb.valid & np.isfinite(fb.sigma_Hz)]
            x=good.measurement_midpoint_local_s
            bx.plot(x,good.detuning_Hz/1e3,color='#2470dd',lw=.8,label='Accepted photon estimates')
            bx.fill_between(x,(good.detuning_Hz-good.sigma_Hz)/1e3,(good.detuning_Hz+good.sigma_Hz)/1e3,alpha=.15,color='#2470dd',label='Reported 1 sigma')
            bx.legend(fontsize=8)
            bx.text(.02,.95,f'{len(fb)-len(good)} rejected cycles retained in CSV',transform=bx.transAxes,fontsize=7,va='top')
        else:bx.text(.5,.5,'No acquired resonance / no tracking estimates',transform=bx.transAxes,ha='center')
        bx.set(xlabel='Time (s); feedback uses local-clock timestamps',ylabel='Estimated detuning (kHz)')
        fig.supxlabel(foot,fontsize=7);figures['clock_frequency_feedback_SIMULATION']=fig
        fig,(ax,bx)=plt.subplots(2,1,figsize=(8.5,6.4),layout='constrained',sharex=True)
        for name,color in [('unlocked','#999999'),('locked','#149ca8')]:
            ax.plot(part.time_s,part[name+'_phase_error_rad'],color=color,label='feedback enabled' if name=='locked' else 'free running')
            bx.plot(part.time_s,part[name+'_time_error_s']*1e6,color=color)
        ax.set(ylabel='Phase deviation (rad)',title='Continuous clock phase and accumulated time error');ax.legend(fontsize=8)
        bx.set(xlabel='True simulation time (s)',ylabel='Time error from nominal (us)')
        fig.supxlabel(foot+'\nA constant reference offset can remain even when Allan deviation improves',fontsize=7)
        figures['clock_phase_time_SIMULATION']=fig
        fig,ax=plt.subplots(figsize=(8.5,5.6),layout='constrained')
        for name,color in [('unlocked','#999999'),('locked','#149ca8')]:
            for key,style,label in [('allan','-','full record'),('allan_fixed_window','--',f'fixed t >= {c.fixed_analysis_start_s:g} s')]:
                a=tables[key];a=a[(a.method==name)&(a.adev>0)]
                ax.loglog(a.tau_s,a.adev,style,color=color,label=('feedback enabled' if name=='locked' else 'free running')+' | '+label)
        ax.set(xlabel='Averaging time (s)',ylabel='Overlapping Allan deviation',title='Stability of actual clock output; failures and drift retained')
        ax.legend(fontsize=8);ax.grid(which='both',alpha=.15)
        fig.supxlabel(foot+'\nDashed window is predeclared, not selected using lock quality or hidden truth',fontsize=7)
        figures['clock_stability_SIMULATION']=fig
        if 'matched_estimator_validation' in tables:
            df=tables['matched_estimator_validation'];good=df[df.valid]
            fig,(ax,bx)=plt.subplots(1,2,figsize=(9,4.8),layout='constrained')
            ax.hist(good.error_Hz/1e3,bins=20,color='#149ca8');ax.set(xlabel='Acquisition error (kHz)',ylabel='Trials',title='Blind count-estimator Monte Carlo')
            if 'tracking_error_Hz' in df:
                good=df[df.tracking_valid]
                bx.hist(good.tracking_error_Hz/good.tracking_sigma_Hz,bins=20,color='#2470dd')
                bx.set(xlabel='Tracking error / reported sigma',ylabel='Trials',title='Calibration uncertainty included to first order')
            fig.supxlabel('SIMULATION | Matched line-family statistics; separate Lindblad-spectrum bias cases in CSV\nHidden truth used only by offline evaluator; no oracle correction in feedback',fontsize=7)
            figures['clock_estimator_validation_SIMULATION']=fig
    return figures


def export_clock(result,c,p=Physics(),references=None):
    context=result['context'];validate(context)
    if context['config']!=asdict(c) or context['physics']!=asdict(p):raise ValueError('Clock export configuration differs from calculation.')
    if context['validation_protocol']!=result['validation_protocol']:raise ValueError('Clock validation protocol changed.')
    if table_hashes(result['tables'])!=result['table_sha256']:raise ValueError('Clock tables changed after calculation.')
    if hashlib.sha256(json.dumps(result['summary'],sort_keys=True).encode()).hexdigest()!=result['summary_sha256']:
        raise ValueError('Clock summary changed after calculation.')
    catalog=sources() if references is None else references;reference_data=catalog_bytes(catalog)
    files={k+'_SIMULATION.csv':table_bytes(v) for k,v in result['tables'].items()}
    files.update({'config.json':json.dumps(asdict(c),indent=2).encode(),
        'summary.json':json.dumps(result['summary'],indent=2).encode(),
        'metadata.json':json.dumps(dict(environment=environment(),data_kind='SIMULATION',
            provenance={k:v for k,v in context.items() if k!='files'},numerical_sha256=result['table_sha256'],
            reference_catalog_sha256=hashlib.sha256(reference_data).hexdigest(),
            estimator_allowed_inputs=['probe_offset_Hz','nominal_gate_s','detected_counts','microwave_on','local_start_s']),indent=2).encode(),
        'sources.json':reference_data,'references.bib':bibtex_bytes(catalog)})
    for name in ('docs/CLOCK_METHODS.md','docs/CLOCK_VALIDATION.md','references/clock_equation_map.md',
                 'legacy/matlab/README.md','legacy/matlab/intern_odmr_as_supplied.m.txt'):
        files[name]=(ROOT/name).read_bytes()
    files.update({'source_snapshot/'+name:data for name,data in context['files'].items()})
    figures=clock_figures(result,c)
    try:
        for name,fig in figures.items():
            for fmt in ('svg','pdf'):files[name+'.'+fmt]=figure_bytes(fig,fmt)
    finally:
        for fig in figures.values():plt.close(fig)
    files['SHA256SUMS.txt']=''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n' for name,data in files.items()).encode()
    return files
