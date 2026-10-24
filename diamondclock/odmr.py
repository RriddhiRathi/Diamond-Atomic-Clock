"""Four-orientation 14NV spectroscopy, H/h in Hz. See docs/ODMR_METHODS.md.

Adapted in functionality from the intern MATLAB transcript in legacy/matlab/;
this is a corrected Python integration, not authorship of that original code.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .physics import Physics, S, I, DZ, hamiltonian, parameter, parameter_rows

_R6, _R2, _R3 = np.sqrt(6), np.sqrt(2), np.sqrt(3)
# Rows are local x,y,z in the lab cubic axes; v_NV = R @ v_lab.
ROTATIONS = np.array([
    [[-1/_R6,1/_R6,-2/_R6],[-1/_R2,-1/_R2,0],[-1/_R3,1/_R3,1/_R3]],
    [[1/_R6,1/_R6,2/_R6],[1/_R2,-1/_R2,0],[1/_R3,1/_R3,-1/_R3]],
    [[-1/_R6,-1/_R6,2/_R6],[-1/_R2,1/_R2,0],[-1/_R3,-1/_R3,-1/_R3]],
    [[1/_R6,-1/_R6,-2/_R6],[1/_R2,1/_R2,0],[1/_R3,-1/_R3,1/_R3]],
])
P0 = np.eye(9) - DZ


@dataclass(frozen=True)
class Stark:
    # Converted from Hz/(V/cm) to Hz/(V/m), factor 1/100.
    d_parallel_Hz_m_V: float = parameter(.0035, 'Hz/(V/m)', 'D2012',
        'Sec. II B, text preceding Eq. (17), p. 205203-6', '0.35(2) Hz cm/V; converted by 1/100')
    d_perp_Hz_m_V: float = parameter(.17, 'Hz/(V/m)', 'D2012',
        'Sec. II B, discussion after Eq. (16), p. 205203-6', '17(3) Hz cm/V; converted by 1/100')


@dataclass(frozen=True)
class ODMRConfig:
    temperature_K: float = 297.
    B_lab_G: tuple = (0., 0., 18.)
    E_lab_V_m: tuple = (0., 0., 0.)
    microwave_lab: tuple = (1., 0., 0.)  # linear polarization direction, not calibrated power
    weights: tuple = (.25, .25, .25, .25)
    linewidth_Hz: float = 300_000.
    contrast: float = .03  # phenomenological bright-to-dark budget, not a prediction
    start_Hz: float = 2.75e9
    stop_Hz: float = 3.0e9
    points: int = 3001

    def validate(self, p=Physics()):
        for field in ('B_lab_G', 'E_lab_V_m', 'microwave_lab'):
            vector(getattr(self, field))
        if np.linalg.norm(self.B_lab_G) > 650:
            raise ValueError('Spectroscopy field magnitude must not exceed 650 G.')
        if abs(self.temperature_K-p.T0_K)>5 or not np.isfinite(self.temperature_K):
            raise ValueError('Temperature must remain within the existing local +/-5 K expansion.')
        w=np.asarray(self.weights, float)
        if w.shape!=(4,) or not np.all(np.isfinite(w)) or np.any(w<0) or w.sum()<=0:
            raise ValueError('Four finite nonnegative orientation weights with positive sum are required.')
        if np.linalg.norm(self.microwave_lab)==0:
            raise ValueError('Microwave polarization cannot be zero.')
        if not all(np.isfinite(x) for x in (self.linewidth_Hz,self.contrast,self.start_Hz,self.stop_Hz)):
            raise ValueError('Spectroscopy parameters must be finite.')
        if self.linewidth_Hz<=0 or not 0<=self.contrast<=.2:
            raise ValueError('Positive FWHM and contrast between 0 and 0.2 are required.')
        if not isinstance(self.points,int) or not 101<=self.points<=20001:
            raise ValueError('Use 101..20001 frequency points.')
        if not 0<self.start_Hz<self.stop_Hz:
            raise ValueError('The positive frequency window must be increasing.')


def vector(value):
    v=np.asarray(value,float)
    if v.shape!=(3,) or not np.all(np.isfinite(v)):
        raise ValueError('Expected a finite Cartesian vector of length three.')
    return v


def spherical(magnitude, theta_deg, phi_deg):
    """Polar theta from +z, azimuth phi from +x toward +y, degrees."""
    if not np.all(np.isfinite([magnitude,theta_deg,phi_deg])) or magnitude<0:
        raise ValueError('Finite angles and nonnegative magnitude are required.')
    t,f=np.deg2rad([theta_deg,phi_deg])
    return magnitude*np.array([np.sin(t)*np.cos(f),np.sin(t)*np.sin(f),np.cos(t)])


def transform(v, orientation, inverse=False):
    if not isinstance(orientation,(int,np.integer)) or not 0<=orientation<4:
        raise ValueError('Orientation index must be 0..3.')
    r=ROTATIONS[orientation]
    return (r.T if inverse else r)@vector(v)


def spectroscopy_hamiltonian(T_K, B_NV_G, E_NV_V_m=(0.,0.,0.), p=Physics(), stark=Stark()):
    """Existing 9x9 model + By Zeeman + D2012 Eq. (24) Stark terms.

    Explicit local transverse-axis convention: -Ex(Sx^2-Sy^2)+Ey{Sx,Sy}.
    No additional strain tensor, excited states, or Stark shifts of hyperfine terms.
    """
    b,e=vector(B_NV_G),vector(E_NV_V_m)
    if not np.isfinite(T_K) or abs(T_K-p.T0_K)>5:
        raise ValueError('Temperature outside local +/-5 K model.')
    if not all(np.isfinite(x) and x>=0 for x in (stark.d_parallel_Hz_m_V,stark.d_perp_Hz_m_V)):
        raise ValueError('Stark coefficients must be finite and nonnegative.')
    he=(stark.d_parallel_Hz_m_V*e[2]*DZ
        -stark.d_perp_Hz_m_V*e[0]*(S[0]@S[0]-S[1]@S[1])
        +stark.d_perp_Hz_m_V*e[1]*(S[0]@S[1]+S[1]@S[0]))
    if np.linalg.norm(he,2)> .01*p.D0_Hz:
        raise ValueError('Electric perturbation exceeds 1% of D; outside supported weak-Stark model.')
    return hamiltonian(T_K,b[2],b[0],p)+b[1]*(p.gamma_e_Hz_G*S[1]-p.gamma_n_Hz_G*I[1])+he


def microwave_operator(polarization, p=Physics()):
    v=vector(polarization)
    norm=np.linalg.norm(v)
    if norm==0:
        raise ValueError('Microwave polarization cannot be zero.')
    return sum(v[k]/norm*(S[k]-p.gamma_n_Hz_G/p.gamma_e_Hz_G*I[k]) for k in range(3))


def _groups(energies, tolerance_Hz=1e-5):
    # Group exact/numerically degenerate manifolds; avoid basis-dependent line weights.
    return np.split(np.arange(len(energies)),np.where(np.diff(energies)>tolerance_Hz)[0]+1)


def transition_table(h, polarization, p=Physics()):
    """Manifold-summed |<j|M|i>|^2, dimensionless, with explicit ODMR proxy.

    Within each degenerate manifold assume uniform population and brightness equal
    to its average m_s=0 character. Population ~ brightness/3. Proxy dip weight is
    strength*(brightness_i-brightness_j)^2/3. This is NOT an optical rate model.
    """
    energies, states=np.linalg.eigh(h)
    m=microwave_operator(polarization,p)
    rows=[]
    groups=_groups(energies)
    for ia,a in enumerate(groups):
        va=states[:,a]
        bright_a=float(np.trace(va.conj().T@P0@va).real/len(a))
        for b in groups[ia+1:]:
            vb=states[:,b]
            bright_b=float(np.trace(vb.conj().T@P0@vb).real/len(b))
            strength=float(np.linalg.norm(vb.conj().T@m@va,'fro')**2)
            rows.append(dict(initial_rank=int(a[0]),final_rank=int(b[0]),
                initial_degeneracy=len(a),final_degeneracy=len(b),
                frequency_Hz=float(energies[b].mean()-energies[a].mean()),
                strength=strength,bright_initial=bright_a,bright_final=bright_b,
                dip_weight=strength*(bright_a-bright_b)**2/3))
    return pd.DataFrame(rows,columns=['initial_rank','final_rank','initial_degeneracy',
        'final_degeneracy','frequency_Hz','strength','bright_initial','bright_final','dip_weight'])


def lorentzian(frequency_Hz, centre_Hz, fwhm_Hz):
    if not np.isfinite(fwhm_Hz) or fwhm_Hz<=0:
        raise ValueError('Lorentzian FWHM must be positive.')
    return 1/(1+4*((np.asarray(frequency_Hz)-centre_Hz)/fwhm_Hz)**2)


def spectrum(c=ODMRConfig(), p=Physics(), stark=Stark()):
    c.validate(p)
    frequency=np.linspace(c.start_Hz,c.stop_Hz,c.points)
    data={'frequency_Hz':frequency}
    lines=[]; levels=[]
    for k in range(4):
        b,e,m=(transform(x,k) for x in (c.B_lab_G,c.E_lab_V_m,c.microwave_lab))
        h=spectroscopy_hamiltonian(c.temperature_K,b,e,p,stark)
        table=transition_table(h,m,p)
        table['orientation']=k+1
        lines.append(table)
        response=np.zeros(c.points)
        for line in table.itertuples():
            response+=line.dip_weight*lorentzian(frequency,line.frequency_Hz,c.linewidth_Hz)
        data[f'NV{k+1}_fluorescence']=1-c.contrast*response
        energy=np.linalg.eigvalsh(h)
        for rank,value in enumerate(energy):
            levels.append(dict(orientation=k+1,energy_rank=rank,energy_Hz=float(value-energy[0])))
    weights=np.asarray(c.weights)/sum(c.weights)
    data['combined_fluorescence']=sum(weights[k]*data[f'NV{k+1}_fluorescence'] for k in range(4))
    return pd.DataFrame(data),pd.concat(lines,ignore_index=True),pd.DataFrame(levels)


def level_sweep(c, maximum_G=None, points=101, p=Physics(), stark=Stark()):
    """Energy ranks (not tracked spin labels); each orientation uses its own zero."""
    c.validate(p)
    maximum_G=float(maximum_G if maximum_G is not None else max(30,np.linalg.norm(c.B_lab_G)))
    if not 0<maximum_G<=650 or not 2<=points<=501:
        raise ValueError('Use 0 < sweep maximum <=650 G and 2..501 points.')
    direction=vector(c.B_lab_G)
    direction=direction/np.linalg.norm(direction) if np.linalg.norm(direction) else np.array([0.,0.,1.])
    rows=[]
    for field in np.linspace(0,maximum_G,points):
        for k in range(4):
            energy=np.linalg.eigvalsh(spectroscopy_hamiltonian(c.temperature_K,
                transform(field*direction,k),transform(c.E_lab_V_m,k),p,stark))
            for rank,value in enumerate(energy):
                rows.append(dict(field_G=field,orientation=k+1,energy_rank=rank,
                                 energy_Hz=float(value-energy[0])))
    return pd.DataFrame(rows)


def transition_sensitivities(T_K, B_NV_G, polarization=(1.,0.,0.), E_NV_V_m=(0.,0.,0.),p=Physics()):
    """Hellmann-Feynman field gradients. Degenerate pairs explicitly have NaN slopes."""
    h=spectroscopy_hamiltonian(T_K,B_NV_G,E_NV_V_m,p)
    e,v=np.linalg.eigh(h)
    table=transition_table(h,polarization,p)
    for k,label in enumerate(('x','y','z')):
        op=p.gamma_e_Hz_G*S[k]-p.gamma_n_Hz_G*I[k]
        gradient=np.real(np.diag(v.conj().T@op@v))
        table[f'dnu_dB{label}_Hz_G']=[
            gradient[row.final_rank]-gradient[row.initial_rank]
            if row.initial_degeneracy==row.final_degeneracy==1 else np.nan
            for row in table.itertuples()]
    return table


def odmr_parameter_provenance(c=ODMRConfig(),stark=Stark()):
    rows=parameter_rows(stark)
    for row in rows:
        row['implementation']='diamondclock/odmr.py:Stark.'+row['parameter']
    for name,value in c.__dict__.items():
        rows.append(dict(parameter=name,value=value,unit={
            'temperature_K':'K','B_lab_G':'G','E_lab_V_m':'V/m',
            'linewidth_Hz':'Hz','start_Hz':'Hz','stop_Hz':'Hz'}.get(name,'dimensionless'),
            source='MODEL',locator='docs/ODMR_METHODS.md: O1-O5',
            note='Explicit spectroscopy scenario assumption, not a measured apparatus parameter',
            implementation='diamondclock/odmr.py:ODMRConfig.'+name))
    return pd.DataFrame(rows)
