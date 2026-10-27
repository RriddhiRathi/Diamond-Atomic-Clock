"""Exact first/second and adjacent-gate counting moments of the optical Lindblad model."""
import numpy as np
from scipy.linalg import expm


def detected_jump(plant,efficiency):
    if plant.backend!='lindblad' or not 0<=efficiency<=1:raise ValueError('Lindblad plant and efficiency [0,1] required.')
    d=plant.d;j=np.zeros((d*d,d*d),complex)
    for name,l in plant.system.jumps:
        if name.startswith('radiative'):j+=efficiency*np.kron(l.conj(),l)
    return j[np.ix_(plant.indices,plant.indices)]


def gate_moments(plant,frequency_Hz,duration_s,efficiency=.01,microwave_on=True):
    if duration_s<=0:raise ValueError('Positive count gate required.')
    l=plant.generator(frequency_Hz,microwave_on);j=detected_jump(plant,efficiency);n=len(l)
    a=np.kron(np.eye(3),l);a[n:2*n,:n]=j;a[2*n:3*n,n:2*n]=2*j
    v=expm(a*duration_s)@np.r_[plant.state,np.zeros(2*n)]
    mean=float(v[n+np.array(plant.trace_indices)].sum().real)
    factorial=float(v[2*n+np.array(plant.trace_indices)].sum().real)
    return dict(mean=mean,variance=factorial+mean-mean**2,fano=(factorial+mean-mean**2)/mean if mean else np.nan)


def adjacent_gate_covariance(plant,first_Hz,second_Hz,duration_s,efficiency=.01):
    j=detected_jump(plant,efficiency);n=len(j)
    def operator(freq,gate):
        l=plant.generator(freq);a=np.kron(np.eye(4),l)
        if gate==0:a[n:2*n,:n]=j;a[3*n:4*n,2*n:3*n]=j
        else:a[2*n:3*n,:n]=j;a[3*n:4*n,n:2*n]=j
        return a
    v=np.r_[plant.state,np.zeros(3*n)]
    v=expm(operator(first_Hz,0)*duration_s)@v
    v=expm(operator(second_Hz,1)*duration_s)@v
    tr=np.array(plant.trace_indices)
    a=float(v[n+tr].sum().real);b=float(v[2*n+tr].sum().real)
    ab=float(v[3*n+tr].sum().real)
    return dict(first_mean=a,second_mean=b,covariance=ab-a*b)
