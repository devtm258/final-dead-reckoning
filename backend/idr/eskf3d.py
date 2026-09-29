"""15-error-state strapdown engine for calibrated external/phone IMUs.
Inputs: right-handed body x-forward/y-left/z-up, specific force m/s², gyro rad/s.
Navigation frame: ENU. Requires a verified sensor-to-vehicle rotation upstream.
Unlike dashboard planar replay, this engine supports 3D motion and biases.
"""
import numpy as np
from scipy.spatial.transform import Rotation

def skew(a):
    x,y,z=a;return np.array([[0,-z,y],[z,0,-x],[-y,x,0.]])

class ESKF3D:
    def __init__(self,position=None,velocity=None,rotation=None):
        self.p=np.zeros(3) if position is None else np.asarray(position,float).copy()
        self.v=np.zeros(3) if velocity is None else np.asarray(velocity,float).copy()
        self.R=np.eye(3) if rotation is None else np.asarray(rotation,float).copy()
        self.ba=np.zeros(3);self.bg=np.zeros(3);self.P=np.diag([16.]*3+[4.]*3+[.05]*3+[.1]*3+[.005]*3);self.rejected=0
    def predict(self,accel,gyro,dt):
        if not 0<dt<=.5:raise ValueError('Invalid IMU dt; reinitialize after gaps.')
        f=np.asarray(accel)-self.ba;w=np.asarray(gyro)-self.bg
        a=self.R@f+np.array([0,0,-9.80665]);self.p+=self.v*dt+.5*a*dt**2;self.v+=a*dt
        F=np.eye(15);F[:3,3:6]=np.eye(3)*dt;F[3:6,6:9]=-self.R@skew(f)*dt;F[3:6,9:12]=-self.R*dt
        F[6:9,6:9]-=skew(w)*dt;F[6:9,12:15]=-np.eye(3)*dt
        self.R=self.R@Rotation.from_rotvec(w*dt).as_matrix()
        Q=np.diag([1e-5]*3+[.15]*3+[.001]*3+[1e-5]*3+[1e-7]*3)*dt
        self.P=F@self.P@F.T+Q
    def update(self,residual,H,V,gate=16.):
        S=H@self.P@H.T+V;r=np.atleast_1d(residual)
        if gate and r@np.linalg.solve(S,r)>gate:self.rejected+=1;return False
        K=np.linalg.solve(S,(self.P@H.T).T).T;dx=K@r;self.p+=dx[:3];self.v+=dx[3:6];self.R=self.R@Rotation.from_rotvec(dx[6:9]).as_matrix();self.ba+=dx[9:12];self.bg+=dx[12:15]
        A=np.eye(15)-K@H;P=A@self.P@A.T+K@V@K.T
        G=np.eye(15);G[6:9,6:9]-=.5*skew(dx[6:9]);self.P=G@P@G.T;self.P=(self.P+self.P.T)*.5;return True
    def position(self,z,variance=9.):
        H=np.zeros((3,15));H[:,:3]=np.eye(3);return self.update(np.asarray(z)-self.p,H,np.eye(3)*variance)
    def body_velocity(self,z,variance,axes=(0,1,2)):
        vb=self.R.T@self.v;H=np.zeros((3,15));H[:,3:6]=self.R.T;H[:,6:9]=skew(vb);a=list(axes)
        return self.update(np.asarray(z)-vb[a],H[a],np.diag(np.broadcast_to(variance,len(a))))
    def learned_speed(self,speed,variance):return self.body_velocity([speed],[variance],(0,))
    def nhc(self,lateral_var=.1,vertical_var=.3):return self.body_velocity([0,0],[lateral_var,vertical_var],(1,2))
    def zupt(self):
        H=np.zeros((3,15));H[:,3:6]=np.eye(3);return self.update(-self.v,H,np.eye(3)*.01)
    def zero_angular_rate(self,gyro):
        H=np.zeros((3,15));H[:,12:15]=np.eye(3);return self.update(np.asarray(gyro)-self.bg,H,np.eye(3)*1e-5)
