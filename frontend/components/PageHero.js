export default function PageHero({title,subtitle,eyebrow='3B SMART SOLUTIONS',compact=false}){
 return <section className={'page-hero '+(compact?'page-hero-compact':'')}><span className="brand-kicker">{eyebrow}</span><h1>{title}</h1>{subtitle&&<p>{subtitle}</p>}</section>;
}
