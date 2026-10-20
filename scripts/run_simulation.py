"""Reproduce a run without starting Streamlit."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from diamondclock.simulation import Config,simulate,ensemble
from diamondclock.reporting import export_files

def main():
    parser=argparse.ArgumentParser(description='Diamond Atomic Clock conditional simulation')
    parser.add_argument('--config',type=Path)
    parser.add_argument('--out',type=Path,default=Path('outputs/reproduction'))
    parser.add_argument('--ensemble',type=int,default=0,help='0 to disable, or 3..100 realizations')
    args=parser.parse_args()
    c=Config(**json.loads(args.config.read_text())) if args.config else Config()
    trace,a,d=simulate(c)
    raw=q=None
    if args.ensemble:raw,q=ensemble(c,args.ensemble)
    files=export_files(trace,a,c,d,quantiles=q,ensemble_raw=raw)
    args.out.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():(args.out/name).write_bytes(data)
    target=a[(a.method=='composite')].iloc[(a[a.method=='composite'].tau_s-200).abs().argmin()]
    print(f'SIMULATION: composite ADEV {target.adev:.6e} at tau={target.tau_s:g} s')
    print(f'Wrote {len(files)} files to {args.out.resolve()}')

if __name__=='__main__':main()
