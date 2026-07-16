"""Совместимый resumable runner реальных Docker runs v0.3.11."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"lab/campaigns")]
import v0310_runner
from v0311_campaign import build_manifest

def execute(campaign:dict,output_root:Path,resume=False,strict=False):
 old=v0310_runner.build_manifest;v0310_runner.build_manifest=build_manifest
 try:return v0310_runner.execute(campaign,output_root,resume=resume,strict=strict)
 finally:v0310_runner.build_manifest=old
