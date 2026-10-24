"""Private optical plant; inference modules must not import this module (CLK1)."""
from dataclasses import replace
import numpy as np
from scipy.linalg import expm
from .physics import Physics, thermal_parameters
from .optical_dynamics import build_system
from .optical_cycle import liouvillian, rate_generator, physical_density, populations


class OpticalClockPlant:
    def __init__(self,optical,rates,nominal_Hz,sample_offset_Hz=0.,backend='lindblad',physics=Physics()):
        optical.validate();rates.validate()
        self.optical=optical;self.rates=rates;self.nominal_Hz=nominal_Hz;self.backend=backend
        private=replace(physics,D0_Hz=physics.D0_Hz+sample_offset_Hz)
        self.system=build_system(optical,rates,private,nominal_Hz)
        self.ng=self.system.ng;self.d=self.system.dimension
        self.q=(np.real(np.diag(self.system.ground_vectors.conj().T@np.diag(np.repeat([0.,1.,0.],self.system.ni))@self.system.ground_vectors))<.5).astype(float)
        self.trace_indices=[i+i*self.ng for i in range(self.ng)]+list(range(self.ng*self.ng,self.ng*self.ng+self.d-self.ng))
        self.indices=[i+j*self.d for j in range(self.ng) for i in range(self.ng)]+[i+i*self.d for i in range(self.ng,self.d)]
        self.emission=np.r_[np.zeros(self.ng*self.ng),np.full(self.ng,rates.radiative_s),np.zeros(self.system.ni)]
        self.matrices={};self.last_normalization_error=0.
        if backend=='lindblad':
            self.state=self.system.initial().ravel(order='F')[self.indices]
            for enabled in (False,True):
                s=build_system(optical if enabled else replace(optical,rabi_Hz=0),rates,private,nominal_Hz)
                full=liouvillian(s).toarray()
                outside=np.setdiff1d(np.arange(self.d**2),self.indices)
                if np.max(abs(full[np.ix_(outside,self.indices)]),initial=0)>1e-9:
                    raise ValueError('Optical support is not a closed Lindblad sector.')
                self.matrices[enabled]=full[np.ix_(self.indices,self.indices)]
            derivative=np.zeros(len(self.indices),complex)
            for j in range(self.ng):
                for i in range(self.ng):derivative[i+j*self.ng]=2j*np.pi*(self.q[i]-self.q[j])
            self.derivative=derivative
        elif backend=='rate':
            self.state=np.diag(self.system.initial()).copy()
            self.emission=np.r_[np.zeros(self.ng),np.full(self.ng,rates.radiative_s),np.zeros(self.system.ni)]
            self.trace_indices=list(range(self.d));self.base_rate=rate_generator(self.system,False)
            out=-np.diag(self.base_rate)
            phi=optical.pure_dephasing_s
            edges=[]
            for i in range(self.ng):
                for j in range(i):
                    omega=4*np.pi*abs(self.system.h_Hz[i,j])
                    if omega>0:edges.append((i,j,omega,.5*(out[i]+out[j])+phi,
                        (self.system.h_Hz[i,i]-self.system.h_Hz[j,j]).real,self.q[i]-self.q[j]))
            self.edges=edges
        else:raise ValueError('Unknown optical backend.')

    def generator(self,frequency_Hz,microwave_on=True):
        delta=float(frequency_Hz-self.nominal_Hz)
        if not np.isfinite(delta) or abs(delta)>20e6:raise ValueError('Probe outside Phase 4 +/-20 MHz model window.')
        if self.backend=='lindblad':return self.matrices[microwave_on]+np.diag(self.derivative*delta)
        k=self.base_rate.copy()
        if microwave_on:
            for i,j,omega,gamma,gap,q in self.edges:
                if gamma:
                    w=omega**2*gamma/(2*(gamma**2+(2*np.pi*(gap-delta*q))**2))
                    k[i,j]+=w;k[j,i]+=w;k[i,i]-=w;k[j,j]-=w
        return k.astype(complex)

    def step(self,frequency_Hz,duration_s,microwave_on=True):
        if duration_s<0 or not np.isfinite(duration_s):raise ValueError('Invalid optical duration.')
        if duration_s==0:return 0.
        l=self.generator(frequency_Hz,microwave_on);n=len(l)
        augmented=np.zeros((n+1,n+1),complex);augmented[:n,:n]=l;augmented[n,:n]=self.emission
        evolved=expm(augmented*duration_s)@np.r_[self.state,0.]
        trace=evolved[self.trace_indices].sum()
        error=abs(trace-1);self.last_normalization_error=max(self.last_normalization_error,float(error))
        if error>2e-7 or abs(evolved[-1].imag)>1e-5 or evolved[-1].real < -1e-6:
            raise ValueError('Optical propagation failed trace/count-integral checks.')
        self.state=evolved[:-1]/trace
        return max(0.,float(evolved[-1].real))

    def density(self):
        if self.backend=='rate':rho=np.diag(self.state)
        else:
            v=np.zeros(self.d*self.d,complex);v[self.indices]=self.state;rho=v.reshape((self.d,self.d),order='F')
        return physical_density(rho)

    def population_summary(self):return populations(self.system,self.density())
