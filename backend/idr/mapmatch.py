"""Offline causal multi-hypothesis road matcher. GeoJSON LineStrings, ENU projection.
Independent diagnostic output: not fed back as independent GNSS into the filter.
Road graph uses shared endpoints; grade separation respected via layer property.
"""
import json
import numpy as np
from .data import enu,geographic

class RoadMatcher:
    def __init__(self,geojson,origin,radius=60,beam=8):
        if isinstance(geojson,str):geojson=json.loads(geojson)
        self.origin=origin;self.radius=radius;self.beam=beam;self.edges=[];self.previous=[]
        for feature in geojson['features']:
            g=feature['geometry'];pr=feature.get('properties',{})
            lines=[g['coordinates']] if g['type']=='LineString' else g['coordinates'] if g['type']=='MultiLineString' else []
            for line in lines:
                ll=np.asarray(line);xy=enu(ll[:,1],ll[:,0],origin)
                for a,b in zip(xy[:-1],xy[1:]):
                    if np.linalg.norm(b-a)>0:self.edges.append((a,b,str(pr.get('layer',0)),pr.get('oneway') in (True,'yes','1')))
        if not self.edges:raise ValueError('Road GeoJSON has no usable LineString edges.')
    def step(self,xy,heading,distance,sigma=15):
        xy=np.asarray(xy);candidates=[]
        for j,(a,b,layer,oneway) in enumerate(self.edges):
            vec=b-a;u=np.clip((xy-a)@vec/(vec@vec),0,1);q=a+u*vec;dist=np.linalg.norm(q-xy)
            if dist>self.radius:continue
            h=np.arctan2(vec[1],vec[0]);dh=abs((h-heading+np.pi)%(2*np.pi)-np.pi)
            if not oneway:dh=min(dh,np.pi-dh)
            cost=.5*(dist/max(sigma,5))**2+2*dh**2
            if self.previous:
                trans=[]
                for old in self.previous:
                    oa,ob,ol,_=self.edges[old['edge']]
                    connected=(j==old['edge'] or (ol==layer and min(np.linalg.norm(a-oa),np.linalg.norm(a-ob),np.linalg.norm(b-oa),np.linalg.norm(b-ob))<2))
                    if connected:trans.append(old['cost']+abs(np.linalg.norm(q-old['point'])-distance)/max(5,sigma))
                if not trans:continue
                cost+=min(trans)
            candidates.append({'edge':j,'point':q,'cost':float(cost)})
        if not candidates:self.previous=[];return {'matched':False,'position':geographic([xy],self.origin)[0].tolist()}
        candidates.sort(key=lambda c:c['cost']);self.previous=candidates[:self.beam];minimum=candidates[0]['cost']
        for c in self.previous:c['cost']-=minimum
        return {'matched':True,'position':geographic([self.previous[0]['point']],self.origin)[0].tolist(),'hypotheses':len(self.previous),'margin':float(self.previous[1]['cost']) if len(self.previous)>1 else None}
