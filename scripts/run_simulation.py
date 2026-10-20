"""Reproduce a run without starting Streamlit."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from diamondclock.simulation import Config,simulate,ensemble
from diamondclock.reporting import export_files
from diamondclock.physics import Physics
from diamondclock.reference_store import ReferenceStore
from diamondclock.run_provenance import capture, write_run_directory

def main():
    parser=argparse.ArgumentParser(description='Diamond Atomic Clock conditional simulation')
    parser.add_argument('--config',type=Path)
    parser.add_argument('--out',type=Path,default=Path('outputs/reproduction'))
    parser.add_argument('--ensemble',type=int,default=0,help='0 to disable, or 3..100 realizations')
    args=parser.parse_args()
    c=Config(**json.loads(args.config.read_text())) if args.config else Config()
    if args.out.exists():
        parser.error('Output path already exists; choose a new run directory.')
    context=capture(config=c,physics=Physics())
    trace,a,d=simulate(c)
    raw=q=None
    if args.ensemble:raw,q=ensemble(c,args.ensemble)
    files=export_files(trace,a,c,d,quantiles=q,ensemble_raw=raw,run_provenance=context,references=ReferenceStore().catalog())
    write_run_directory(args.out,files)
    target=a[(a.method=='composite')].iloc[(a[a.method=='composite'].tau_s-200).abs().argmin()]
    print(f'SIMULATION: composite ADEV {target.adev:.6e} at tau={target.tau_s:g} s')
    print(f'Wrote {len(files)} files to {args.out.resolve()}')

if __name__=='__main__':main()
