"""Reproducible optical measurements; no frequency estimator or clock servo."""
from dataclasses import replace
import numpy as np
import pandas as pd
from .physics import Physics, thermal_parameters
from .optical_parameters import OpticalExperiment
from .optical_dynamics import build_system
from .optical_cycle import steady_state, rate_steady, populations, transient
from .photon_detection import poisson_counts


def cw_scan(experiment=OpticalExperiment(),p=Physics()):
    experiment.validate();c=experiment.optical;det=experiment.detector
    solve=steady_state if experiment.backend=='lindblad' else rate_steady
    centre=thermal_parameters(c.temperature_K,p)[0]+p.gamma_e_Hz_G*c.Bz_G
    frequencies=np.linspace(centre-experiment.span_Hz,centre+experiment.span_Hz,experiment.points)
    off=build_system(replace(c,rabi_Hz=0),experiment.rates,p,centre)
    rho_off=solve(off)
    rows=[];contrasts=[]
    for index,f in enumerate(frequencies):
        on=build_system(c,experiment.rates,p,f);rho_on=solve(on)
        pair=[];emission=[]
        for j,(label,system,rho) in enumerate([('off',off,rho_off),('on',on,rho_on)]):
            rate=max(0.,float(np.trace(system.emission_operator()@rho).real))
            mean=(det.centers*det.efficiency*rate+det.background_s+det.dark_s)*experiment.dwell_s
            # Independent deterministic streams identified by row, rather than hidden RNG state.
            stream=index*2+j
            seed=np.random.SeedSequence([experiment.seed,stream]).generate_state(1)[0].item()
            n=int(poisson_counts(mean,seed))
            row=dict(data_kind='SIMULATION',states=c.states,backend=experiment.backend,
                microwave_frequency_Hz=float(f),microwave=label,frequency_index=index,
                acquisition_start_s=stream*experiment.dwell_s,gate_s=experiment.dwell_s,
                expected_counts=mean,detected_counts=n,emitted_per_center_s=rate,
                seed=experiment.seed,stream=stream,stream_seed=seed,
                count_model='poisson_approximation',preparation='stationary_reset_each_gate; preparation overhead excluded',
                **populations(system,rho))
            row.update({f'population_{k:02d}':float(v) for k,v in enumerate(np.diag(rho).real)})
            rows.append(row);pair.append((mean,n));emission.append(rate)
        contrasts.append(dict(microwave_frequency_Hz=float(f),
            expected_detected_contrast=1-pair[1][0]/pair[0][0] if pair[0][0]>0 else np.nan,
            expected_intrinsic_contrast=1-emission[1]/emission[0] if emission[0]>0 else np.nan,
            sampled_contrast=1-pair[1][1]/pair[0][1] if pair[0][1]>0 else np.nan,
            sampled_contrast_defined=pair[0][1]>0))
    return pd.DataFrame(rows),pd.DataFrame(contrasts)


def optical_transient(c,rates,p=Physics()):
    # Pump-only initialization from completely mixed ground populations.
    system=build_system(replace(c,rabi_Hz=0),rates,p)
    times=np.linspace(0,5e-6,101)
    density=transient(system,times)
    emission=system.emission_operator()
    rows=[dict(time_s=t,states=c.states,emitted_per_center_s=float(np.trace(emission@rho).real),
               **populations(system,rho)) for t,rho in zip(times,density)]
    return pd.DataFrame(rows)
