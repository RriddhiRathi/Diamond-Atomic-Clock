"""Source-checkout wrapper; installed users can also run diamondclock-clock."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from diamondclock.clock_cli import main

if __name__=='__main__':main()
