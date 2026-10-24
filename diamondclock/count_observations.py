"""Allowed inputs to Phase 4 inference. No expected counts, seeds or hidden truth."""
from dataclasses import dataclass
import math


@dataclass(frozen=True,slots=True)
class CountObservation:
    probe_offset_Hz: float  # known DDS command, relative to the controlled carrier
    nominal_gate_s: float  # programmed local-clock duration, not oracle SI duration
    detected_counts: int
    microwave_on: bool = True
    local_start_s: float = 0.

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (self.probe_offset_Hz,self.nominal_gate_s,self.local_start_s)):
            raise ValueError('Observation commands/times must be finite.')
        if self.nominal_gate_s<=0 or not isinstance(self.detected_counts,int) or self.detected_counts<0:
            raise ValueError('Use a positive programmed gate and nonnegative integer count.')


@dataclass(frozen=True)
class Calibration:
    centre_command_Hz: float
    width_Hz: float
    baseline_per_nominal_s: float
    fractions: tuple
    offsets_Hz: tuple
    covariance: tuple  # [centre_MHz,log(width_MHz),log(baseline),fractions...]
    centre_sigma_Hz: float
    lower_Hz: float
    upper_Hz: float
    valid: bool
    reason: str
    likelihood_ratio: float


@dataclass(frozen=True)
class FrequencyEstimate:
    detuning_Hz: float
    sigma_Hz: float
    lower_Hz: float
    upper_Hz: float
    count_only_lower_Hz: float
    count_only_upper_Hz: float
    valid: bool
    reason: str
    baseline_per_nominal_s: float
