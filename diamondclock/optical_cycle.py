"""Seven-electronic-state cycle, coherent MW, and secular rate benchmark (OPM1-5)."""
from dataclasses import dataclass
import numpy as np
from scipy import sparse
from scipy.linalg import lstsq
from scipy.sparse.linalg import spsolve, expm_multiply
from .physics import Physics, SX, SY, SZ, thermal_parameters
from .optical_parameters import OpticalConfig, OpticalRates


@dataclass
class OpticalSystem:
    h_Hz: np.ndarray  # rotating-frame Hamiltonian, cyclic Hz
    jumps: list  # (name, operator with units sqrt(s^-1))
    ground_energies_Hz: np.ndarray
    ground_vectors: np.ndarray
    ground_hamiltonian_Hz: np.ndarray
    ng: int
    ni: int

    @property
    def dimension(self): return self.h_Hz.shape[0]

    def initial(self):
        r=np.zeros_like(self.h_Hz); r[:self.ng,:self.ng]=np.eye(self.ng)/self.ng
        return r

    def emission_operator(self):
        return sum((l.conj().T@l for name,l in self.jumps if name.startswith('radiative')),np.zeros_like(self.h_Hz))


def _assemble(c,r,p,hg,drive,frequency_Hz):
    """Ground eigenbasis; independent optical channels are an explicit secular model."""
    ng=len(hg); ni=ng//3; d=2*ng+ni
    e,u=np.linalg.eigh(hg)
    # Low-field axial branch assignment; reject ambiguities rather than fabricate labels.
    ms0=np.tile([0.,1.,0.],(ni,1)).T.ravel() if ni==1 else np.repeat([0.,1.,0.],ni)
    bright=np.real(np.diag(u.conj().T@np.diag(ms0)@u))
    if np.any((bright>.01)&(bright<.99)):
        raise ValueError('Ground mixing outside the Phase 3 secular optical scope.')
    q=(bright<.5).astype(float)
    f=float(frequency_Hz) if frequency_Hz is not None else float(thermal_parameters(c.temperature_K,p)[0]+p.gamma_e_Hz_G*c.Bz_G)
    if not np.isfinite(f) or not 1e9 < f < 4e9:
        raise ValueError('Microwave frequency must be finite and in 1..4 GHz.')
    mw=u.conj().T@drive@u
    allowed=q[:,None]!=q[None,:]
    h=np.zeros((d,d),complex)
    h[:ng,:ng]=np.diag(e-f*q)+c.rabi_Hz/2*np.sqrt(2)*mw*allowed
    jumps=[]
    def edge(name,target,origin,rate):
        if rate<=1e-18:return
        l=np.zeros((d,d),complex);l[target,origin]=np.sqrt(rate);jumps.append((name,l))
    # Bare electronic order +1,0,-1; nuclear order +1,0,-1. Each rate is per channel.
    for a in range(ng):
        m=a//ni; nuclear=a%ni
        isc=r.isc_zero_s if m==1 else r.isc_pm_s
        back=r.singlet_zero_s if m==1 else r.singlet_pm_s
        edge('isc',2*ng+nuclear,ng+a,isc)
        for i in range(ng):
            overlap=abs(u[a,i])**2
            edge('pump',ng+a,i,c.pump_s*overlap)
            edge('radiative',i,ng+a,r.radiative_s*overlap)
            edge('singlet_return',i,2*ng+nuclear,back*overlap)
    # Symmetric electron-pair ground relaxation in the bare basis, projected incoherently.
    overlaps=abs(u)**2
    for i in range(ng):
        for j in range(ng):
            if i==j:continue
            rate=0.
            for n in range(ni):
                for a in range(3):
                    for b in range(3):
                        if a!=b:rate+=c.ground_pair_s*overlaps[a*ni+n,i]*overlaps[b*ni+n,j]
            edge('ground_relaxation',j,i,rate)
        edge('pure_dephasing',i,i,c.pure_dephasing_s)
    return OpticalSystem(h,jumps,e,u,hg,ng,ni)


def seven_state(c=OpticalConfig(),r=OpticalRates(),p=Physics(),frequency_Hz=None):
    c.validate();r.validate()
    if c.states!=7:raise ValueError('seven_state requires states=7.')
    d=thermal_parameters(c.temperature_K,p)[0]
    hg=d*(SZ@SZ)+p.gamma_e_Hz_G*c.Bz_G*SZ
    return _assemble(c,r,p,hg,SX,frequency_Hz)


