'use client';
import {useEffect,useState} from 'react';
import {usePathname,useRouter} from 'next/navigation';

export default function RequireAuth({children}){
 const [ready,setReady]=useState(false);const router=useRouter();const pathname=usePathname();
 useEffect(()=>{let alive=true;fetch('/api/session/',{credentials:'include'}).then(r=>{
  if(!alive)return;
  if(r.ok)setReady(true);else router.replace('/login?next='+encodeURIComponent(pathname));
 }).catch(()=>{if(alive)router.replace('/login?next='+encodeURIComponent(pathname))});return()=>{alive=false}},[pathname,router]);
 return ready?children:<main className="p-8">Checking session…</main>;
}
