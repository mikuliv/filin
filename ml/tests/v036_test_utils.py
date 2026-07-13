from pathlib import Path
import sys,yaml
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ml/analysis'),str(ROOT/'ml/features'),str(ROOT/'lab/holdout'),str(ROOT/'lab/campaigns')]
def load(path):return yaml.safe_load((ROOT/path).read_text(encoding='utf-8'))
