"""Count-only Poisson inference. Fits may fail; no simulator or plant imports."""
import numpy as np
from scipy.optimize import least_squares, minimize_scalar, brentq
from .count_observations import Calibration, FrequencyEstimate


def _arrays(observations):
    if not observations:raise ValueError('No photon observations.')
    return (np.array([o.probe_offset_Hz for o in observations])/1e6,
            np.array([o.nominal_gate_s for o in observations]),
            np.array([o.detected_counts for o in observations],float),
            np.array([o.microwave_on for o in observations],bool))


def dip_profile(x,log_width,fractions,offsets_MHz):
    width=np.exp(log_width)
    return np.sum(np.asarray(fractions)[:,None]/(1+4*((np.asarray(x)[None,:]-np.asarray(offsets_MHz)[:,None])/width)**2),axis=0)


def _deviance(n,mu):
    mu=np.maximum(mu,1e-200)
    term=mu-n
    positive=n>0
    term[positive]+=n[positive]*np.log(n[positive]/mu[positive])
    return np.maximum(term,0.)


def fit_acquisition(observations,offsets_Hz=(0.,),profile=True):
    x,t,n,on=_arrays(observations);offsets=np.asarray(offsets_Hz)/1e6
    if len(x)<10 or not np.any(on):raise ValueError('Acquisition requires at least 10 probe observations.')
    lo,hi=float(x.min()-offsets.min()),float(x.max()-offsets.max())
    if lo>=hi:raise ValueError('Acquisition window must cover the declared spectral pattern.')
    beta=max(1.,float(np.quantile(n/t,.8)))
    lower=np.r_[lo,np.log(.04),np.log(1e-3),np.zeros(len(offsets))]
    upper=np.r_[hi,np.log(2.),np.log(1e13),np.full(len(offsets),.25)]
    def means(z):
        v=np.ones(len(x));v[on]-=dip_profile(x[on]-z[0],z[1],z[3:],offsets)
        return t*np.exp(z[2])*v
    def residual(z):
        mu=means(z)
        return np.sign(mu-n)*np.sqrt(2*_deviance(n,mu))
    solutions=[]
    for centre in np.linspace(lo+(hi-lo)*.001,hi-(hi-lo)*.001,13):
        start=np.r_[centre,np.log(.65),np.log(beta),np.full(len(offsets),.06)]
        opt=least_squares(residual,start,bounds=(lower,upper),max_nfev=200,ftol=1e-9,xtol=1e-9,gtol=1e-8)
        solutions.append(opt)
    best=min(solutions,key=lambda z:z.cost);z=best.x
    # Expected Poisson Fisher information, including fitted nuisance parameters.
    derivative=[]
    for j in range(len(z)):
        step=1e-5;delta=np.zeros(len(z));delta[j]=step
        derivative.append((means(z+delta)-means(z-delta))/(2*step))
    derivative=np.array(derivative).T;mu=means(z)
    fisher=derivative.T@(derivative/mu[:,None])
    cov=np.linalg.pinv(fisher,rcond=1e-12)
    sigma=float(np.sqrt(max(cov[0,0],0)))
    flat=t*n.sum()/t.sum()
    ratio=2*(float(_deviance(n,flat).sum())-best.cost)
    ambiguity=any(abs(o.x[0]-z[0])>.35 and o.cost-best.cost<2 for o in solutions)
    reason='ok'
    if n.sum()<100 or ratio<25 or max(z[3:])<.003:reason='insufficient_count_contrast'
    elif ambiguity:reason='ambiguous_resonance'
    elif not best.success or not np.isfinite(sigma) or sigma<=0 or sigma>.3*np.exp(z[1]):reason='unidentified_frequency'
    elif min(z[0]-lo,hi-z[0])<.01:reason='scan_boundary'
    ci=[z[0]-1.96*sigma,z[0]+1.96*sigma]
    if profile and reason=='ok':
        def pnll(centre):
            def fun(nuisance):return residual(np.r_[centre,nuisance])
            opt=least_squares(fun,z[1:],bounds=(lower[1:],upper[1:]),max_nfev=150)
            return opt.cost-best.cost-1.920729410347062
        try:
            ci=[brentq(pnll,lo,z[0],xtol=1e-7),brentq(pnll,z[0],hi,xtol=1e-7)]
        except ValueError:reason='unbounded_profile_interval'
    return Calibration(float(z[0]*1e6),float(np.exp(z[1])*1e6),float(np.exp(z[2])),
        tuple(z[3:]),tuple(float(v) for v in offsets_Hz),tuple(tuple(float(v) for v in row) for row in cov),
        sigma*1e6,ci[0]*1e6,ci[1]*1e6,reason=='ok',reason,ratio)


