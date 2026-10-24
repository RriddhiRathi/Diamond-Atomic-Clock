"""Causal clock simulation. Only CountObservation/Calibration reach inference (CLK1-6)."""
from dataclasses import asdict
import heapq
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from .physics import Physics, thermal_parameters
from .count_observations import CountObservation
from .frequency_estimation import fit_acquisition, estimate_detuning
from .clock_controller import PhotonController
from .clock_parameters import ClockExperiment
from .clock_plant import OpticalClockPlant
from .oscillator import free_frequency, phase_and_time
from .stability import overlapping_adev


class ClockTimeLimit(Exception):pass


class _ExperimentClock:
    """Private ideal-time integrator with LO-derived gate/latency deadlines."""
    def __init__(self,c,plant,f0,free,photon_seed):
        self.c=c;self.plant=plant;self.f0=f0;self.free=free;self.rng=np.random.default_rng(photon_seed)
        self.t=0.;self.local=0.;self.index=0;self.u=0.;self.integral=0.;self.correction_integral=0.
        self.queue=[];self.serial=0;self.events=[];self.observed=[];self.truth=[];self.output=[];self.status='ACQUIRING'

    def request(self,command,cycle):
        self.serial+=1;deadline=self.local+self.c.controller.latency_s
        heapq.heappush(self.queue,(deadline,self.serial,float(command),cycle))
        return deadline

    def advance(self,duration,probe=0.,microwave=True):
        target=self.local+duration;mean=0.
        while self.local<target-1e-13:
            while self.queue and self.queue[0][0]<=self.local+1e-12:
                ready,serial,command,cycle=heapq.heappop(self.queue);self.u=command
                self.events.append(dict(cycle=cycle,request_id=serial,applied_local_s=self.local,
                    applied_true_s=self.t,deadline_local_s=ready,correction_Hz=command))
            if self.index>=len(self.free):raise ClockTimeLimit()
            f=self.free[self.index]+self.u
            ratio=1+f/self.f0
            if not .99<ratio<1.01:raise ValueError('Clock frequency outside supported monotone local timebase.')
            next_boundary=(self.index+1)*self.c.native_dt_s
            h=min(next_boundary-self.t,(target-self.local)/ratio)
            if self.queue:h=min(h,max(0.,(self.queue[0][0]-self.local)/ratio))
            if h<=1e-14:
                if next_boundary-self.t<1e-12:h=max(0.,next_boundary-self.t)
                else:continue
            emitted=self.plant.step(self.f0+f+probe,h,microwave)
            det=self.c.detector
            mean+=det.efficiency*det.centers*emitted+(det.background_s+det.dark_s)*h
            self.integral+=f*h;self.correction_integral+=self.u*h
            self.t+=h;self.local+=ratio*h
            if self.t>=next_boundary-1e-12:
                deviation=self.integral/self.c.native_dt_s
                self.output.append(dict(time_s=self.index*self.c.native_dt_s,
                    locked_deviation_Hz=deviation,unlocked_deviation_Hz=float(self.free[self.index]),
                    mean_correction_Hz=self.correction_integral/self.c.native_dt_s,status=self.status))
                self.index+=1;self.integral=0.;self.correction_integral=0.;self.t=next_boundary
        return mean

    def measure(self,probe,enabled,stage,cycle):
        self.advance(self.c.settling_s,probe,enabled)
        start=self.t;local=self.local
        mean=self.advance(self.c.gate_s,probe,enabled)
        counts=int(self.rng.poisson(mean))
        observation=CountObservation(float(probe),self.c.gate_s,counts,bool(enabled),local)
        ident=len(self.observed)
        self.observed.append(dict(observation_id=ident,stage=stage,cycle=cycle,**asdict(observation)))
        self.truth.append(dict(observation_id=ident,true_start_s=start,true_end_s=self.t,
            actual_duration_s=self.t-start,expected_counts=mean,**self.plant.population_summary()))
        return observation


