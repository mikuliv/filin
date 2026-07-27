"""Regenerate third-party notices through the canonical licensing builder."""
from .build_license_manifest import build_notices
def main()->int: build_notices(); return 0
if __name__=="__main__":raise SystemExit(main())
