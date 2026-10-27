"""Band-limited discrete oscillator; coherent phase and interval frequency (CLK3)."""
from dataclasses import dataclass,asdict
import numpy as np


@dataclass(frozen=True)
class OscillatorConfig:
    offset_Hz: float = 150e3
    drift_Hz_s: float = 10e3
    white_fm_Hz_at_1s: float = 300.
    random_walk_Hz_sqrt_s: float = 100.
    phase_noise_rad: float = .02

    def validate(self):
        if not all(np.isfinite(v) for v in asdict(self).values()):raise ValueError('Nonfinite oscillator parameter.')
        if min(self.white_fm_Hz_at_1s,self.random_walk_Hz_sqrt_s,self.phase_noise_rad)<0:
            raise ValueError('Noise magnitudes cannot be negative.')


def free_frequency(c,dt_s,seconds,seed):
    c.validate()
    if not np.isfinite(dt_s) or dt_s<=0 or not np.isfinite(seconds) or seconds<=dt_s:
        raise ValueError('Positive oscillator interval and duration are required.')
    count=int(np.ceil(seconds/dt_s));streams=[np.random.default_rng(v) for v in np.random.SeedSequence(seed).spawn(3)]
    t=(np.arange(count)+.5)*dt_s
    white=streams[0].normal(0,c.white_fm_Hz_at_1s/np.sqrt(dt_s),count)
    walk=np.r_[0.,np.cumsum(streams[1].normal(0,c.random_walk_Hz_sqrt_s*np.sqrt(dt_s),count-1))]
    pm=streams[2].normal(0,c.phase_noise_rad,count+1)
    # Linearly interpolated white phase nodes: continuous phase, finite numerical band.
    phase_frequency=np.diff(pm)/(2*np.pi*dt_s)
    return c.offset_Hz+c.drift_Hz_s*t+white+walk+phase_frequency


def phase_and_time(frequency_deviation_Hz,dt_s,nominal_Hz):
    if nominal_Hz<=0 or dt_s<=0:raise ValueError('Positive nominal frequency and interval required.')
    f=np.asarray(frequency_deviation_Hz,float)
    if f.ndim!=1 or not np.all(np.isfinite(f)):raise ValueError('Finite 1D output frequency required.')
    phase=np.r_[0.,2*np.pi*np.cumsum(f*dt_s)]
    return phase,phase/(2*np.pi*nominal_Hz)
