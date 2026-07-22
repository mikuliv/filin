from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "runtime/v0_3_15_4"


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    source = json.loads((RUNTIME / "label_vault.json").read_text(encoding="utf-8"))
    development = [row for row in source["records"] if row["split"] in {"training", "calibration"}]
    audit = [row for row in source["records"] if row["split"] == "internal_audit"]
    write(RUNTIME / "development_labels.json", {"schema_version": "v03154_development_labels_v1", "record_count": len(development), "records": development})
    write(RUNTIME / "sealed_internal_audit_labels.json", {"schema_version": "v03154_internal_audit_labels_v1", "sealed": True, "record_count": len(audit), "records": audit})
    commitment = {"development_record_count": len(development), "audit_record_count": len(audit), "development_sha256": sha(RUNTIME / "development_labels.json"), "sealed_audit_sha256": sha(RUNTIME / "sealed_internal_audit_labels.json"), "audit_labels_exposed_to_training_process": False}
    write(RUNTIME / "label_separation_commitment.json", commitment)
    print(json.dumps(commitment, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
