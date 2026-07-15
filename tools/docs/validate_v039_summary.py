"""Strict-проверка самостоятельного summary v0.3.9."""
from __future__ import annotations
import argparse,re
from pathlib import Path
HEADINGS=("Причина нового цикла","Научная гипотеза","Ограничения использования старых наборов","Protocol freeze","Data access policy","Training campaign","Prospective validation campaign","Episode design","Feature schema","Fixed HGB/HGB architecture","Calibration","Mondrian conformal prediction","Continuous class-support margins","Strong single-window evidence","Weak repeated evidence","Signed evidence","Alert lifecycle","Hysteresis","Control policy","Decision-policy selection","Frozen candidate","Validation lock","Candidate integrity","No-fit audit","Closed-set metrics","Calibration metrics","Conformal metrics","Support-margin metrics","Strong evidence metrics","Weak evidence metrics","Window evidence metrics","Episode metrics","Detection latency","Lifecycle metrics","Per-run metrics","Per-group metrics","Benign variant metrics","Attack-class metrics","Decision transitions","Paired control comparison","Feature distribution","Model interpretation","Bootstrap intervals","Policy result","Ограничения","Вывод","Следующий этап")
PLACEHOLDERS=("результаты зафиксированы в одноимённом json","todo","заполнить позже")
def validate(path:Path)->list[str]:
 text=path.read_text(encoding="utf-8");errors=[]
 for heading in HEADINGS:
  marker=f"## {heading}";match=re.search(rf"^{re.escape(marker)}\s*$\n(.*?)(?=^## |\Z)",text,re.M|re.S)
  if not match:errors.append(f"отсутствует раздел: {heading}")
  elif len(match.group(1).strip())<20:errors.append(f"пустой раздел: {heading}")
 lower=text.casefold()
 for phrase in PLACEHOLDERS:
  if phrase in lower:errors.append(f"placeholder: {phrase}")
 for token in ("12 runs","504 scored","6 runs","252 scored","SHA-256","Macro F1","episode","latency","v039 completed=true","backend integration","shadow mode","Immutable prediction SHA-256"):
  if token.casefold() not in lower:errors.append(f"нет обязательного значения: {token}")
 return errors
def main():
 p=argparse.ArgumentParser();p.add_argument("--summary",required=True);p.add_argument("--strict",action="store_true");a=p.parse_args();errors=validate(Path(a.summary))
 if errors:
  print("Ошибки summary:");[print("-",x) for x in errors];return 1 if a.strict else 0
 print("Summary v0.3.9 прошёл проверку.");return 0
if __name__=="__main__":raise SystemExit(main())
