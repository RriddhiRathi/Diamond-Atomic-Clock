"""Observable-only PI and lock detector. Latency is applied by the event scheduler."""
import numpy as np
from .clock_parameters import ControllerConfig


class PhotonController:
    def __init__(self,config=ControllerConfig()):
        config.validate();self.config=config;self.integrator=0.;self.good=0;self.bad=0;self.locked=False

    def acquired(self,command_Hz):
        self.integrator=float(np.clip(command_Hz,-self.config.correction_limit_Hz,self.config.correction_limit_Hz))
        self.good=0;self.bad=0;self.locked=False
        return self.integrator

    def update(self,estimate,nominal_cycle_s):
        c=self.config
        if not estimate.valid or not np.isfinite(estimate.sigma_Hz):
            self.good=0;self.bad+=1
            if self.bad>=c.consecutive_bad:self.locked=False
            return None
        candidate=self.integrator-c.integral_per_s*nominal_cycle_s*estimate.detuning_Hz
        raw=candidate-c.proportional*estimate.detuning_Hz
        limit=c.correction_limit_Hz
        saturated=abs(raw)>limit
        # Conditional integration: do not wind farther into an actuator limit.
        if not saturated or (raw>limit and estimate.detuning_Hz>0) or (raw < -limit and estimate.detuning_Hz<0):
            self.integrator=candidate
        command=float(np.clip(self.integrator-c.proportional*estimate.detuning_Hz,-limit,limit))
        good=not saturated and abs(estimate.detuning_Hz)+estimate.sigma_Hz<c.lock_error_Hz and estimate.sigma_Hz<c.lock_sigma_Hz
        if good:self.good+=1;self.bad=0
        else:self.good=0;self.bad+=1
        if self.good>=c.consecutive_good:self.locked=True
        if self.bad>=c.consecutive_bad:self.locked=False
        return command
