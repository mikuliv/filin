"""Post-hoc false-positive analysis; tuning is prohibited."""
def analyze(frame):return frame[(frame.label=='benign')&(frame.prediction!='benign')].to_dict('records')
