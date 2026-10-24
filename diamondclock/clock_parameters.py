"""Declared Phase 4 protocol; defaults are simulation assumptions, not hardware fits."""
from dataclasses import dataclass,asdict
import numpy as np
from .optical_parameters import OpticalConfig, OpticalRates, Detector
from .oscillator import OscillatorConfig


@dataclass(frozen=True)
class ControllerConfig:
    proportional: float = 0.
    integral_per_s: float = 3.
    latency_s: float = .01
    correction_limit_Hz: float = 2e6
    capture_Hz: float = 450e3
    lock_error_Hz: float = 100e3
    lock_sigma_Hz: float = 80e3
    consecutive_good: int = 8
    consecutive_bad: int = 4
    max_reacquisitions: int = 2

    def validate(self):
        if not all(np.isfinite(v) for v in asdict(self).values()):raise ValueError('Controller values must be finite.')
        if min(self.proportional,self.integral_per_s,self.latency_s)<0 or min(self.correction_limit_Hz,self.capture_Hz,self.lock_error_Hz,self.lock_sigma_Hz)<=0:
            raise ValueError('Nonnegative gains/latency and positive limits required.')
        if self.capture_Hz>800e3 or self.correction_limit_Hz>10e6:raise ValueError('Controller exceeds supported spectroscopy range.')
        for key in ('consecutive_good','consecutive_bad','max_reacquisitions'):
            v=getattr(self,key)
            if not isinstance(v,int) or isinstance(v,bool) or v < (0 if key=='max_reacquisitions' else 1):raise ValueError('Invalid lock counter.')


@dataclass(frozen=True)
class ClockExperiment:
    optical: OpticalConfig = OpticalConfig()
    rates: OpticalRates = OpticalRates()
    detector: Detector = Detector()
    oscillator: OscillatorConfig = OscillatorConfig()
    controller: ControllerConfig = ControllerConfig()
    native_dt_s: float = .002
    gate_s: float = .01
    settling_s: float = 20e-6
    cycles: int = 512
    acquisition_points: int = 81
    acquisition_span_Hz: float = 4e6
    dither_Hz: float = 250e3
    maximum_time_s: float = 120.
    seed: int = 410024
    reference_offset_Hz: float = -35e3  # plant-only sample shift; never passed to inference
    plant_backend: str = 'lindblad'

    def validate(self):
        for obj in (self.optical,self.rates,self.detector,self.oscillator,self.controller):obj.validate()
        # The seven-state end-to-end implementation is validated before removing this guard.
        if self.optical.states!=7:raise ValueError('Seven-state clock validation comes first.')
        for key in ('native_dt_s','gate_s','settling_s','acquisition_span_Hz','dither_Hz','maximum_time_s','reference_offset_Hz'):
            if not np.isfinite(getattr(self,key)):raise ValueError('Nonfinite protocol value.')
        if not .0001<=self.native_dt_s<=.01 or not .001<=self.gate_s<=.1 or self.native_dt_s>self.gate_s:
            raise ValueError('Use native dt 0.1..10 ms <= gate, and gates 1..100 ms.')
        if not 0<=self.settling_s<=.01 or not 50e3<=self.dither_Hz<=500e3:
            raise ValueError('Invalid settling time or dither.')
        if not isinstance(self.cycles,int) or not 4<=self.cycles<=4096 or not isinstance(self.acquisition_points,int) or not 31<=self.acquisition_points<=201:
            raise ValueError('Use 4..4096 cycles and 31..201 acquisition points.')
        if not 3e6<=self.acquisition_span_Hz<=8e6 or not 2<=self.maximum_time_s<=1800 or abs(self.reference_offset_Hz)>1e6:
            raise ValueError('Protocol exceeds the declared simulation window.')
        if not isinstance(self.seed,int) or isinstance(self.seed,bool) or self.seed<0:raise ValueError('Nonnegative integer seed required.')
        if self.detector.efficiency>.02 or self.optical.pump_s<.1e6:
            raise ValueError('Long clock uses qualified low-efficiency Poisson counts and pump >=0.1 million/s.')
        if self.plant_backend not in ('lindblad','rate'):raise ValueError('Unknown optical plant backend.')
