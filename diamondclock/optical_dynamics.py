"""Opt-in 21-state extension. Exact existing H_g; secular optical channels (OPM6)."""
from .physics import Physics, hamiltonian
from .odmr import microwave_operator
from .optical_parameters import OpticalConfig, OpticalRates
from .optical_cycle import seven_state, _assemble


def build_system(c=OpticalConfig(),r=OpticalRates(),p=Physics(),frequency_Hz=None):
    c.validate();r.validate()
    if c.states==7:return seven_state(c,r,p,frequency_Hz)
    hg=hamiltonian(c.temperature_K,c.Bz_G,0.,p)
    return _assemble(c,r,p,hg,microwave_operator((1.,0.,0.),p),frequency_Hz)
