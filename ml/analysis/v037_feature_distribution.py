"""Post-hoc drift-анализ training/internal-validation признаков v0.3.7."""
from __future__ import annotations
import numpy as np
import pandas as pd


def _psi(reference,current,bins=10):
    cuts=np.unique(np.quantile(reference,np.linspace(0,1,bins+1)))
    if len(cuts)<3:return 0.0
    a=np.histogram(reference,bins=cuts)[0].astype(float)+1e-6;b=np.histogram(current,bins=cuts)[0].astype(float)+1e-6
    a/=a.sum();b/=b.sum();return float(np.sum((b-a)*np.log(b/a)))


def analyze(training:pd.DataFrame,validation:pd.DataFrame,predictions:pd.DataFrame)->dict:
    records=[]
    for name in training.columns:
        a=training[name].astype(float).to_numpy();b=validation[name].astype(float).to_numpy();std=max(float(np.nanstd(a)),1e-9)
        records.append({'feature':name,'psi':_psi(np.nan_to_num(a),np.nan_to_num(b)),
         'standardized_mean_difference':float((np.nanmean(b)-np.nanmean(a))/std),
         'median_ratio':float(np.nanmedian(b)/max(abs(np.nanmedian(a)),1e-9)),
         'zero_rate_difference':float(np.mean(b==0)-np.mean(a==0)),
         'missing_rate_difference':float(np.mean(np.isnan(b))-np.mean(np.isnan(a))),
         'out_of_training_range_rate':float(np.mean((b<np.nanmin(a))|(b>np.nanmax(a))))})
    ranked=sorted(records,key=lambda x:(-x['psi'],-abs(x['standardized_mean_difference'])))
    return {'features':records,'top_drift_features':[x['feature'] for x in ranked[:10]],
     'stable_features':[x['feature'] for x in sorted(records,key=lambda x:x['psi'])[:10]],
     'analysis_used_for_tuning':False}
