"""Conditional stochastic model; no apparatus-specific calibration or servo."""
from dataclasses import dataclass, replace
import numpy as np
import pandas as pd
from scipy.signal import lfilter
from .physics import Physics, parameter, calibration, observables, composite_weights
from .stability import overlapping_adev


def assumption(v, unit, note):
    return parameter(v, unit, "MODEL", "docs/METHODOLOGY.md", note)


@dataclass(frozen=True)
class Config:
    n: int = assumption(32768, "samples", "Record length; integer 1024..262144")
    dt_s: float = assumption(1., "s", "Contiguous effective measurement interval")
    seed: int = assumption(20261019, "integer", "NumPy SeedSequence root; independent named component streams")
    Bz_G: float = assumption(475., "G", "Bias inspired by L2026; scenario setting, not a measured apparatus")
    Bx_G: float = assumption(0., "G", "Static misalignment component")
    temp_rms_K: float = assumption(.05, "K", "Stationary OU RMS, not total trace RMS")
    temp_corr_s: float = assumption(300., "s", "OU temperature correlation time")
    temp_sine_K: float = assumption(.1, "K", "Peak environmental temperature cycle amplitude")
    temp_period_s: float = assumption(7200., "s", "Environmental cycle period")
    temp_drift_K_h: float = assumption(.002, "K/h", "Deterministic thermal drift")
    Bz_rms_G: float = assumption(.001, "G", "Stationary axial field OU RMS; 1 G = 100 microtesla")
    Bx_rms_G: float = assumption(.0001, "G", "Stationary transverse field OU RMS")
    B_corr_s: float = assumption(100., "s", "Field OU correlation time")
    electron_readout_Hz: float = assumption(50., "Hz", "Independent per-transition Gaussian sigma at dt=1 s; scales dt^-1/2")
    nuclear_readout_Hz: float = assumption(.03, "Hz", "Independent per-transition Gaussian sigma at dt=1 s; scales dt^-1/2")
    readout_rho: float = assumption(0., "dimensionless", "Correlation of the two transition errors within each pair")
    thermometer_rms_K: float = assumption(.001, "K", "White thermometer sigma at dt=1 s")
    thermometer_delay_s: float = assumption(0., "s", "Delay rounded to nearest sample; startup held at first reading")
    slope_error_pct: float = assumption(1., "%", "Q slope relative calibration error; also external thermometer D-slope error")
    lo_white_adev_1s: float = assumption(1e-9, "fractional", "Residual white FM ADEV at 1 s; no feedback suppression is inferred")
    lo_rw_diffusion: float = assumption(1e-11, "fractional/sqrt(s)", "Random-walk FM step diffusion; starts at zero")
    lo_drift_per_s: float = assumption(0., "fractional/s", "Residual deterministic oscillator frequency drift")

    def validate(self):
        if not isinstance(self.n, int) or not 1024<=self.n<=262144:
            raise ValueError("n must be an integer between 1024 and 262144")
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        for k,v in self.__dict__.items():
            if not np.isfinite(v):
                raise ValueError(f"{k} must be finite")
        if self.dt_s<=0 or min(self.temp_corr_s,self.temp_period_s,self.B_corr_s)<=0:
            raise ValueError("Intervals and correlation times must be positive")
        positive = ['temp_rms_K','temp_sine_K','Bz_rms_G','Bx_rms_G','electron_readout_Hz','nuclear_readout_Hz','thermometer_rms_K','thermometer_delay_s','lo_white_adev_1s','lo_rw_diffusion']
        if any(getattr(self,k)<0 for k in positive) or abs(self.readout_rho)>1:
            raise ValueError("Noise amplitudes must be nonnegative; correlation must be in [-1,1]")
        if not 10<=self.Bz_G<=600 or abs(self.Bx_G)>1:
            raise ValueError("Use 10..600 G axial bias and |Bx| <= 1 G")
        if self.temp_period_s < 10*self.dt_s:
            raise ValueError("Resolve the temperature cycle with at least 10 samples")
        if self.thermometer_delay_s>self.n*self.dt_s/2:
            raise ValueError("Thermometer delay must be less than half the record duration")


METHODS = {
    "single_electron": "Single electronic transition",
    "electron_average": "Electronic transition average",
    "external_thermometer": "External temperature correction",
    "nuclear_average": "Nuclear transition average",
    "composite": "Electronic–nuclear composite",
}


def ou(n, dt, sigma, corr, rng):
    """M5: exact discrete stationary OU recurrence, scenario assumption."""
    a = np.exp(-dt/corr)
    z = rng.normal(size=n)
    noise = sigma*np.sqrt(-np.expm1(-2*dt/corr))*z
    noise[0] = sigma*z[0]
    return lfilter([1.], [1., -a], noise)


def paired_readout(n, sigma, rho, rng):
    z = rng.normal(size=(2,n))
    return sigma*z[0], sigma*(rho*z[0]+np.sqrt(max(0.,1-rho*rho))*z[1])


