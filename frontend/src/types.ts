export type Word = {text:string;start:number;end:number;confidence:number|null;review:boolean};
export type Sentence = {id:string;text:string;start:number;end:number;review:boolean;reason:string;accent:boolean;words:Word[]};
export type Style = {template:'dark'|'gold'|'paper'|'typewriter';font:'serif'|'sans'|'mono';background:string;foreground:string;accent:string;font_size:number;line_height:number;transition:number;position:number;safe_top:number;safe_bottom:number;safe_left:number;safe_right:number;grain:number};
export type Project = {id:string;name:string;text:string;style:Style;sentences:Sentence[];audio:{duration:number;filename:string;sample_rate:number;channels:number;waveform:number[]};alignment:null|{engine:string;model?:string}};
export type Job = {id:string;kind:string;status:string;progress:number;message:string;result?:Project|{files:Record<string,string>}};
export type Scene = {digest:string;width:number;height:number;geometry:{x:number;y:number;gap:number;width:number;max_height:number};sprites:{file:string;width:number;height:number;font_size:number}[]};
export const defaultStyle:Style = {template:'dark',font:'serif',background:'#151719',foreground:'#F1E9D6',accent:'#D6AF70',font_size:78,line_height:1.25,transition:.6,position:0,safe_top:220,safe_bottom:340,safe_left:100,safe_right:160,grain:.025};
export const templates = [
 {id:'dark',name:'Dark Editorial',note:'Sessiz. Güçlü. Zamansız.',bg:'#151719',fg:'#F1E9D6',accent:'#D6AF70',font:'serif',mark:'Aa'},
 {id:'gold',name:'Cinematic Gold',note:'Sıcak bir sinema hissi.',bg:'#191812',fg:'#D6AF70',accent:'#F1E9D6',font:'serif',mark:'Aa'},
 {id:'paper',name:'Minimal Paper',note:'Kâğıdın yalın güzelliği.',bg:'#EAE5DA',fg:'#252720',accent:'#8F673F',font:'sans',mark:'Aa'},
 {id:'typewriter',name:'Typewriter',note:'Her kelimenin bir izi var.',bg:'#1B201E',fg:'#E3E2D6',accent:'#D6AF70',font:'mono',mark:'Aa'},
] as const;
export async function api<T>(url:string, options:RequestInit={}):Promise<T> {
 const res = await fetch('/api'+url, {...options, headers: options.body instanceof FormData ? options.headers : {'Content-Type':'application/json',...options.headers}});
 if(res.status===401)window.dispatchEvent(new Event('reels-auth-required'));
 if(!res.ok){let data; try {data=await res.json()}catch{throw Error('Sunucuya ulaşılamadı. Uygulamanın çalıştığını kontrol edin.')}; throw Error(typeof data.detail==='string'?data.detail:Array.isArray(data.detail)?data.detail.map((x:{msg:string})=>x.msg).join(' · '):'İşlem tamamlanamadı.')}
 return res.json();
}
export function editBody(p:Project){return {name:p.name,text:p.text,sentences:p.sentences,style:p.style}}
export function timeLabel(t:number){return `${Math.floor(t/60).toString().padStart(2,'0')}:${(t%60).toFixed(1).padStart(4,'0')}`}