def liouvillian(system):
    """Column-vectorized rho. H/h [Hz] -> H/hbar [rad/s] ONLY here."""
    d=system.dimension; eye=sparse.eye(d,format='csc');h=sparse.csc_matrix(system.h_Hz)
    result=-2j*np.pi*(sparse.kron(eye,h)-sparse.kron(h.T,eye))
    for _,jump in system.jumps:
        l=sparse.csc_matrix(jump);a=l.conj().T@l
        result+=sparse.kron(l.conj(),l)-.5*sparse.kron(eye,a)-.5*sparse.kron(a.T,eye)
    return result.tocsc()


def physical_density(rho,atol=2e-7):
    if not np.all(np.isfinite(rho)) or not np.allclose(rho,rho.conj().T,atol=atol):
        raise ValueError('Nonfinite or non-Hermitian optical density matrix.')
    if abs(np.trace(rho)-1)>atol or np.linalg.eigvalsh(rho).min() < -atol:
        raise ValueError('Optical density matrix violates trace or positivity.')
    return rho


def steady_state(system):
    l=liouvillian(system);d=system.dimension
    a=(l/1e6).tolil();a[0,:]=0;a[0,np.arange(d)*(d+1)]=1
    b=np.zeros(d*d,complex);b[0]=1
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        v=spsolve(a.tocsc(),b)
    invalid=not np.all(np.isfinite(v)) or np.linalg.norm(l@v)>1e-3
    if not invalid:
        try: physical_density(v.reshape((d,d),order='F'))
        except ValueError: invalid=True
    if invalid:
        # Non-unique stationary states (e.g. disconnected nuclear sectors): minimum norm.
        v=lstsq(a.toarray(),b,cond=1e-13)[0]
    rho=v.reshape((d,d),order='F');physical_density(rho)
    if np.linalg.norm(l@v)>1e-2:raise ValueError('Stationary Lindblad residual too large.')
    return rho


def rate_generator(system,include_microwave=True):
    """Population reduction; MW rate from steady optical Bloch coherence (OPM5)."""
    d=system.dimension;k=np.zeros((d,d));out=np.zeros(d)
    for name,l in system.jumps:
        rates=abs(l)**2
        if name=='pure_dephasing':continue
        k+=rates;out+=rates.sum(axis=0)
    np.fill_diagonal(k,0)
    if include_microwave:
        phi=np.zeros(d)
        for name,l in system.jumps:
            if name=='pure_dephasing':phi+=abs(np.diag(l))**2
        for i in range(system.ng):
            for j in range(i):
                omega=4*np.pi*abs(system.h_Hz[i,j])
                gamma=.5*(out[i]+out[j]+phi[i]+phi[j])
                delta=2*np.pi*(system.h_Hz[i,i]-system.h_Hz[j,j]).real
                if omega and gamma:
                    w=omega**2*gamma/(2*(gamma**2+delta**2));k[i,j]+=w;k[j,i]+=w
    np.fill_diagonal(k,-k.sum(axis=0))
    return k


def rate_steady(system):
    k=rate_generator(system);a=k/1e6;a[0,:]=1;b=np.zeros(len(k));b[0]=1
    v=lstsq(a,b,cond=1e-13)[0]
    if v.min() < -1e-7 or abs(v.sum()-1)>1e-7 or np.linalg.norm(k@v)>1e-2:
        raise ValueError('Invalid stationary rate solution.')
    return np.diag(v.astype(complex))


def transient(system,times_s,rho=None):
    times=np.asarray(times_s,float)
    if times.ndim!=1 or len(times)<2 or times[0]!=0 or np.any(np.diff(times)<=0) or not np.allclose(np.diff(times),times[1],rtol=1e-10,atol=1e-18):
        raise ValueError('Transient requires an increasing uniform grid beginning at zero.')
    initial=system.initial() if rho is None else physical_density(np.asarray(rho,complex))
    l=liouvillian(system)
    vectors=expm_multiply(l,initial.ravel(order='F'),start=0,stop=times[-1],num=len(times),traceA=l.diagonal().sum())
    result=np.array([v.reshape(initial.shape,order='F') for v in vectors])
    for item in result:physical_density(item)
    return result


def populations(system,rho):
    p=np.diag(rho).real
    ground=abs(system.ground_vectors)**2@p[:system.ng]
    return dict(ground_zero=float(ground[system.ni:2*system.ni].sum()),
        ground_pm=float(ground.sum()-ground[system.ni:2*system.ni].sum()),
        excited_zero=float(p[system.ng+system.ni:system.ng+2*system.ni].sum()),
        excited_pm=float(p[system.ng:2*system.ng].sum()-p[system.ng+system.ni:system.ng+2*system.ni].sum()),
        singlet=float(p[2*system.ng:].sum()))
