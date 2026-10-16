import {useEffect,useRef,useState,RefObject} from 'react';
import {Expand,ShieldCheck} from 'lucide-react';
import {api,editBody,Project,Scene,Style,Job} from './types';
import {motion,letterMotion} from './motion';

export function Preview({project,style,time,guides,onError,videoRef,onVideoPlay,onVideoPause,onVideoEnd}:{videoRef:RefObject<HTMLVideoElement|null>;onVideoPlay:()=>void;onVideoPause:()=>void;onVideoEnd:()=>void;project:Project|null;style:Style;time:number;guides:boolean;onError:(s:string)=>void}){
 const canvas=useRef<HTMLCanvasElement>(null);
 const [assets,setAssets]=useState<{scene:Scene;images:HTMLImageElement[];bg:HTMLImageElement;pid:string}|null>(null);
 const [loading,setLoading]=useState(false);
 const sceneKey=JSON.stringify({id:project?.id,text:project?.sentences.map(s=>[s.text,s.accent]),style});
 useEffect(()=>{
  if(!project?.sentences.length){setAssets(null);return}
  let alive=true;
  const controller=new AbortController();
  const load=async(url:string):Promise<HTMLImageElement>=>{
   for(let attempt=0;attempt<3;attempt++){
    if(!alive)throw Error('İptal edildi.');
    try{return await new Promise<HTMLImageElement>((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=()=>reject(Error('Önizleme görseli yüklenemedi.'));im.src=url+(attempt?'?retry='+attempt:'')});}
    catch(e){if(attempt===2)throw e;await new Promise(resolve=>setTimeout(resolve,500*(attempt+1)));}
   }
   throw Error('Önizleme görseli yüklenemedi.');
  };
  setLoading(true);
  const timer=setTimeout(async()=>{
   try{let response=await api<Scene|{pending:true;job:string}>(`/projects/${project.id}/scene`,{method:'POST',body:JSON.stringify(editBody(project)),signal:controller.signal});
    if('pending' in response){
     const jid=response.job;
     while(alive){
      await new Promise(resolve=>setTimeout(resolve,1100));
      if(!alive)return;
      const job=await api<Job>(`/jobs/${jid}`,{signal:controller.signal});
      if(job.status==='completed'){response=job.result as unknown as Scene;break}
      if(['failed','cancelled'].includes(job.status))throw Error(job.message||'Önizleme işi iptal edildi.');
     }
    }
    if(!alive||'pending' in response)return;
    const scene=response;
    const prefix=`/api/projects/${project.id}/scenes/${scene.digest}/`;
    // Bound parallel protected media requests on shared hosting.
    const urls=[prefix+'background.jpg',...scene.sprites.map(s=>prefix+s.file)];
    const loaded:HTMLImageElement[]=[];
    for(let i=0;i<urls.length;i+=3){if(!alive)return;loaded.push(...await Promise.all(urls.slice(i,i+3).map(load)));}
    const [bg,...images]=loaded;
    if(alive){setAssets({scene,images,bg,pid:project.id});setLoading(false)}
   }catch(e){if(alive){setLoading(false);onError((e as Error).message)}}
  },250);
  return()=>{alive=false;clearTimeout(timer);controller.abort()};
 // sceneKey is the complete visual signature; timing edits don't regenerate sprites.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[sceneKey]);
 useEffect(()=>{
  const c=canvas.current;if(!c)return;const ctx=c.getContext('2d');if(!ctx)return;
  const ratio=c.width/1080;
  ctx.setTransform(ratio,0,0,ratio,0,0);ctx.globalAlpha=1;
  ctx.clearRect(0,0,1080,1920);ctx.fillStyle=project?.background?'rgba(0,0,0,.35)':style.background;ctx.fillRect(0,0,1080,1920);
  if(assets&&assets.pid===project?.id){
   if(!project?.background)ctx.drawImage(assets.bg,0,0,1080,1920);
   for(const item of motion(project.sentences,time,style.transition,project.audio.duration,!!project.background)){
    const im=assets.images[item.index];if(!im)continue;
    const geo=assets.scene.geometry;
    ctx.globalAlpha=item.opacity;
    const w=im.width*item.scale,h=im.height*item.scale;
    const left=geo.x-w/2,top=geo.y+item.offset*geo.gap-h/2;
    const glyphs=assets.scene.sprites[item.index].glyphs;
    if(item.dissolve>0&&glyphs?.length){
     glyphs.forEach((g,index)=>{const drift=letterMotion(index,item.dissolve);ctx.globalAlpha=item.opacity*drift.opacity;
      ctx.drawImage(im,g.x,g.y,g.width,g.height,left+g.x*item.scale+drift.x,top+g.y*item.scale+drift.y,g.width*item.scale,g.height*item.scale);
     });
    }else ctx.drawImage(im,left,top,w,h);
   }
  }else{
   ctx.textAlign='center';ctx.fillStyle=style.foreground;
   ctx.globalAlpha=.25;ctx.font='42px Georgia';ctx.fillText('Bir ses, bir hikâye.',540,680);
   ctx.globalAlpha=1;ctx.font='78px Georgia';ctx.fillText('Kelimeleriniz',540,900);ctx.fillText('hayat bulsun.',540,1004);
   ctx.globalAlpha=.25;ctx.font='42px Georgia';ctx.fillText('Şiirin ritminde.',540,1200);
  }
  if(guides){ctx.globalAlpha=.45;ctx.strokeStyle=style.accent;ctx.lineWidth=2;ctx.setLineDash([12,12]);ctx.strokeRect(style.safe_left,style.safe_top,1080-style.safe_left-style.safe_right,1920-style.safe_top-style.safe_bottom);ctx.setLineDash([])}
  ctx.globalAlpha=1;
 },[assets,time,project?.sentences,style,guides,project?.background?.id]);
 return <div className="preview-frame" style={{background:style.background}}>
  {project?.background&&<video ref={videoRef} className="background-video" key={project.background.id} src={`/api/projects/${project.id}/backgrounds/${project.background.id}`} muted playsInline preload="auto" onPlay={onVideoPlay} onPause={onVideoPause} onEnded={onVideoEnd} onError={()=>onError('Arka plan videosu oynatılamadı. Videoyu yeniden yükleyin.')} aria-label="Doğa videosu arka planı"/>}
  <canvas ref={canvas} width={540} height={960} aria-label="Sesle eş zamanlı 9:16 video önizlemesi"/>
  {!project?.sentences.length&&<span className="sample-label">TASARIM ÖNİZLEMESİ</span>}
  {loading&&<span className="preview-loading">Tipografi hazırlanıyor…</span>}
  <button className="fullscreen icon" title="Önizlemeyi büyüt" onClick={()=>canvas.current?.parentElement?.requestFullscreen().catch(e=>onError(e.message))}><Expand size={16}/></button>
  {guides&&<span className="safe-label"><ShieldCheck size={12}/> Reels güvenli alanı</span>}
 </div>
}
