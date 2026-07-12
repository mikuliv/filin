"""Print current development-environment metadata without claiming historical provenance."""
from __future__ import annotations

import importlib.metadata
import json
import platform
import subprocess
import sys


def version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def main() -> None:
    try:
        docker = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"], capture_output=True, text=True, check=True).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        docker = None
    print(json.dumps({"scope": "current_development_environment_not_historical_experiment_provenance", "python": sys.version, "platform": platform.platform(), "packages": {name: version(name) for name in ("pandas", "numpy", "scikit-learn", "joblib", "PyYAML")}, "docker_server": docker}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
