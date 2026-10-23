'use client';
import {useState} from 'react';

function safeDestination(){
 const next=new URLSearchParams(window.location.search).get('next');
 return next&&next.startsWith('/')&&!next.startsWith('//')?next:'/dashboard';
}
export default function Login(){
 const [username,setUsername]=useState(''),[password,setPassword]=useState(''),[error,setError]=useState('');
 async function signIn(){
  await fetch('/api/csrf/',{credentials:'include'});
  const response=await fetch('/api/login/',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json','X-CSRFToken':document.cookie.match(/csrftoken=([^;]+)/)?.[1]||''},body:JSON.stringify({username,password})});
  if(response.ok)location.assign(safeDestination());else setError('Invalid credentials');
 }
 return <main className="max-w-sm mx-auto mt-24 card"><h1 className="text-2xl font-bold">3B Smart Solutions</h1><p className="muted">Administrator sign in</p><input className="border p-2 w-full my-2" placeholder="Username" onChange={event=>setUsername(event.target.value)}/><input className="border p-2 w-full my-2" type="password" placeholder="Password" onChange={event=>setPassword(event.target.value)}/>{error&&<p className="text-red-600">{error}</p>}<button className="btn w-full" onClick={signIn}>Sign in</button></main>;
}
