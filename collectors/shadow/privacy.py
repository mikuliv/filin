from __future__ import annotations
import json, re

FORBIDDEN_KEYS = {"raw_pcap","pcap","payload","http_body","authentication_data","password","token","cookie","authorization","username","email","phone","patient_data","medical_data","filesystem_path","ip_address","mac_address","hostname","container_id","label","true_class","benign_variant","historical_policy_result","features","feature_vector","joint_class_probabilities","subtype_probabilities"}
PATTERNS = [
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(r"\b[0-9a-f]{2}(?::[0-9a-f]{2}){5}\b", re.I),
    re.compile(r"bearer\s+\S+", re.I),
    re.compile(r"[A-Za-z]:\\(?:Users|Documents and Settings)\\", re.I),
    re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b"),
    re.compile(r"https?://[^\s?]+\?[^\s]+", re.I),
    re.compile(r"\b(?:api[_-]?key|password|cookie|authorization)\s*[:=]\s*\S+", re.I),
]

def audit(value) -> list[str]:
    failures=[]
    def visit(item,path="$"):
        if isinstance(item,dict):
            for key,val in item.items():
                if key.casefold() in FORBIDDEN_KEYS: failures.append(f"forbidden_key:{path}.{key}")
                visit(val,f"{path}.{key}")
        elif isinstance(item,list):
            for index,val in enumerate(item): visit(val,f"{path}[{index}]")
        elif isinstance(item,str):
            for index,pattern in enumerate(PATTERNS):
                if pattern.search(item): failures.append(f"forbidden_pattern_{index}:{path}")
    visit(value); return failures

def validate(value):
    failures=audit(value)
    if failures: raise ValueError("privacy_validation_failed:"+",".join(failures))
    return True


def sanitize_exception(error: BaseException) -> dict:
    """Возвращает только класс и стабильный код без исходного сообщения."""
    return {"error_type": type(error).__name__, "error_code": "sanitized_runtime_error"}


def audit_targets(targets: dict) -> dict:
    findings = []
    for name, value in targets.items():
        findings.extend({"target": name, "finding": finding} for finding in audit(value))
    return {"target_count": len(targets), "targets": sorted(targets), "finding_count": len(findings), "findings": findings}
