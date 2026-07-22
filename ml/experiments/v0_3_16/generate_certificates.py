from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "runtime/v0_3_16/tls"
REPORT = ROOT / "runtime/v0_3_16/certificate_manifest.json"


def run(*args: str) -> None:
    environment = dict(os.environ)
    environment["OPENSSL_CONF"] = "NUL"
    subprocess.run(["openssl", *args], check=True, capture_output=True, env=environment)


def issue(ca_dir: Path, target: Path, name: str, serial: int, san: str, usage: str) -> None:
    key, csr, cert = target / f"{name}-key.pem", target / f"{name}.csr", target / f"{name}.pem"
    run("genpkey", "-algorithm", "ED25519", "-out", str(key))
    run("req", "-new", "-key", str(key), "-out", str(csr), "-subj", f"/CN={name}")
    ext = target / f"{name}.ext"
    ext.write_text(f"subjectAltName=DNS:{san}\nextendedKeyUsage={usage}\nbasicConstraints=CA:FALSE\n", encoding="ascii")
    run("x509", "-req", "-in", str(csr), "-CA", str(ca_dir / "ca.pem"), "-CAkey", str(ca_dir / "ca-key.pem"), "-set_serial", str(serial), "-days", "7", "-extfile", str(ext), "-out", str(cert))
    csr.unlink(); ext.unlink()


def ca(path: Path, name: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    run("genpkey", "-algorithm", "ED25519", "-out", str(path / "ca-key.pem"))
    run("req", "-x509", "-new", "-key", str(path / "ca-key.pem"), "-out", str(path / "ca.pem"), "-days", "7", "-subj", f"/CN={name}", "-addext", "basicConstraints=critical,CA:TRUE")


def main() -> int:
    if OUT.exists(): shutil.rmtree(OUT)
    first, second = OUT / "ca-sensor-connector", OUT / "ca-connector-receiver"
    sensor, connector, receiver = OUT / "sensor", OUT / "connector", OUT / "receiver"
    for path in (sensor, connector, receiver): path.mkdir(parents=True, exist_ok=True)
    ca(first, "sensor_connector_test_ca"); ca(second, "connector_receiver_test_ca")
    issue(first, sensor, "client", 3163001, "sensor-runtime", "clientAuth")
    issue(first, connector, "ingress-server", 3163002, "staging-connector", "serverAuth")
    issue(second, connector, "delivery-client", 3164001, "staging-connector", "clientAuth")
    issue(second, connector, "delivery-client-b", 3164002, "staging-connector", "clientAuth")
    issue(second, receiver, "server", 3164003, "reference-receiver", "serverAuth")
    issue(second, receiver, "server-b", 3164004, "reference-receiver", "serverAuth")
    shutil.copy2(first / "ca.pem", sensor / "server-ca.pem"); shutil.copy2(first / "ca.pem", connector / "ingress-client-ca.pem")
    shutil.copy2(second / "ca.pem", connector / "delivery-server-ca.pem"); shutil.copy2(second / "ca.pem", receiver / "client-ca.pem")
    public = []
    for path in sorted(OUT.rglob("*.pem")):
        if "key" in path.name: continue
        public.append({"role": str(path.relative_to(OUT)).replace("\\", "/"), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size": path.stat().st_size})
    REPORT.write_text(json.dumps({"schema_version": "v0316_certificate_manifest_v1", "synthetic_only": True, "tls_version": "TLSv1.3", "certificate_count": 6, "ca_count": 2, "private_key_count_tracked": 0, "public_artifacts": public}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
