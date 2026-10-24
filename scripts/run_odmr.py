"""Reproduce an ODMR bundle inside DiamondClock Lab; refuses existing directories."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from diamondclock.odmr import ODMRConfig
from diamondclock.odmr_bridge import ReadoutScenario
from diamondclock.odmr_reporting import calculate, export_odmr
from diamondclock.simulation import Config
from diamondclock.reference_store import ReferenceStore
from diamondclock.run_provenance import write_run_directory


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,help='ODMRConfig JSON; defaults if omitted')
    parser.add_argument('--clock-config',type=Path)
    parser.add_argument('--readout-config',type=Path)
    parser.add_argument('--compare',action='store_true')
    parser.add_argument('--samples',type=int,default=4096,help='Clock samples if no clock JSON supplied')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():parser.error('Output path already exists; choose a new directory.')
    def read(path):return json.loads(path.read_text(encoding='utf-8'))
    c=ODMRConfig(**read(args.config)) if args.config else ODMRConfig()
    clock=Config(**read(args.clock_config)) if args.clock_config else Config(n=args.samples)
    readout=ReadoutScenario(**read(args.readout_config)) if args.readout_config else ReadoutScenario()
    result=calculate(c,clock if args.compare else None,readout if args.compare else None)
    files=export_odmr(result,c,references=ReferenceStore().catalog())
    write_run_directory(args.out,files)
    print(f'SIMULATION: wrote {len(files)} reproducible ODMR bundle members to {args.out}')


if __name__=='__main__':main()
