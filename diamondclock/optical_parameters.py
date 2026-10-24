"""Phase 3 parameters. Rates are s^-1, not angular frequencies; see OPM1-OPM9."""
from dataclasses import dataclass, asdict
import numpy as np


@dataclass(frozen=True)
class OpticalRates:
    # One complete fitted set: Tetienne 2012 Table 1, printed p.9, NV E.
    radiative_s: float = 63.7e6
    isc_zero_s: float = 9.3e6
    isc_pm_s: float = 53.0e6
    singlet_zero_s: float = .9e6
    singlet_pm_s: float = .5e6  # EACH of +1 and -1, not their sum

    def validate(self):
        if any(not np.isfinite(v) or v < 0 for v in asdict(self).values()):
            raise ValueError('Optical rates must be finite and nonnegative.')
        if self.radiative_s <= 0 or self.singlet_zero_s+2*self.singlet_pm_s <= 0:
            raise ValueError('Positive radiative rate and total singlet return are required.')


@dataclass(frozen=True)
class OpticalConfig:
    states: int = 7
    Bz_G: float = 20.
    temperature_K: float = 297.
    pump_s: float = 2e6
    rabi_Hz: float = 200_000.  # isolated electronic transition Rabi cycles/s
    pure_dephasing_s: float = 100_000.
    ground_pair_s: float = 1000.  # symmetric electron-spin pair rate, MODEL

    def validate(self):
        if not isinstance(self.states, int) or self.states not in (7, 21) or isinstance(self.states, bool):
            raise ValueError('Use 7 electronic or 21 electron/nuclear optical states.')
        if not all(np.isfinite(v) for v in asdict(self).values()):
            raise ValueError('Optical settings must be finite.')
        if not 5 <= self.Bz_G <= 50 or self.temperature_K != 297:
            raise ValueError('Phase 3 scope: local axial B=5..50 G, E=0, nominal room temperature 297 K. No 475 G validation.')
        if not 0 <= self.pump_s <= 20e6 or not 0 <= self.rabi_Hz <= 1e6:
            raise ValueError('Use pump 0..20e6 s^-1 and electronic Rabi 0..1e6 Hz.')
        if min(self.pure_dephasing_s, self.ground_pair_s) < 0:
            raise ValueError('Relaxation and pure dephasing cannot be negative.')


@dataclass(frozen=True)
class Detector:
    efficiency: float = .01
    centers: int = 100
    background_s: float = 1000.
    dark_s: float = 100.

    def validate(self):
        if not all(np.isfinite(v) for v in asdict(self).values()):
            raise ValueError('Detector inputs must be finite.')
        if not 0 <= self.efficiency <= 1 or not isinstance(self.centers, int) or isinstance(self.centers, bool) or self.centers < 1:
            raise ValueError('Use efficiency [0,1] and a positive integer center count.')
        if min(self.background_s, self.dark_s) < 0:
            raise ValueError('Background and dark rates cannot be negative.')


@dataclass(frozen=True)
class OpticalExperiment:
    optical: OpticalConfig = OpticalConfig()
    rates: OpticalRates = OpticalRates()
    detector: Detector = Detector()
    points: int = 81
    span_Hz: float = 6e6
    dwell_s: float = .001
    seed: int = 310024
    backend: str = 'lindblad'

    def validate(self):
        self.optical.validate(); self.rates.validate(); self.detector.validate()
        if not isinstance(self.points, int) or not 5 <= self.points <= 1001:
            raise ValueError('Use 5..1001 scan frequencies.')
        if not np.isfinite(self.span_Hz) or not 1e6 <= self.span_Hz <= 15e6:
            raise ValueError('Use scan half-span 1..15 MHz around the upper electronic branch.')
        if not np.isfinite(self.dwell_s) or not 1e-4 <= self.dwell_s <= 1:
            raise ValueError('Fast Poisson CW acquisition uses 0.1 ms..1 s gates.')
        if self.detector.efficiency > .02:
            raise ValueError('Fast scan Poisson approximation restricted to efficiency <=2%; use number-resolved reference otherwise.')
        if not isinstance(self.seed, int) or isinstance(self.seed, bool) or self.seed < 0:
            raise ValueError('A nonnegative integer seed is required.')
        if self.optical.pump_s <= 0 or self.backend not in ('lindblad', 'rate'):
            raise ValueError('CW scan needs positive pumping and lindblad or rate backend.')


def parameter_records(experiment):
    """Explicitly separate published fits from operating assumptions; no fit to our data."""
    rows=[]
    uncertainties=[4.5e6,3e6,5.9e6,.8e6,.2e6]
    for (name,value),uncertainty in zip(asdict(experiment.rates).items(),uncertainties):
        default=getattr(OpticalRates(),name)
        rows.append(dict(parameter=name,value=value,unit='s^-1',
            classification='published_fitted_value' if value==default else 'simulation_assumption_override',
            source='TET2012',locator='Table 1, printed p.9, NV E',
            published_value=default,published_standard_deviation=uncertainty,
            uncertainty_propagated=False,experimental_validation='Published defect only; not this simulator or sample'))
    for group,obj in [('optical',experiment.optical),('detector',experiment.detector)]:
        for name,value in asdict(obj).items():
            rows.append(dict(parameter=group+'.'+name,value=value,unit={
                'Bz_G':'G','temperature_K':'K','pump_s':'s^-1','rabi_Hz':'Hz',
                'pure_dephasing_s':'s^-1','ground_pair_s':'s^-1','background_s':'counts/s',
                'dark_s':'counts/s'}.get(name,'dimensionless'),classification='simulation_assumption',
                source='MODEL',locator='docs/OPTICAL_METHODS.md',uncertainty_propagated=False,
                experimental_validation='None'))
    for name in ('points','span_Hz','dwell_s','seed','backend'):
        rows.append(dict(parameter=name,value=getattr(experiment,name),unit={
            'span_Hz':'Hz','dwell_s':'s'}.get(name,'dimensionless'),classification='numerical_protocol',
            source='MODEL',locator='OPM7',experimental_validation='None'))
    return rows
