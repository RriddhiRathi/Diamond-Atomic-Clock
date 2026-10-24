"""Opt-in spectroscopy-informed readout scenario; original engine is unchanged."""
from dataclasses import dataclass, replace
import numpy as np
import pandas as pd
from .physics import Physics, calibration
from .simulation import Config, simulate
from .odmr import spectroscopy_hamiltonian, transition_table


@dataclass(frozen=True)
class ReadoutScenario:
    linewidth_Hz: float = 300_000.
    line_contrast: float = .03  # contrast of EACH resolved addressed line, user assumption
    photon_rate_per_s: float = 1e6  # rate during acquisition, before duty factor
    duty_fraction: float = 1.

    def validate(self):
        if not all(np.isfinite(v) for v in self.__dict__.values()):
            raise ValueError('Readout scenario parameters must be finite.')
        if self.linewidth_Hz<=0 or self.photon_rate_per_s<=0:
            raise ValueError('Positive linewidth and photon rate are required.')
        if not 0<self.line_contrast<=.1 or not 0<self.duty_fraction<=1:
            raise ValueError('Use low line contrast (0,0.1] and duty fraction (0,1].')


def readout_eta(s=ReadoutScenario()):
    """DRE2011 Eq. (3): Hz sqrt(s) per line; half the live time for each line.

    Low-contrast, ideal maximum-slope detection of a resolved Lorentzian. No
    frequency scan, baseline-reference overhead, technical noise, or servo model.
    """
    s.validate()
    return (4/(3*np.sqrt(3))*s.linewidth_Hz /
            (s.line_contrast*np.sqrt(s.photon_rate_per_s*s.duty_fraction/2)))


def resolved_clock_readout(c=Config(), s=ReadoutScenario(), p=Physics()):
    c.validate();s.validate()
    if c.readout_rho!=0:
        raise ValueError('Ideal independent photon readout requires existing paired correlation = 0.')
    cal=calibration(c.Bz_G,c.Bx_G,p)
    table=transition_table(spectroscopy_hamiltonian(p.T0_K,(c.Bx_G,0,c.Bz_G),p=p),(1,0,0),p)
    active=table[(table.frequency_Hz>1e8)&(table.dip_weight>1e-5)]
    checks=[]
    for name,target in zip(('f_plus','f_minus'),cal['nominal_Hz'][:2]):
        if len(active)<2:
            raise ValueError('Cannot verify isolation of the clock resonance.')
        distances=np.abs(active.frequency_Hz.to_numpy()-target)
        idx=int(np.argmin(distances))
        if distances[idx]>1:
            raise ValueError('Clock resonance cannot be identified in the spectroscopy model.')
        nearest=float(np.min(np.delete(distances,idx)))
        if nearest<5*s.linewidth_Hz:
            raise ValueError('Clock line is not isolated by five FWHM from other active lines; reduce linewidth.')
        checks.append(dict(line=name,frequency_Hz=float(target),nearest_other_line_Hz=nearest))
    eta=readout_eta(s)
    return replace(c,electron_readout_Hz=eta),dict(
        per_line_sigma_at_1s_Hz=eta,original_per_line_sigma_at_1s_Hz=c.electron_readout_Hz,
        isolation_checks=checks,clock_frame_B_G=[c.Bx_G,0,c.Bz_G],electric_field_V_m=[0,0,0],
        geometry='Single NV clock frame; not a lock to the four-orientation ensemble minimum',
        changed_fields=['electron_readout_Hz'],
        assumptions='DRE2011 Eq. (3), low contrast, two resolved Lorentzian lines, half live time per line, ideal maximum-slope independent photon detection. Line contrast supplied, not inferred from spectrum proxy. No claim about apparatus accuracy.')


def compare_stability(c=Config(), s=ReadoutScenario(), p=Physics()):
    informed,diagnostics=resolved_clock_readout(c,s,p)
    original_trace,original_a,original_d=simulate(c,p)
    informed_trace,informed_a,informed_d=simulate(informed,p)
    original_a=original_a.assign(scenario='Original assumed readout')
    informed_a=informed_a.assign(scenario='ODMR-informed ideal readout')
    return dict(original_trace=original_trace,informed_trace=informed_trace,
        allan=pd.concat([original_a,informed_a],ignore_index=True),
        original_diagnostics=original_d,informed_diagnostics=informed_d,
        informed_config=informed,bridge_diagnostics=diagnostics)
