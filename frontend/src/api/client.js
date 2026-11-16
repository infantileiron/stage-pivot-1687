const token=()=>localStorage.getItem('token');
function detailText(detail,statusText){
 if(typeof detail==='string')return detail;
 if(Array.isArray(detail))return detail.map(d=>String(d.msg||d).replace(/^Value error,\s*/,'')).join('；');
 if(detail)return JSON.stringify(detail);
 return statusText;
}
export async function api(path,options={}){
 const r=await fetch('/api'+path,{...options,headers:{'Content-Type':'application/json',
  ...(token()?{Authorization:'Bearer '+token()}:{}),...options.headers}});
 if(!r.ok){const e=await r.json().catch(()=>({detail:r.statusText}));throw Error(detailText(e.detail,r.statusText))}
 return r.json();
}
export const post=(path,data)=>api(path,{method:'POST',body:JSON.stringify(data)});
