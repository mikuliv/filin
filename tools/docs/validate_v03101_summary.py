"""Strict validator самостоятельного отчёта v0.3.10.1."""
import argparse
from pathlib import Path

REQUIRED = ["Frozen integrity","Legacy pending semantics","120","Post-alert continuation","Structural policy reachability",
 "Training model-selection audit","Selection unchanged","Ryzen 5 5600X","64 ГБ RAM","RTX 5060 Ti","5:05","66 минут",
 "Controlled benchmark","CPU utilization","RAM utilization","speedup=","Equivalence audit","Recommended resource profile",
 "Ограничения результатов","Рекомендации следующему этапу","internal validation=false"]

def validate(path: Path):
    text=path.read_text(encoding="utf-8"); missing=[item for item in REQUIRED if item not in text]
    sections=text.split("\n## ")[1:]; empty=[s.splitlines()[0] for s in sections if len([x for x in s.splitlines()[1:] if x.strip()])==0]
    return {"valid":not missing and not empty,"missing":missing,"empty_sections":empty}

def main():
    p=argparse.ArgumentParser();p.add_argument("--summary",required=True);p.add_argument("--strict",action="store_true");a=p.parse_args()
    result=validate(Path(a.summary));print(result)
    if a.strict and not result["valid"]: raise SystemExit(1)
if __name__=="__main__":main()
