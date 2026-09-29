"""JSON-lines edge process: first line config, subsequent lines live IMU samples.
Example config: {"model_id":"...", "origin":[52,-1], "heading_deg":0, "speed":0,
"sensor_to_vehicle":[[1,0,0],[0,1,0],[0,0,1]]}
Sample: {"t":0.1,"accel":[0,0,9.80665],"gyro":[0,0,0],"gravity":[0,0,9.80665]}
"""
import json,sys
from idr.storage import get_model
from idr.edge import EdgeEngine
if __name__=='__main__':
 c=json.loads(sys.stdin.readline());m=get_model(c.pop('model_id'));engine=EdgeEngine(m,**c)
 for line in sys.stdin:
    try:print(json.dumps(engine.step(json.loads(line)),allow_nan=False),flush=True)
    except Exception as exc:print(json.dumps({'error':str(exc),'reinitialize_required':True}),flush=True)
