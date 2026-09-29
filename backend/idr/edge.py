"""Stateful 3D edge runtime; PyTorch-free. Raw IMU adapter and explicit mounting rotation.
Use calibrated sensor frames. The dashboard's historical CSV adapter is separate.
"""
from collections import deque
import numpy as np
from scipy.spatial.transform import Rotation
from .eskf3d import ESKF3D
from .data import enu,geographic

class EdgeEngine:
    def __init__(self,predictor,origin,heading_deg=0,speed=0,sensor_to_vehicle=None):
        self.model=predictor;self.origin=origin;self.mount=np.eye(3) if sensor_to_vehicle is None else np.asarray(sensor_to_vehicle,float)
        if self.mount.shape!=(3,3) or not np.allclose(self.mount.T@self.mount,np.eye(3),atol=1e-4) or np.linalg.det(self.mount)<.99:raise ValueError('sensor_to_vehicle must be a proper 3x3 rotation matrix')
        yaw=np.deg2rad(90-heading_deg);R=Rotation.from_euler('z',yaw).as_matrix()
        self.filter=ESKF3D(velocity=R@np.array([speed,0,0.]),rotation=R)
        self.buffer=deque(maxlen=predictor.window);self.bucket=[];self.last=None;self.bucket_t=None;self.last_update=-1e9;self.last_fix=-1e9;self.stationary_time=0.;self.last_fix_speed=speed
    def step(self,sample):
        t=float(sample['t']);a=np.asarray(sample['accel'],float);w=np.asarray(sample['gyro'],float);g=np.asarray(sample['gravity'],float)
        if a.shape!=(3,) or w.shape!=(3,) or g.shape!=(3,) or not np.isfinite(np.r_[t,a,w,g]).all():raise ValueError('Finite timestamp and 3-axis accel/gyro/gravity required')
        if self.last is None:self.last=t;self.bucket_t=t;return {'warming_up':True}
        dt=t-self.last
        if not 0<dt<=.5:raise ValueError('Timestamp gap/reset; explicitly initialize a new stream')
        self.last=t;self.filter.predict(self.mount@a,self.mount@w,dt)
        self.bucket.append(np.r_[a-g,w]);mean=None;variance=None
        if t-self.bucket_t>=.099:
            # Causal box average anti-alias adapter. Match this acquisition recipe when training for device deployment.
            self.buffer.append(np.mean(self.bucket,axis=0));self.bucket=[];self.bucket_t=t
        if len(self.buffer)==self.buffer.maxlen and t-self.last_update>=.49:
            x=np.array(self.buffer,np.float32).T[None];p,v=self.model.predict(x);mean=float(p[0]);variance=float(v[0])*2;self.filter.learned_speed(mean,variance);self.last_update=t
            stopped=mean<.2 and variance<1 and self.last_fix_speed<.5 and np.linalg.norm(w)<.02 and np.linalg.norm(a-g)<.2
            self.stationary_time=self.stationary_time+.5 if stopped else 0
            if self.stationary_time>=1.5:self.filter.zupt();self.filter.zero_angular_rate(self.mount@w)
        self.filter.nhc(.1+2*np.linalg.norm(w)+.1*np.linalg.norm(a-g)**2,.3+np.linalg.norm(a-g)**2)
        fix=sample.get('gnss')
        if fix and fix.get('valid',True) and float(fix['t'])>self.last_fix and 0<=t-float(fix['t'])<=.5 and fix.get('accuracy',100)<=30:
            pos=enu([fix['lat']],[fix['lon']],self.origin)[0]
            # Only horizontal GNSS is supplied. Do not fabricate an altitude measurement.
            H=np.zeros((2,15));H[:,:2]=np.eye(2)
            if self.filter.update(pos-self.filter.p[:2],H,np.eye(2)*max(4,fix['accuracy']**2),25):
                self.last_fix=float(fix['t']);self.last_fix_speed=float(fix.get('speed',np.linalg.norm(self.filter.v)))
        ll=geographic([self.filter.p[:2]],self.origin)[0]
        return {'t':t,'latitude':float(ll[0]),'longitude':float(ll[1]),'height_relative_m':float(self.filter.p[2]),'speed':float(np.linalg.norm(self.filter.v)),'mode':'GNSS_AIDED' if t-self.last_fix<1.5 else 'DEAD_RECKONING','ml_speed':mean,'ml_variance':variance,'warming_up':len(self.buffer)<self.buffer.maxlen,'position_sigma_m':np.sqrt(np.diag(self.filter.P)[:3]).tolist()}
