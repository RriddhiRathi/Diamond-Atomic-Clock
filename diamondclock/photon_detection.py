"""Detected counts: number-resolved Lindblad reference and labeled Poisson mode."""
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import expm_multiply
from .optical_cycle import liouvillian, physical_density, rate_generator


def poisson_counts(expected,seed):
    mean=np.asarray(expected,float)
    if np.any(~np.isfinite(mean)) or np.any(mean<0):raise ValueError('Invalid expected counts.')
    return np.random.Generator(np.random.PCG64(seed)).poisson(mean)


def count_distribution(system,rho,gate_s,efficiency=.01):
    """P(n) via d rho_n/dt=(L-J)rho_n+J rho_(n-1); not Poisson sampling.

    Independent spin-resolved radiative channels, ideal detector, one center;
    finite cutoff mass is checked before normalization. Dark/background added separately.
    """
    physical_density(rho)
    if not np.isfinite(gate_s) or not 0<gate_s<=50e-6 or not np.isfinite(efficiency) or not 0<=efficiency<=1:
        raise ValueError('Reference gates: (0,50 us], detection efficiency [0,1].')
    d=system.dimension
    j=sparse.csc_matrix((d*d,d*d),dtype=complex)
    maximum=0.
    for name,l in system.jumps:
        if name.startswith('radiative'):
            a=sparse.csc_matrix(l);j+=efficiency*sparse.kron(a.conj(),a)
            maximum+=l.conj().T@l
    bound=efficiency*max(np.linalg.eigvalsh(maximum))*gate_s
    cutoff=int(np.ceil(bound+10*np.sqrt(bound+1)+12))
    if cutoff>300:raise ValueError('Reference distribution too large; reduce gate or efficiency.')
    diagonal=np.allclose(system.h_Hz,np.diag(np.diag(system.h_Hz)),atol=1e-12) and np.allclose(rho,np.diag(np.diag(rho)),atol=1e-12)
    if diagonal:
        # EXACT invariant diagonal sector of this Lindblad model, not a MW approximation.
        l=sparse.csc_matrix(rate_generator(system,include_microwave=False))
        jr=np.zeros((d,d))
        for name,a in system.jumps:
            if name.startswith('radiative'):jr+=efficiency*abs(a)**2
        j=sparse.csc_matrix(jr);v=np.diag(rho).real;dim=d
        trace_indices=np.arange(d)
    else:
        l=liouvillian(system);v=rho.ravel(order='F');dim=d*d
        trace_indices=np.arange(d)*(d+1)
    generator=sparse.kron(sparse.eye(cutoff+1),l-j)+sparse.kron(sparse.diags(np.ones(cutoff),-1),j)
    initial=np.zeros((cutoff+1)*dim,complex);initial[:dim]=v
    out=expm_multiply(generator*gate_s,initial,traceA=generator.diagonal().sum()*gate_s).reshape(cutoff+1,dim)
    probabilities=out[:,trace_indices].sum(axis=1).real
    if probabilities.min() < -1e-9 or abs(probabilities.sum()-1)>1e-8:
        raise ValueError('Number-resolved cutoff or numerical probability failure.')
    probabilities=np.maximum(probabilities,0);return probabilities/probabilities.sum()


def sample_reference(probabilities,repetitions,seed,background_mean=0.):
    p=np.asarray(probabilities,float)
    if p.ndim!=1 or np.any(p<0) or not np.isclose(p.sum(),1) or repetitions<1 or background_mean<0:
        raise ValueError('Invalid counting distribution, repetitions or background.')
    rng=np.random.Generator(np.random.PCG64(seed))
    return rng.choice(len(p),size=repetitions,p=p)+rng.poisson(background_mean,size=repetitions)
