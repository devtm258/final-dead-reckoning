const API='/api';
export async function request(path,options={}){
 const response=await fetch(`${API}${path}`,options);
 const result=await response.json().catch(()=>({detail:response.statusText}));
 if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:JSON.stringify(result.detail));
 return result;
}
export const json=(path,value)=>request(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});
export const listDatasets=()=>request('/datasets');
export const listModels=()=>request('/models');
export const listJobs=()=>request('/jobs');
export function pairFiles(files){
 const byDir=new Map();
 for(const file of files){
  if(!/\.csv(\.gz)?$/i.test(file.name))continue;
  const dir=(file.webkitRelativePath||file.name).split('/').slice(0,-1).join('/')||file.name.replace(/^[SV]-?/i,'').replace(/\.csv(\.gz)?$/i,'');
  const entry=byDir.get(dir)||{};
  if(/^S[-_]/i.test(file.name))entry.smartphone=file;
  if(/^V[-_]/i.test(file.name))entry.vbox=file;
  byDir.set(dir,entry);
 }
 return [...byDir.entries()].filter(([,v])=>v.smartphone).map(([dir,v])=>({dir,...v}));
}
export async function uploadPair(smartphone,vbox){
 const form=new FormData();form.append('smartphone',smartphone);if(vbox)form.append('vbox',vbox);
 form.append('speed_unit','auto');form.append('alignment','motion');
 return request('/dataset/upload',{method:'POST',body:form});
}