def run_clock(c=ClockExperiment(),p=Physics()):
    c.validate()
    f0=float(thermal_parameters(c.optical.temperature_K,p)[0]+p.gamma_e_Hz_G*c.optical.Bz_G)
    streams=np.random.SeedSequence(c.seed).spawn(2)
    lo_seed=int(streams[0].generate_state(1)[0]);photon_seed=int(streams[1].generate_state(1)[0])
    free=free_frequency(c.oscillator,c.native_dt_s,c.maximum_time_s,lo_seed)
    plant=OpticalClockPlant(c.optical,c.rates,f0,c.reference_offset_Hz,c.plant_backend,p)
    engine=_ExperimentClock(c,plant,f0,free,photon_seed);controller=PhotonController(c.controller)
    feedback=[];acquisitions=[];cal=None;attempts=0;timed_out=False
    try:
        engine.advance(50e-6,0.,False)
        for cycle in range(c.cycles):
            reacquire=cal is None or controller.bad>=c.controller.consecutive_bad
            if reacquire and attempts<=c.controller.max_reacquisitions:
                engine.status='ACQUIRING';engine.queue.clear();attempts+=1
                batch=[engine.measure(0.,False,'acquisition',cycle)]
                batch += [engine.measure(float(x),True,'acquisition',cycle) for x in np.linspace(-c.acquisition_span_Hz,c.acquisition_span_Hz,c.acquisition_points)]
                batch.append(engine.measure(0.,False,'acquisition',cycle))
                offsets=(0.,)  # first validate the seven-electronic-state lock
                cal=fit_acquisition(batch,offsets)
                acquisitions.append(dict(attempt=attempts,cycle=cycle,local_end_s=engine.local,**asdict(cal)))
                if cal.valid:
                    request=controller.acquired(engine.u+cal.centre_command_Hz)
                    engine.request(request,cycle)
                else:
                    controller.bad=c.controller.consecutive_bad;engine.status='LOST'
            if cal is None or not cal.valid:
                engine.status='LOST';engine.advance(6*(c.gate_s+c.settling_s),0.,False)
                feedback.append(dict(cycle=cycle,local_end_s=engine.local,valid=False,locked=False,reason='no_calibration'))
                continue
            start=engine.local;batch=[]
            for probe,enabled in [(0.,False),(c.dither_Hz,True),(-c.dither_Hz,True),(-c.dither_Hz,True),(c.dither_Hz,True),(0.,False)]:
                batch.append(engine.measure(probe,enabled,'tracking',cycle))
            estimate=estimate_detuning(batch,cal,c.controller.capture_Hz)
            command=controller.update(estimate,engine.local-start)
            ready=engine.request(command,cycle) if command is not None else np.nan
            engine.status='LOCKED' if controller.locked else 'TRACKING' if estimate.valid else 'LOST'
            feedback.append(dict(cycle=cycle,local_start_s=start,local_end_s=engine.local,
                measurement_midpoint_local_s=np.mean([o.local_start_s+o.nominal_gate_s/2 for o in batch]),
                **asdict(estimate),locked=controller.locked,requested_correction_Hz=command,
                correction_deadline_local_s=ready))
        # Complete the last native interval; clock output never drops dead-time samples.
        if engine.t>engine.index*c.native_dt_s+1e-12:
            remaining=(engine.index+1)*c.native_dt_s-engine.t
            ratio=1+(free[engine.index]+engine.u)/f0
            engine.advance(remaining*ratio,0.,False)
    except ClockTimeLimit:timed_out=True
    output=pd.DataFrame(engine.output)
    if len(output)<20:raise ValueError('Record too short for clock stability analysis.')
    allan=[]
    for name in ('locked','unlocked'):
        delta=output[name+'_deviation_Hz'].to_numpy()
        phase,time_error=phase_and_time(delta,c.native_dt_s,f0)
        output[name+'_y']=delta/f0;output[name+'_phase_error_rad']=phase[:-1]
        output[name+'_time_error_s']=time_error[:-1]
        a=overlapping_adev(delta/f0,c.native_dt_s);a['method']=name;allan.append(a)
    e=plant.system.ground_energies_Hz;u=plant.system.ground_vectors
    bare,order=linear_sum_assignment(-abs(u)**2);order=order[np.argsort(bare)]
    reference=e[order[0]]-e[order[1]]  # offline seven-state target only
    output['evaluation_error_to_hamiltonian_Hz']=f0+output.locked_deviation_Hz-reference
    for name in ('locked','unlocked'):
        last=output[name+'_deviation_Hz'].iloc[-1]
        # Endpoint values are separate from interval-start phase/time columns.
        output.attrs[name+'_final_phase_error_rad']=float(2*np.pi*output[name+'_deviation_Hz'].sum()*c.native_dt_s)
        output.attrs[name+'_final_time_error_s']=output.attrs[name+'_final_phase_error_rad']/(2*np.pi*f0)
    tables=dict(clock_output=output,photon_observations=pd.DataFrame(engine.observed),
        feedback=pd.DataFrame(feedback),actuation=pd.DataFrame(engine.events),
        evaluation_measurement_truth=pd.DataFrame(engine.truth),acquisition=pd.DataFrame(acquisitions),
        allan=pd.concat(allan,ignore_index=True))
    diagnostics=dict(data_kind='SIMULATION',experimental_validation=False,nominal_Hz=f0,
        evaluation_hamiltonian_reference_Hz=float(reference),lo_seed=lo_seed,photon_seed=photon_seed,
        timed_out=timed_out,acquisitions=attempts,record_s=len(output)*c.native_dt_s,
        observed_lock_fraction=float(np.mean([v.get('locked',False) for v in feedback])),
        final_time_errors_s={name:output.attrs[name+'_final_time_error_s'] for name in ('locked','unlocked')},
        optical_trace_roundoff_max=plant.last_normalization_error,
        uncertainty='Count-only profile intervals plus first-order independent calibration-shape covariance; coverage tested, not guaranteed.',
        scope='Low-field single-transition NV-referenced LO. No SI accuracy claim or 475 G optical validation.')
    return tables,diagnostics
