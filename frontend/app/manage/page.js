'use client';
import {useEffect,useState} from 'react';
import Nav from '../../components/Nav';
import RequireAuth from '../../components/RequireAuth';
const csrf=()=>document.cookie.match(/csrftoken=([^;]+)/)?.[1]||'';
const api=(url,opts={})=>fetch('/api/'+url,{credentials:'include',headers:{'Content-Type':'application/json','X-CSRFToken':csrf(),...(opts.headers||{})},...opts});
export default function Manage(){
 const [tab,setTab]=useState('clients'),[rows,setRows]=useState([]),[form,setForm]=useState({});
 const load=()=>api(tab+'/').then(r=>r.ok?r.json():[]).then(setRows);
 useEffect(()=>{load();setForm({})},[tab]);
 const save=async()=>{const response=await api(tab+'/',{method:'POST',body:JSON.stringify(form)});if(!response.ok)alert((await response.json()).detail||'Check fields');else{setForm({});load()}};
 const fields=tab==='clients'?['business_name','contact_name','email','phone']:tab==='services'?['client','name','domain','amount','frequency','start_date','next_due_date']:['amount','payer_name','recipient_account','transaction_id','source','notes'];
 return <RequireAuth><main className="max-w-6xl mx-auto p-6"><h1 className="text-3xl font-bold">Management</h1><Nav/><div className="flex gap-2 mb-4">{['clients','services','payments'].map(x=><button className="btn" key={x} onClick={()=>setTab(x)}>{x}</button>)}</div><div className="card mb-5"><h2 className="font-bold">Create {tab.slice(0,-1)}</h2><div className="grid md:grid-cols-3 gap-2 mt-3">{fields.map(key=><input className="border p-2" key={key} placeholder={key} value={form[key]||''} onChange={event=>setForm({...form,[key]:event.target.value})}/>)}</div><button className="btn mt-3" onClick={save}>Save</button><p className="muted mt-2">For services use the numeric client ID shown in the Clients list; frequency is monthly or yearly.</p></div><div className="space-y-2">{rows.map(row=><div className="card" key={row.id}><b>{row.business_name||row.name||row.payer_name}</b> <span className="muted">#{row.id} · {row.email||row.domain||('$'+row.amount)} · {row.status||''}</span>{tab==='clients'&&<a className="ml-3 underline" href={'/clients/'+row.id}>Details & aliases</a>}{tab==='services'&&<a className="ml-3 underline" href={'/services/'+row.id}>Details</a>}</div>)}</div></main></RequireAuth>;
}
