from pathlib import Path
import argparse
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'research/src')]
from satquery_research.phase3b_integrity import Source,validate
from satquery_research.manifests import atomic_json

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--results',required=True,help='Original ZIP or extracted run directory; read-only')
    parser.add_argument('--output',default=str(ROOT/'research/analysis/phase3b'))
    parser.add_argument('--integrity-only',action='store_true')
    args=parser.parse_args();output=Path(args.output).resolve()
    input_path=Path(args.results).resolve()
    if input_path.is_dir() and output.is_relative_to(input_path):raise ValueError('Output must not overwrite source run')
    output.mkdir(parents=True,exist_ok=True)
    try:
        source=Source(args.results)
        report,p,e,r,roster=validate(source)
    except (OSError,ValueError,KeyError,AssertionError,zipfile.BadZipFile) as exc:
        report=dict(status='failed',policy_selection_allowed=False,errors=[type(exc).__name__+': '+str(exc)])
        atomic_json(output/'integrity_report.json',report)
        print(report,flush=True)
        return 2
    if not source.archive and output.is_relative_to(source.path):raise ValueError('Output must not overwrite source run')
    output.mkdir(parents=True,exist_ok=True)
    atomic_json(output/'integrity_report.json',report)
    atomic_json(output/'source_file_hashes.json',source.hashes)
    print(report['status'],report['counts'],report['errors'],flush=True)
    if not report['policy_selection_allowed']:return 2
    if not args.integrity_only:
        from satquery_research.phase3b_analysis import analyze
        analyze(source,output,p,e,r,roster)
    return 0

if __name__=='__main__':sys.exit(main())
