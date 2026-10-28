'use client';

import {useEffect,useState} from 'react';

function CopyButton({label,value}){
 const [message,setMessage]=useState('');
 const copy=async()=>{
  try{
   if(!navigator.clipboard?.writeText) throw new Error('Clipboard access is unavailable');
   await navigator.clipboard.writeText(value);
   setMessage('Copied');
  }catch(error){
   setMessage('Copy failed. Select the value and copy it manually.');
  }
 };
 return <span className="inline-flex items-center gap-2">
  <button type="button" className="copy-button" onClick={copy} aria-label={`Copy ${label}`} title={`Copy ${label}`}><span aria-hidden="true">⧉</span></button>
  <span className="copy-status" role="status" aria-live="polite">{message}</span>
 </span>;
}

function PaymentValue({label,value,copyValue}){
 return <div className="payment-value">
  <span className="payment-label">{label}</span>
  <div className="flex items-center gap-2"><span className="payment-text" tabIndex="0">{value}</span><CopyButton label={label} value={copyValue}/></div>
 </div>;
}

export default function Portal({params}){
 const [details,setDetails]=useState();
 useEffect(()=>{params.then(({token})=>fetch(`/api/public/${token}/`).then(response=>response.json()).then(setDetails))},[params]);
 if(!details)return <main className="p-8">Loading secure payment details…</main>;
 const contact=details.zelle_recipient||'Contact 3B Smart Solutions';
 return <main className="max-w-xl mx-auto p-4 sm:p-6"><div className="card">
  <h1 className="text-2xl font-bold">{details.brand}</h1><p>{details.description} · {details.domain}</p><hr className="my-4"/>
  <p>Period: {details.period}</p>
  <PaymentValue label="Amount" value={`$${details.amount}`} copyValue={String(details.amount)}/>
  <PaymentValue label="Zelle contact" value={contact} copyValue={contact}/>
  <p>Balance: ${details.balance}</p><p>Due: {details.due_date} · Grace deadline: {details.grace_ends}</p>
  {details.qr_url?<><img className="max-w-56" src={details.qr_url} alt="Official American Express Zelle QR"/><a className="underline" href={details.qr_url} download>Download official QR</a></>:<p className="muted">No official QR has been uploaded. Use the Zelle contact above.</p>}
  <p className="mt-5">Payments are detected automatically. Your balance will update after verification. You do not need to submit a payment confirmation.</p>
 </div></main>;
}
