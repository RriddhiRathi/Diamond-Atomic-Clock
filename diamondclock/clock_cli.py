"""Reproduce a Phase 4 clock bundle in a fresh directory."""
import argparse,json
from dataclasses import replace
from pathlib import Path
from .clock_parameters import ClockExperiment,ControllerConfig
from .optical_parameters import OpticalConfig,OpticalRates,Detector
from .oscillator import OscillatorConfig
from .clock_reporting import calculate_clock,export_clock
from .reference_store import ReferenceStore
from .run_provenance import write_run_directory


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path)
    parser.add_argument('--states',type=int,choices=(7,21),default=7)
    parser.add_argument('--cycles',type=int,default=512)
    parser.add_argument('--scenario',choices=('normal','high-gain','latency','photon-starved','low-drift'),default='normal')
    parser.add_argument('--validation-trials',type=int,default=0)
    parser.add_argument('--physical-trials',type=int,default=0)
    parser.add_argument('--out',type=Path,required=True)
    a=parser.parse_args()
    if a.out.exists():parser.error('Output already exists; select a fresh directory.')
    if a.config:
        data=json.loads(a.config.read_text(encoding='utf-8'))
        for key,cls in [('optical',OpticalConfig),('rates',OpticalRates),('detector',Detector),('oscillator',OscillatorConfig),('controller',ControllerConfig)]:
            if key in data:data[key]=cls(**data[key])
        c=ClockExperiment(**data)
    else:
        c=ClockExperiment(optical=OpticalConfig(states=a.states),cycles=a.cycles,
            plant_backend='lindblad' if a.states==7 else 'rate',detector=Detector(centers=100 if a.states==7 else 1000))
        if a.scenario=='high-gain':c=replace(c,controller=replace(c.controller,integral_per_s=70,max_reacquisitions=0))
        if a.scenario=='latency':c=replace(c,controller=replace(c.controller,integral_per_s=12,latency_s=.3,max_reacquisitions=0))
        if a.scenario=='photon-starved':c=replace(c,detector=Detector(centers=1),controller=replace(c.controller,max_reacquisitions=0))
        if a.scenario=='low-drift':c=replace(c,oscillator=replace(c.oscillator,drift_Hz_s=100))
    result=calculate_clock(c,a.validation_trials,a.physical_trials)
    write_run_directory(a.out,export_clock(result,c,references=ReferenceStore().catalog()))
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':main()
