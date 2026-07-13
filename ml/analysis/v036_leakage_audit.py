"""Leakage audit v0.3.6."""
from v036_holdout import FORBIDDEN_FEATURES
def audit(columns):
 found=sorted(set(columns)&FORBIDDEN_FEATURES)
 return {'v036_leakage_valid':not found,'forbidden_model_features':found}
