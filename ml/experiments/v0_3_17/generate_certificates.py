from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "runtime/v0_3_17"


def run(*args: str) -> None:
    environment = dict(os.environ)
    environment["OPENSSL_CONF"] = "NUL" if os.name == "nt" else "/dev/null"
    subprocess.run(["openssl", *args], check=True, capture_output=True, env=environment)


def ca(path: Path, name: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    run("genpkey", "-algorithm", "ED25519", "-out", str(path / "ca-key.pem"))
    run("req", "-x509", "-new", "-key", str(path / "ca-key.pem"), "-out", str(path / "ca.pem"), "-days", "7", "-subj", f"/CN={name}", "-addext", "basicConstraints=critical,CA:TRUE")


def issue(ca_dir: Path, target: Path, name: str, serial: int, san: str, usage: str) -> None:
    target.mkdir(parents=True, exist_ok=True)
    key, csr, cert = target / f"{name}-key.pem", target / f"{name}.csr", target / f"{name}.pem"
    run("genpkey", "-algorithm", "ED25519", "-out", str(key))
    run("req", "-new", "-key", str(key), "-out", str(csr), "-subj", f"/CN={name}")
    extension = target / f"{name}.ext"
    extension.write_text(f"subjectAltName=DNS:{san}\nextendedKeyUsage={usage}\nbasicConstraints=CA:FALSE\n", encoding="ascii")
    run("x509", "-req", "-in", str(csr), "-CA", str(ca_dir / "ca.pem"), "-CAkey", str(ca_dir / "ca-key.pem"), "-set_serial", str(serial), "-days", "7", "-extfile", str(extension), "-out", str(cert))
    csr.unlink()
    extension.unlink()
    key.chmod(stat.S_IRUSR | stat.S_IWUSR)


def link_set(root: Path, link: str, variant: str, serial: int) -> None:
    ca_dir = root / f"ca-{link}-{variant}"
    ca(ca_dir, f"v0317_{link}_{variant}_ca")
    if link == "sensor-connector":
        sensor, connector = root / variant / "sensor", root / variant / "connector"
        issue(ca_dir, sensor, "client", serial, "sensor-runtime", "clientAuth")
        issue(ca_dir, connector, "ingress-server", serial + 1, "staging-connector", "serverAuth")
        shutil.copy2(ca_dir / "ca.pem", sensor / "server-ca.pem")
        shutil.copy2(ca_dir / "ca.pem", connector / "ingress-client-ca.pem")
    else:
        connector, receiver = root / variant / "connector", root / variant / "receiver"
        issue(ca_dir, connector, "delivery-client", serial, "staging-connector", "clientAuth")
        issue(ca_dir, receiver, "server", serial + 1, "reference-receiver", "serverAuth")
        shutil.copy2(ca_dir / "ca.pem", connector / "delivery-server-ca.pem")
        shutil.copy2(ca_dir / "ca.pem", receiver / "client-ca.pem")


def activate(root: Path, variant: str) -> None:
    active = root / "active"
    if active.exists():
        shutil.rmtree(active)
    for component in ("sensor", "connector", "receiver"):
        source = root / variant / component
        target = active / component
        target.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            for path in source.iterdir():
                shutil.copy2(path, target / path.name)
    for key in active.rglob("*-key.pem"):
        key.chmod(stat.S_IRUSR | stat.S_IWUSR)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-index", type=int, required=True, choices=(1, 2, 3))
    parser.add_argument("--revision", type=int, required=True, choices=(3,))
    args = parser.parse_args()
    root = RUNTIME / "tls" / f"run-{args.run_index}"
    if root.exists():
        raise RuntimeError(f"certificate_session_already_exists:{root}")
    base = 3_173_000 + args.run_index * 100
    for variant, offset in (("a", 0), ("b", 20)):
        link_set(root, "sensor-connector", variant, base + offset + 1)
        link_set(root, "connector-receiver", variant, base + offset + 41)
    activate(root, "a")
    public = []
    for path in sorted(root.rglob("*.pem")):
        if "key" in path.name:
            continue
        public.append({
            "relative_path": str(path.relative_to(root)).replace("\\", "/"),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size": path.stat().st_size,
        })
    manifest = {
        "schema_version": "v0317_certificate_session_v1",
        "run_index": args.run_index,
        "revision": args.revision,
        "synthetic_only": True,
        "tls_version": "TLSv1.3",
        "variants": ["a", "b"],
        "private_key_count_tracked": 0,
        "private_key_mode": "0600",
        "public_artifacts": public,
    }
    path = root / "certificate_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
