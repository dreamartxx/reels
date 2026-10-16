import {useRef,useState} from 'react';
import {AudioLines,MousePointer2,Minus,Plus} from 'lucide-react';
import {Project,Sentence,timeLabel} from './types';

export function Timeline({project,time,selected,onSelect,onSeek,onChange,disabled}:{project:Project|null;time:number;selected:string|null;onSelect:(id:string)=>void;onSeek:(t:number)=>void;onChange:(s:Sentence[])=>void;disabled:boolean}){
 const [zoom,setZoom]=useState(1);
 const track=useRef<HTMLDivElement>(null);
 const audioDuration=project?.audio.duration||20;
 const duration=project?.background?.duration||audioDuration;
 const drag=useRef<{id:string;kind:string;x:number;start:number;end:number;original:Sentence[]}|null>(null);
 function seek(e:React.PointerEvent){if(!track.current||!project)return;const r=track.current.getBoundingClientRect();onSeek(Math.max(0,Math.min(duration,(e.clientX-r.left)/r.width*duration)))}
 function begin(e:React.PointerEvent,s:Sentence,kind:string){e.stopPropagation();onSelect(s.id);if(disabled||!project)return;e.currentTarget.setPointerCapture(e.pointerId);drag.current={id:s.id,kind,x:e.clientX,start:s.start,end:s.end,original:project.sentences}}
 function move(e:React.PointerEvent){
  const d=drag.current;if(!d||!track.current)return;
  const delta=(e.clientX-d.x)/track.current.getBoundingClientRect().width*duration;
  const idx=d.original.findIndex(s=>s.id===d.id),min=idx?d.original[idx-1].end:0,max=idx+1<d.original.length?d.original[idx+1].start:audioDuration;
  let start=d.start,end=d.end;
  if(d.kind==='move'){start=Math.max(min,Math.min(max-(d.end-d.start),d.start+delta));end=start+d.end-d.start}
  else if(d.kind==='start')start=Math.max(min,Math.min(d.end-.04,d.start+delta));
  else end=Math.max(d.start+.04,Math.min(max,d.end+delta));
  onChange(d.original.map(s=>s.id===d.id?{...s,start,end,review:true,reason:'Zaman elle değiştirildi; dinleyip onaylayın.',words:[]}:s));
 }
 return <section className="timeline panel">
  <div className="timeline-title"><div><AudioLines size={17}/><h2>Zaman çizelgesi</h2><span className="pill">{project?.sentences.length||0} cümle</span></div><div className="timeline-tools"><span className="muted hint"><MousePointer2 size={13}/> Taşı • Kenarlardan süreyi ayarla</span><button className="icon ghost" title="Zaman çizelgesini uzaklaştır" disabled={zoom<=1} onClick={()=>setZoom(Math.max(1,zoom-1))}><Minus size={13}/></button><span className="zoom-label">{zoom}×</span><button className="icon ghost" title="Zaman çizelgesini yakınlaştır" disabled={zoom>=8} onClick={()=>setZoom(Math.min(8,zoom+1))}><Plus size={13}/></button></div></div>
  <div className="timeline-scroll"><div className="timeline-track" ref={track} style={{width:`${zoom*100}%`}}>
   <div className="ruler" onPointerDown={seek}>{Array.from({length:9},(_,i)=><span key={i} style={{left:`${i/8*100}%`}}>{timeLabel(duration*i/8)}</span>)}</div>
   <div className="waveform" onPointerDown={seek}>
    <svg style={{width:`${audioDuration/duration*100}%`}} viewBox="0 0 1600 64" preserveAspectRatio="none" role="img" aria-label="Ses dalga formu"><path d={(project?.audio.waveform||Array.from({length:400},()=>.03)).map((v,i,a)=>`M${i/a.length*1600},${32-v*28}v${Math.max(1,v*56)}`).join(' ')} stroke="currentColor" strokeWidth="1.1"/></svg>
    <span className="wave-name">{project?.audio.filename||'Ses dosyanız burada görünecek'}</span>
   </div>
   <div className="sentence-lane" onPointerDown={seek}>
    {project?.sentences.map((s,i)=><div key={s.id} role="button" tabIndex={0} aria-label={`${i+1}. cümle: ${s.text}`} aria-pressed={selected===s.id} className={`sentence-block ${selected===s.id?'selected':''} ${s.review?'review':''}`} style={{left:`${s.start/duration*100}%`,width:`${(s.end-s.start)/duration*100}%`}} onPointerDown={e=>begin(e,s,'move')} onPointerMove={move} onPointerUp={()=>drag.current=null} onPointerCancel={()=>drag.current=null} onKeyDown={e=>{if(e.key==='Enter'){onSelect(s.id);onSeek(s.start)}}}>
     <span className="resize left" onPointerDown={e=>begin(e,s,'start')} aria-label="Başlangıç tutamacı"/>
     <span className="block-text">{String(i+1).padStart(2,'0')} <b>{s.text}</b></span>
     <span className="resize right" onPointerDown={e=>begin(e,s,'end')} aria-label="Bitiş tutamacı"/>
    </div>)}
   </div>
   {project&&<div className="playhead" style={{left:`${time/duration*100}%`}}><span/></div>}
  </div></div>
  <div className="timeline-footer"><span><i className="dot amber"/> Kontrol gerekli</span><span><i className="dot green"/> Kontrol edildi</span><span className="right">30 FPS <em>·</em> 1080 × 1920 <em>·</em> H.264 / AAC</span></div>
 </section>
}
