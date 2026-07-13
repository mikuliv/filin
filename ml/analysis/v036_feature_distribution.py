"""Post-hoc feature distribution helpers."""
def summarize(frame,features):return {f:{'mean':float(frame[f].mean()),'median':float(frame[f].median()),'zero_rate':float((frame[f]==0).mean()),'missing_rate':float(frame[f].isna().mean())} for f in features}
