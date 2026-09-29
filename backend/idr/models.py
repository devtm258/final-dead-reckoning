"""Versioned tree and compact causal neural models. NumPy neural inference needs no torch."""
from __future__ import annotations
import json, os
from pathlib import Path
import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from threadpoolctl import threadpool_limits
from .data import sequence_indices, windows, tree_features

THREADS=max(1,int(os.getenv('IDR_THREADS','2')))
threadpool_limits(limits=THREADS)

def scores(y,p,var=None):
    good=np.isfinite(y)&np.isfinite(p); y=y[good];p=p[good]
    if len(y)<2:return {'mae':None,'rmse':None,'r2':None,'n':len(y)}
    r={'mae':float(mean_absolute_error(y,p)),'rmse':float(np.sqrt(mean_squared_error(y,p))), 'r2':float(r2_score(y,p)),'bias':float(np.mean(p-y)),'p95_abs_error':float(np.quantile(abs(y-p),.95)),'n':len(y)}
    if var is not None:
        sd=np.sqrt(np.maximum(var[good],1e-4));r.update(coverage_1sigma=float(np.mean(abs(y-p)<=sd)),coverage_2sigma=float(np.mean(abs(y-p)<=2*sd)))
    return r


def make_net(kind):
    import torch
    from torch import nn
    class Causal(nn.Module):
        def __init__(self,ci,co,d=1):
            super().__init__();self.pad=2*d;self.conv=nn.Conv1d(ci,co,3,dilation=d)
        def forward(self,x):return self.conv(torch.nn.functional.pad(x,(self.pad,0)))
    class Block(nn.Module):
        def __init__(self,ci,co,d):
            super().__init__();self.c1=Causal(ci,co,d);self.c2=Causal(co,co,d);self.skip=nn.Conv1d(ci,co,1) if ci!=co else nn.Identity()
        def forward(self,x):return torch.relu(self.c2(torch.relu(self.c1(x)))+self.skip(x))
    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            if kind=='tcn':
                self.blocks=nn.ModuleList([Block(6,24,1),Block(24,24,2),Block(24,24,4)])
                self.head=nn.Conv1d(24,2,1)
            else:
                self.enc=Causal(6,24);self.gru=nn.GRU(24,32,batch_first=True);self.head=nn.Linear(32,2)
        def forward(self,x):
            if kind=='tcn':
                for block in self.blocks:x=block(x)
                return self.head(x).transpose(1,2)
            x=torch.relu(self.enc(x)).transpose(1,2);x,_=self.gru(x);return self.head(x)
    return Net()


def conv(x,w,b,d=1):
    k=w.shape[2];a=np.pad(x,((0,0),(0,0),(d*(k-1),0)));n=x.shape[2]
    y=np.zeros((x.shape[0],w.shape[0],n),np.float32)
    for j in range(k): y+=np.einsum('bct,oc->bot',a[:,:,j*d:j*d+n],w[:,:,j],optimize=True)
    return y+b[None,:,None]

def np_forward(kind,x,s):
    if kind=='tcn':
        for i,d in enumerate([1,2,4]):
            p=f'blocks.{i}.'
            z=np.maximum(conv(x,s[p+'c1.conv.weight'],s[p+'c1.conv.bias'],d),0)
            z=conv(z,s[p+'c2.conv.weight'],s[p+'c2.conv.bias'],d)
            skip=conv(x,s[p+'skip.weight'],s[p+'skip.bias']) if p+'skip.weight' in s else x
            x=np.maximum(z+skip,0)
        return conv(x,s['head.weight'],s['head.bias']).transpose(0,2,1)
    x=np.maximum(conv(x,s['enc.conv.weight'],s['enc.conv.bias']),0).transpose(0,2,1)
    h=np.zeros((len(x),32),np.float32);outs=[]
    def sig(a):return 1/(1+np.exp(-np.clip(a,-40,40)))
    for j in range(x.shape[1]):
        gi=x[:,j]@s['gru.weight_ih_l0'].T+s['gru.bias_ih_l0'];gh=h@s['gru.weight_hh_l0'].T+s['gru.bias_hh_l0']
        ir,iz,inn=np.split(gi,3,axis=1);hr,hz,hn=np.split(gh,3,axis=1)
        r=sig(ir+hr);z=sig(iz+hz);n=np.tanh(inn+r*hn);h=(1-z)*n+z*h
        outs.append(h@s['head.weight'].T+s['head.bias'])
    return np.stack(outs,axis=1)

class Predictor:
    def __init__(self,folder):
        self.folder=Path(folder);self.meta=json.loads((self.folder/'metadata.json').read_text());self.kind=self.meta['kind'];self.window=self.meta['window']
        if self.kind in ('extra_trees','random_forest'):
            self.model=joblib.load(self.folder/'model.joblib');self.model.n_jobs=1
        else:
            self.weights=dict(np.load(self.folder/'weights.npz'));self.mean=np.array(self.meta['normalization_mean'],np.float32)[None,:,None];self.std=np.array(self.meta['normalization_std'],np.float32)[None,:,None]
    def raw(self,w):
        if self.kind in ('extra_trees','random_forest'):
            p=self.model.predict(tree_features(w));return p,np.full(len(p),self.meta.get('residual_variance',4.))
        z=np_forward(self.kind,(w-self.mean)/self.std,self.weights)[:,-1]
        return z[:,0],np.exp(np.clip(z[:,1],-5,5))
    def predict(self,w):
        p,v=self.raw(w)
        return np.clip(p,0,60),np.clip(v*self.meta.get('variance_scale',1.),.04,400.)
    def sequence(self,d):
        ids=sequence_indices(d,self.window);p=np.full(len(d),np.nan);v=np.full(len(d),np.nan)
        for start in range(0,len(ids),128):
            ix=ids[start:start+128];p[ix],v[ix]=self.predict(windows(d,ix,self.window))
        return p,v
