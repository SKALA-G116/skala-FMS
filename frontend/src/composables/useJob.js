import {ref,onUnmounted} from 'vue';import {api} from '../api/client';
export function useJob(){const job=ref(null);let timer,controller,attempt=0,disposed=false;
 const stop=()=>{clearTimeout(timer);controller?.abort()};
 async function poll(id,done){if(disposed)return;if(document.hidden){timer=setTimeout(()=>poll(id,done),5000);return}controller=new AbortController();try{job.value=(await api('/jobs/'+id,{signal:controller.signal})).data;if(['succeeded','partial','failed','cancelled'].includes(job.value.status)){done?.(job.value);return}}catch(e){if(e.name==='AbortError')return}timer=setTimeout(()=>poll(id,done),[2000,5000,10000][Math.min(attempt++,2)])}
 const start=(id,done)=>{stop();attempt=0;poll(id,done)};onUnmounted(()=>{disposed=true;stop()});return {job,start,stop}}