def estimate_detuning(observations,calibration,capture_Hz=450e3):
    """Profile baseline; propagate independent calibration shape covariance to first order.

    Profile count-only endpoints and first-order total 95% intervals are both returned.
    Their empirical coverage must be assessed; neither is guaranteed at sparse counts.
    """
    x,t,n,on=_arrays(observations);c=calibration;cap=capture_Hz/1e6
    invalid=lambda why:FrequencyEstimate(0.,float('inf'),-float('inf'),float('inf'),
        -float('inf'),float('inf'),False,why,0.)
    if not c.valid:return invalid('invalid_calibration')
    if n.sum()<20 or not np.any(~on) or not np.any(on):return invalid('insufficient_observations')
    shape=np.r_[np.log(c.width_Hz/1e6),c.fractions];offsets=np.asarray(c.offsets_Hz)/1e6
    def evaluate(e,sh=shape):
        v=np.ones(len(x));v[on]-=dip_profile(x[on]+e,sh[0],sh[1:],offsets)
        if np.min(v)<=0:return 1e90,0.
        beta=n.sum()/np.sum(t*v)
        return float(_deviance(n,t*beta*v).sum()),float(beta)
    grid=np.linspace(-cap,cap,41);values=[evaluate(v)[0] for v in grid]
    idx=int(np.argmin(values));left=grid[max(idx-1,0)];right=grid[min(idx+1,len(grid)-1)]
    if left==right:return invalid('flat_error_signal')
    opt=minimize_scalar(lambda e:evaluate(e)[0],bounds=(left,right),method='bounded',options={'xatol':1e-9})
    e=float(opt.x);cost,beta=evaluate(e)
    if abs(e)>.97*cap:return invalid('capture_boundary')
    try:
        low=brentq(lambda q:evaluate(q)[0]-cost-1.920729410347062,-cap,e,xtol=1e-8)
        high=brentq(lambda q:evaluate(q)[0]-cost-1.920729410347062,e,cap,xtol=1e-8)
    except ValueError:return invalid('unbounded_frequency_interval')
    h=2e-4;curvature=(evaluate(e+h)[0]-2*cost+evaluate(e-h)[0])/h**2
    if curvature<=0:return invalid('nonpositive_information')
    sensitivities=[]
    for j in range(len(shape)):
        sh=shape.copy();step=1e-5;sh[j]+=step
        plus=(evaluate(e+h,sh)[0]-evaluate(e-h,sh)[0])/(2*h)
        sh[j]-=2*step
        minus=(evaluate(e+h,sh)[0]-evaluate(e-h,sh)[0])/(2*h)
        sensitivities.append(-(plus-minus)/(2*step)/curvature)
    indices=[1]+list(range(3,3+len(c.fractions)))
    covariance=np.asarray(c.covariance)[np.ix_(indices,indices)]
    shape_variance=max(0.,float(np.array(sensitivities)@covariance@np.array(sensitivities)))
    sigma=np.sqrt(1/curvature+shape_variance)
    return FrequencyEstimate(e*1e6,sigma*1e6,(e-1.96*sigma)*1e6,(e+1.96*sigma)*1e6,
                             low*1e6,high*1e6,True,'ok',beta)
