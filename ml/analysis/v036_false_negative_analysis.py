"""Post-hoc attack false-negative analysis; tuning is prohibited."""
def analyze(frame):return frame[(frame.label!='benign')&(frame.prediction=='benign')].to_dict('records')
