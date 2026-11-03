'use client';
import {useState} from 'react';

function safeDestination(){
 const next=new URLSearchParams(window.location.search).get('next');
 return next&&next.startsWith('/')&&!next.startsWith('//')?next:'/dashboard';
}
export default function Login(){
 const [username,setUsername]=useState(''),[password,setPassword]=useState(''),[error,setError]=useState(''),[submitting,setSubmitting]=useState(false);
 async function signIn(){
  if(submitting)return;
  setError('');setSubmitting(true);
  try{
   const csrfResponse=await fetch('/api/csrf/',{credentials:'include',cache:'no-store'});
   if(!csrfResponse.ok)throw new Error('csrf');
   const response=await fetch('/api/login/',{method:'POST',credentials:'include',cache:'no-store',headers:{'Content-Type':'application/json','X-CSRFToken':document.cookie.match(/csrftoken=([^;]+)/)?.[1]||''},body:JSON.stringify({username,password})});
   if(response.ok){location.assign(safeDestination());return;}
   if(response.status===400)setError('Username or password is incorrect.');
   else if(response.status===403)setError('Your security session expired. Please try again.');
   else setError('Sign-in is temporarily unavailable. Please try again.');
  }catch(error){setError('Unable to contact the sign-in service. Check your connection and try again.');}
  finally{setSubmitting(false);}
 }
 return <main className="max-w-sm mx-auto mt-24 card"><h1 className="text-2xl font-bold">3B Smart Solutions</h1><p className="muted">Administrator sign in</p><label className="sr-only" htmlFor="username">Username</label><input id="username" className="border p-2 w-full my-2" autoComplete="username" placeholder="Username" onChange={event=>setUsername(event.target.value)}/><label className="sr-only" htmlFor="password">Password</label><input id="password" className="border p-2 w-full my-2" type="password" autoComplete="current-password" placeholder="Password" onChange={event=>setPassword(event.target.value)}/>{error&&<p className="text-red-600" role="alert">{error}</p>}<button className="btn w-full" type="button" disabled={submitting} onClick={signIn}>{submitting?'Signing in…':'Sign in'}</button></main>;
}
