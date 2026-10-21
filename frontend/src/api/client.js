let csrf='';
export class ApiError extends Error {constructor(status,data){super(data?.error?.message||'요청을 처리할 수 없습니다.');this.status=status;this.data=data}}
export async function refreshCsrf(){const r=await fetch('/api/v1/auth/csrf');csrf=(await r.json()).csrf_token}
export async function api(path,options={}){
 const method=options.method||'GET';if(method!=='GET'&&!csrf)await refreshCsrf();
 const headers={...options.headers};if(method!=='GET'){headers['X-CSRF-Token']=csrf;headers['Idempotency-Key']=options.key||crypto.randomUUID()}
 if(options.etag)headers['If-Match']=options.etag;
 let body=options.body;if(body&&!(body instanceof FormData)){headers['Content-Type']='application/json';body=JSON.stringify(body)}
 const r=await fetch('/api/v1'+path,{method,headers,body,signal:options.signal});const data=r.status===204?null:await r.json();if(!r.ok)throw new ApiError(r.status,data);
 if(data?.csrf_token)csrf=data.csrf_token;return {data,etag:r.headers.get('ETag')}
}
export const get=async(path)=>(await api(path)).data;
