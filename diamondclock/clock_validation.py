"""Offline validation only. Oracle values here never enter online inference/control."""
from dataclasses import replace
import numpy as np
import pandas as pd
from .physics import Physics,thermal_parameters
from .count_observations import CountObservation
from .frequency_estimation import fit_acquisition,estimate_detuning,dip_profile
from .clock_parameters import ClockExperiment
from .clock_plant import OpticalClockPlant
from .clock_counting_reference import gate_moments,adjacent_gate_covariance
from .optical_dynamics import build_system
from .optical_cycle import steady_state


def estimator_monte_carlo(states=7,trials=100,seed=411,gate_s=.02,baseline_per_s=1.28e6):
    """Independent calibration/tracking counts; matched line family tests statistics.

    This does NOT test the line-family approximation against optical physics;
    optical_model_comparison and physical_estimator_cases do that separately.
    """
    rng=np.random.default_rng(seed);offsets=(0.,) if states==7 else (-2.16519e6,0.,2.16519e6)
    fractions=(.125,) if states==7 else (.05,.055,.045)
    x=np.linspace(-4e6,4e6,61);rows=[]
    for trial in range(trials):
        centre=float(rng.uniform(-.25e6,.25e6))
        rate=baseline_per_s*(1-dip_profile((x-centre)/1e6,np.log(.9),fractions,np.array(offsets)/1e6))
        observations=[CountObservation(float(f),gate_s,int(n)) for f,n in zip(x,rng.poisson(rate*gate_s))]
        cal=fit_acquisition(observations,offsets,profile=False)
        error=cal.centre_command_Hz-centre
        row=dict(trial=trial,states=states,seed=seed,evaluation_true_command_Hz=centre,
            estimated_command_Hz=cal.centre_command_Hz,error_Hz=error,reported_sigma_Hz=cal.centre_sigma_Hz,
            valid=cal.valid,covered=cal.lower_Hz<=centre<=cal.upper_Hz,
            interval='acquisition Fisher/Wald; production acquisition uses profile likelihood')
        detuning=float(rng.uniform(-100e3,100e3));batch=[]
        for probe,on in [(0.,False),(250e3,True),(-250e3,True),(-250e3,True),(250e3,True),(0.,False)]:
            depth=dip_profile(np.array([(probe+detuning)/1e6]),np.log(.9),fractions,np.array(offsets)/1e6)[0] if on else 0.
            batch.append(CountObservation(probe,gate_s,int(rng.poisson(gate_s*baseline_per_s*(1-depth))),on))
        est=estimate_detuning(batch,cal)
        row.update(tracking_valid=est.valid,tracking_error_Hz=est.detuning_Hz-detuning,
            tracking_sigma_Hz=est.sigma_Hz,tracking_covered=est.lower_Hz<=detuning<=est.upper_Hz)
        rows.append(row)
    return pd.DataFrame(rows)


def optical_model_comparison(c=ClockExperiment(),p=Physics()):
    """Sequential transient/mean-count comparison; no reset between side probes."""
    f0=float(thermal_parameters(297,p)[0]+p.gamma_e_Hz_G*c.optical.Bz_G)
    full=OpticalClockPlant(c.optical,c.rates,f0,c.reference_offset_Hz,'lindblad',p)
    rate=OpticalClockPlant(c.optical,c.rates,f0,c.reference_offset_Hz,'rate',p)
    rows=[]
    for step,(offset,on,dt) in enumerate([(0.,False,50e-6),(250e3,True,.001),(-250e3,True,.001),(250e3,True,.01),(-250e3,True,.01)]):
        a=full.step(f0+offset,dt,on);b=rate.step(f0+offset,dt,on)
        error=c.detector.centers*c.detector.efficiency*(b-a)
        photons=c.detector.centers*c.detector.efficiency*a+(c.detector.background_s+c.detector.dark_s)*dt
        rows.append(dict(states=c.optical.states,step=step,probe_offset_Hz=offset,gate_s=dt,microwave_on=on,
            lindblad_emitted_per_center=a,rate_emitted_per_center=b,detected_mean_difference=error,
            poisson_standard_deviation=np.sqrt(photons),mean_difference_in_count_sigma=error/np.sqrt(photons)))
    return pd.DataFrame(rows)


def counting_cases(c=ClockExperiment(),p=Physics()):
    f0=float(thermal_parameters(297,p)[0]+p.gamma_e_Hz_G*c.optical.Bz_G)
    plant=OpticalClockPlant(replace(c.optical,states=7),c.rates,f0,0.,'lindblad',p)
    plant.step(f0,1e-3,False)
    rows=[]
    for offset in (-250e3,250e3):
        values=gate_moments(plant,f0+offset,c.gate_s,c.detector.efficiency)
        pair=adjacent_gate_covariance(plant,f0+offset,f0-offset,c.gate_s,c.detector.efficiency)
        rows.append(dict(probe_offset_Hz=offset,gate_s=c.gate_s,efficiency=c.detector.efficiency,
            reference_states=7,reference_centers=1,**values,**pair,
            interpretation='Driven quantum-count moments; long clock counts remain an explicitly qualified Poisson approximation'))
    return pd.DataFrame(rows)


def physical_estimator_cases(states=7,trials=40,seed=412,centers=100,efficiency=.01,background_s=1100.,gate_s=.02,
                             experiment=None,physics=Physics()):
    """Estimator line-shape bias/coverage against actual Lindblad optical means."""
    p=physics;base=ClockExperiment() if experiment is None else experiment
    oc=replace(base.optical,states=states)
    f0=float(thermal_parameters(297,p)[0]+p.gamma_e_Hz_G*oc.Bz_G)
    private=replace(p,D0_Hz=p.D0_Hz+base.reference_offset_Hz)
    x=np.linspace(-4e6,4e6,81);rates=[]
    for frequency in f0+x:
        s=build_system(oc,base.rates,private,frequency)
        rates.append(centers*efficiency*float(np.trace(s.emission_operator()@steady_state(s)).real)+background_s)
    rng=np.random.default_rng(seed);rows=[]
    offsets=(0.,) if states==7 else (-abs(p.Apar0_Hz),0.,abs(p.Apar0_Hz))
    # Independent target eigenvalue assignment, used only after count-only estimation.
    s=build_system(oc,base.rates,private,f0);from scipy.optimize import linear_sum_assignment
    a,b=linear_sum_assignment(-abs(s.ground_vectors)**2);b=b[np.argsort(a)];ni=s.ni
    truth=s.ground_energies_Hz[b[ni//2]]-s.ground_energies_Hz[b[ni+ni//2]]-f0
    for trial in range(trials):
        obs=[CountObservation(float(f),gate_s,int(n)) for f,n in zip(x,rng.poisson(np.array(rates)*gate_s))]
        cal=fit_acquisition(obs,offsets,profile=True)
        rows.append(dict(states=states,trial=trial,seed=seed,evaluation_hamiltonian_command_Hz=truth,
            estimated_command_Hz=cal.centre_command_Hz,error_Hz=cal.centre_command_Hz-truth,
            sigma_Hz=cal.centre_sigma_Hz,valid=cal.valid,covered=cal.lower_Hz<=truth<=cal.upper_Hz,
            interpretation='Includes line-shape/line-pulling bias; no oracle bias correction applied'))
    return pd.DataFrame(rows)
