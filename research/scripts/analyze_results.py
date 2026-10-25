from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/"research/src")]
from satquery_research.analysis import analyze
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("run_directory");a=p.parse_args();print(analyze(a.run_directory))
