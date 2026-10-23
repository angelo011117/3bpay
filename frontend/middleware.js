import {NextResponse} from 'next/server';

const protectedPaths=['/dashboard','/manage','/payments','/operations','/settings','/clients','/services'];

export async function middleware(request){
 const path=request.nextUrl.pathname;
 if(!protectedPaths.some(prefix=>path===prefix||path.startsWith(prefix+'/')))return NextResponse.next();
 try{
  const response=await fetch('http://backend:8000/api/session/',{headers:{cookie:request.headers.get('cookie')||'',host:request.headers.get('host')||'localhost'},cache:'no-store'});
  if(response.ok)return NextResponse.next();
 }catch{}
 const login=new URL('/login',request.url);
 login.searchParams.set('next',path+request.nextUrl.search);
 return NextResponse.redirect(login);
}

export const config={matcher:['/dashboard/:path*','/manage/:path*','/payments/:path*','/operations/:path*','/settings/:path*','/clients/:path*','/services/:path*']};
