"""Export compact neural weights to JSON and optionally ONNX for native mobile integration."""
import argparse,json
from idr.storage import get_model
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('model_id');p.add_argument('--onnx',action='store_true');a=p.parse_args();m=get_model(a.model_id)
 if m.kind not in ('tcn','cnn_gru'):raise SystemExit('JSON neural export requires TCN or CNN-GRU; tree inference remains available through joblib.')
 out={'metadata':m.meta,'weights':{k:{'shape':list(v.shape),'data':v.flatten().tolist()} for k,v in m.weights.items()}}
 (m.folder/'portable.json').write_text(json.dumps(out,separators=(',',':')))
 print(m.folder/'portable.json')
 if a.onnx:
    import torch
    from idr.models import make_net
    net=make_net(m.kind).eval();net.load_state_dict({k:torch.tensor(v) for k,v in m.weights.items()})
    torch.onnx.export(net,torch.zeros(1,6,m.window),str(m.folder/'model.onnx'),input_names=['normalized_imu'],output_names=['speed_logvariance_sequence'],opset_version=17,dynamo=False)
    print('ONNX exported: preprocessing and variance calibration are in metadata.json; validate target-runtime parity.')
