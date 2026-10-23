'use client';
import {useEffect,useState} from 'react';
import Nav from '../../components/Nav';
import RequireAuth from '../../components/RequireAuth';

export default function Dashboard(){
 const [data,setData]=useState(null);
 useEffect(()=>{fetch('/api/dashboard/',{credentials:'include'}).then(r=>r.ok?r.json():null).then(setData)},[]);
 return <RequireAuth>{!data?<main className="p-8">Loading...</main>:<main className="max-w-6xl mx-auto p-6"><header><h1 className="text-3xl font-bold">3B Smart Solutions</h1><p className="muted">Maintenance billing · <b>Simulation mode</b></p></header><Nav/><section className="grid md:grid-cols-3 gap-4">{Object.entries(data).map(([key,value])=><div className="card" key={key}><div className="muted">{key.replaceAll('_',' ')}</div><strong className="text-2xl">{String(value)}</strong></div>)}</section></main>}</RequireAuth>;
}
