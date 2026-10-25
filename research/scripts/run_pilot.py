from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/"research/src")]
from satquery_research.runner import main
if __name__=="__main__": main("pilot.yaml")
