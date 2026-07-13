"""Overlap audit v0.3.6."""
from v036_holdout import collection_audits
def audit(*args,**kwargs): return collection_audits(*args,**kwargs)['overlap']
