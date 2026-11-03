import {NextResponse} from 'next/server';

const protectedPaths=['/dashboard','/manage','/payments','/operations','/settings','/clients','/services'];

export async function middleware(request){
 const path=request.nextUrl.pathname;
 if(!protectedPaths.some(prefix=>path===prefix||path.startsWith(prefix+'/')))return NextResponse.next();
 try{
  // The browser reaches us through the TLS-terminating proxy. Preserve that
  // scheme for this internal session probe so Django does not SSL-redirect it.
  const response=await fetch('http://backend:8000/api/session/',{headers:{cookie:request.headers.get('cookie')||'',host:request.headers.get('host')||'localhost','x-forwarded-proto':'https','x-forwarded-host':request.headers.get('host')||'localhost'},cache:'no-store'});
  if(response.ok)return NextResponse.next();
 }catch{}
 const login=new URL('/login',request.url);
 login.searchParams.set('next',path+request.nextUrl.search);
 return NextResponse.redirect(login);
}

export const config={matcher:['/dashboard/:path*','/manage/:path*','/payments/:path*','/operations/:path*','/settings/:path*','/clients/:path*','/services/:path*']};
