"""Generate a Phase 3 optical bundle; no deployment, no clock engine changes."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from diamondclock.optical_parameters import OpticalExperiment, OpticalConfig, OpticalRates, Detector
from diamondclock.optical_reporting import calculate_optical, export_optical
from diamondclock.reference_store import ReferenceStore
from diamondclock.run_provenance import write_run_directory


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--states',type=int,choices=(7,21),default=7)
    parser.add_argument('--points',type=int,default=81)
    parser.add_argument('--config',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    a=parser.parse_args()
    if a.out.exists():parser.error('Output already exists; choose a fresh path.')
    if a.config:
        values=json.loads(a.config.read_text(encoding='utf-8'))
        for key,cls in [('optical',OpticalConfig),('rates',OpticalRates),('detector',Detector)]:
            if key in values:values[key]=cls(**values[key])
        experiment=OpticalExperiment(**values)
    else:experiment=OpticalExperiment(optical=OpticalConfig(states=a.states),points=a.points)
    result=calculate_optical(experiment)
    write_run_directory(a.out,export_optical(result,experiment,references=ReferenceStore().catalog()))
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':main()
