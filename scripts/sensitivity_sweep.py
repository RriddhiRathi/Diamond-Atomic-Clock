"""M8: paired calibration-error study at fixed assumed environment and readout."""
import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from diamondclock.simulation import Config,simulate

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path)
    parser.add_argument('--out',type=Path,default=Path('outputs/calibration_sweep_SIMULATION.csv'))
    args=parser.parse_args()
    c=Config(**json.loads(args.config.read_text())) if args.config else Config()
    frames=[]
    for error in [-10.,-5.,-1.,0.,1.,5.,10.]:
        _,a,_=simulate(replace(c,slope_error_pct=error))
        a['slope_error_pct']=error
        a['paired_seed']=c.seed
        frames.append(a)
    args.out.parent.mkdir(exist_ok=True,parents=True)
    pd.concat(frames).to_csv(args.out,index=False)
    print(f'Wrote paired SIMULATION sweep to {args.out.resolve()}')

if __name__=='__main__':main()
