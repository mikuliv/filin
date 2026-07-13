"""Post-hoc качество сетевого наблюдения."""
def analyze(frame):
 return {'rows':len(frame),'mean_flow_count':float(frame.flow_count.mean()),'mean_event_count':float(frame.window_event_count.mean()),'minimum_event_count':int(frame.window_event_count.min()),'empty_windows':int((frame.window_event_count==0).sum()),'errors':int((frame.label!=frame.prediction).sum())}