def simulate(c=Config(), p=Physics()):
    c.validate()
    streams = [np.random.default_rng(s) for s in np.random.SeedSequence(c.seed).spawn(8)]
    t = np.arange(c.n)*c.dt_s
    dT = (ou(c.n,c.dt_s,c.temp_rms_K,c.temp_corr_s,streams[0])
          + c.temp_sine_K*np.sin(2*np.pi*t/c.temp_period_s)+c.temp_drift_K_h*t/3600)
    if np.max(np.abs(dT))>5:
        raise ValueError("Temperature excursion exceeds local +/-5 K model range; shorten record or reduce drift.")
    bz = c.Bz_G+ou(c.n,c.dt_s,c.Bz_rms_G,c.B_corr_s,streams[1])
    bx = c.Bx_G+ou(c.n,c.dt_s,c.Bx_rms_G,c.B_corr_s,streams[2])
    if np.min(bz)<5 or np.max(bz)>650 or np.max(np.abs(bx))>2:
        raise ValueError("Field excursion outside supported tracking range")
    cal = calibration(c.Bz_G,c.Bx_G,p)
    f = observables(p.T0_K+dT,bz,bx,p,cal['reference'])
    er1,er2 = paired_readout(c.n,c.electron_readout_Hz/np.sqrt(c.dt_s),c.readout_rho,streams[3])
    nr1,nr2 = paired_readout(c.n,c.nuclear_readout_Hz/np.sqrt(c.dt_s),c.readout_rho,streams[4])
    lo_white = streams[5].normal(0,c.lo_white_adev_1s/np.sqrt(c.dt_s),c.n)
    # First random-walk sample is zero. Increments have sigma=q*sqrt(dt).
    lo_rw = np.r_[0.,np.cumsum(streams[6].normal(0,c.lo_rw_diffusion*np.sqrt(c.dt_s),c.n-1))]
    lo = lo_white+lo_rw+c.lo_drift_per_s*t
    nom = cal['nominal_Hz']
    # Work with frequency differences before adding readout, to avoid cancellation.
    signal = (f-nom)/nom
    y_single = signal[:,0]+er1/nom[0]
    yD = signal[:,4]+(er1+er2)/(2*nom[4])
    yQ = signal[:,5]-(nr1+nr2)/(2*nom[5])
    Tread = dT+streams[7].normal(0,c.thermometer_rms_K/np.sqrt(c.dt_s),c.n)
    lag = int(np.floor(c.thermometer_delay_s/c.dt_s+.5))
    if lag:
        Tread = np.r_[np.repeat(Tread[0],lag),Tread[:-lag]]
    lamD,lamQ = cal['lambda_per_K'][[4,5]]
    lamQ_est = lamQ*(1+c.slope_error_pct/100)
    wD,wQ = composite_weights(lamD,lamQ_est)
    y_external = yD-lamD*(1+c.slope_error_pct/100)*Tread
    ys = dict(single_electron=y_single+lo,electron_average=yD+lo,
              external_thermometer=y_external+lo,nuclear_average=yQ+lo,composite=wD*yD+wQ*yQ+lo)
    trace = pd.DataFrame(dict(time_s=t,temperature_K=p.T0_K+dT,Bz_G=bz,Bx_G=bx,
                              thermometer_delta_K=Tread,lo_white_y=lo_white,lo_random_walk_y=lo_rw,lo_total_y=lo))
    for i,k in enumerate(['f_plus_Hz','f_minus_Hz','f1_Hz','f2_Hz','D_observed_Hz','Q_observed_Hz']):
        trace[k]=f[:,i]
    for key,y in ys.items():
        trace['y_'+key]=y
    stability = []
    for key,y in ys.items():
        a=overlapping_adev(y,c.dt_s)
        a['method']=key
        a['data_kind']='SIMULATION'
        stability.append(a)
    diagnostics = dict(nominal_Hz=nom.tolist(),slope_Hz_K=cal['slope_Hz_K'].tolist(),
                       lambda_per_K=cal['lambda_per_K'].tolist(),wD=wD,wQ=wQ,
                       thermal_sensitivity_composite_per_K=wD*lamD+wQ*lamQ,
                       actual_thermometer_delay_s=lag*c.dt_s,
                       peak_temperature_excursion_K=float(np.max(np.abs(dT))))
    return trace,pd.concat(stability,ignore_index=True),diagnostics


def ensemble(c=Config(), count=20, p=Physics()):
    """M6: 5th/50th/95th ensemble quantiles, NOT experimental confidence limits."""
    if not 3<=count<=100:
        raise ValueError("Use 3..100 independent realizations")
    frames=[]
    children=np.random.SeedSequence(c.seed).spawn(count)
    for i,child in enumerate(children):
        seed=int(child.generate_state(1)[0])
        _,a,_=simulate(replace(c,seed=seed),p)
        a['realization']=i
        a['seed']=seed
        frames.append(a)
    raw=pd.concat(frames,ignore_index=True)
    q=raw.groupby(['method','tau_s']).adev.quantile([.05,.5,.95]).unstack().reset_index()
    q.columns=['method','tau_s','p05','median','p95']
    q['realizations']=count
    q['interval_kind']='MODEL_ENSEMBLE_QUANTILES'
    return raw,q
