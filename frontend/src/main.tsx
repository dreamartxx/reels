import React,{useCallback,useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {AudioLines,ArrowUpRight,Check,ChevronDown,Download,FileAudio,FolderOpen,Headphones,Loader2,Pause,Play,Plus,Save,Settings2,ShieldCheck,SkipBack,Sparkles,Type,Upload,X,AlertTriangle,CheckCircle2,Film,SlidersHorizontal} from 'lucide-react';
import {api,defaultStyle,editBody,Job,Project,Sentence,Style,templates,timeLabel} from './types';
import {Preview} from './Preview';
import {Timeline} from './Timeline';
import './style.css';
import {AuthGate} from './AuthGate';

const DEMO='[deep] Gece sessizce şehrin üstüne iner.\nBir ışık kalır uzak bir pencerede.\n\n[pause] Rüzgâr geçer, yapraklar usulca konuşur.\n[firm] İçimde yeni bir sabah büyür.';
function readStyle():Style {try{return {...defaultStyle,...JSON.parse(localStorage.getItem('reels-style')||'{}')}}catch{return defaultStyle}}
function App(){
 const [project,setProject]=useState<Project|null>(null),[text,setText]=useState(''),[style,setStyle]=useState<Style>(readStyle);
 const [time,setTime]=useState(0),[playing,setPlaying]=useState(false),[selected,setSelected]=useState<string|null>(null),[guides,setGuides]=useState(false);
 const [error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[job,setJob]=useState<Job|null>(null),[saved,setSaved]=useState('');
 const [tab,setTab]=useState<'design'|'sentence'>('design'),[mode,setMode]=useState('sentences'),[model,setModel]=useState('base'),[device,setDevice]=useState('cpu');
 const [showProjects,setShowProjects]=useState(false),[projects,setProjects]=useState<{id:string;name:string;duration:number}[]>([]),[files,setFiles]=useState<Record<string,string>|null>(null),[quality,setQuality]=useState('final');
 const [health,setHealth]=useState<{ffmpeg:boolean;ffprobe:boolean;alignment:boolean;models:string[];mode?:string;worker_online?:boolean}|null>(null);
 const audioRef=useRef<HTMLAudioElement>(null),inputRef=useRef<HTMLInputElement>(null),latest=useRef(project),lastSaved=useRef(''),saveSequence=useRef(0);
 const locked=busy||!!job&&['running','queued'].includes(job.status);
 latest.current=project;
 const report=useCallback((s:string)=>setError(s),[]);
 function apply(p:Project){if(p.alignment?.model)setModel(p.alignment.model);setProject(p);setText(p.text);setStyle(p.style);setSelected(p.sentences[0]?.id||null);setTime(0);setPlaying(false);lastSaved.current=JSON.stringify(editBody(p));setSaved('Kaydedildi');localStorage.setItem('reels-project',p.id)}
 async function open(id:string){try{const p=await api<Project>('/projects/'+id);apply(p);setShowProjects(false);setFiles(null);const history=await api<{files:Record<string,string>}[]>(`/projects/${id}/exports`);if(history.length)setFiles(history[0].files);const active=await api<Job[]>(`/projects/${id}/jobs`);setJob(active[0]||null)}catch(e){report((e as Error).message)}}
 useEffect(()=>{api<typeof health>('/health').then(setHealth).catch(()=>setError('Yerel sunucuya bağlanılamadı. README içindeki başlatma adımlarını izleyin.'));const id=localStorage.getItem('reels-project');if(id)void open(id)},[]);
 useEffect(()=>{if(health?.mode!=='cloud')return;const timer=setInterval(()=>api<typeof health>('/health').then(setHealth).catch(()=>{}),15000);return()=>clearInterval(timer)},[health?.mode]);
 useEffect(()=>{localStorage.setItem('reels-style',JSON.stringify(style))},[style]);
 useEffect(()=>{
  if(!project||locked)return;
  const signature=JSON.stringify(editBody(project));if(signature===lastSaved.current)return;
  setSaved('Kaydediliyor…');const seq=++saveSequence.current;
  const timer=setTimeout(()=>{api<Project>('/projects/'+project.id,{method:'PUT',body:signature}).then(()=>{if(seq===saveSequence.current){lastSaved.current=signature;setSaved('Kaydedildi')}}).catch(e=>{setSaved('Kaydedilemedi');report(e.message)})},700);
  return()=>clearTimeout(timer);
 },[project,locked,report]);
 useEffect(()=>{
  if(!job||!['running','queued'].includes(job.status))return;
  let active=true;
  const timer=setInterval(async()=>{try{const updated=await api<Job>('/jobs/'+job.id);if(!active)return;setJob(updated);
   if(updated.status==='completed'){if(updated.kind==='align'||updated.kind==='ingest'){apply(updated.result as Project);setNotice(updated.kind==='ingest'?'Ses analizi tamamlandı. Şimdi şiiri sesle hizalayabilirsiniz.':'Hizalama tamamlandı. İşaretli kelimeleri dinleyerek kontrol edin.')}else{setFiles((updated.result as {files:Record<string,string>}).files);setNotice('Video ve altyazı dosyalarınız hazır.')}}
   if(['failed','cancelled'].includes(updated.status))setError(updated.message);
  }catch(e){if(active){setError((e as Error).message);setJob(null)}}},900);
  return()=>{active=false;clearInterval(timer)};
 },[job?.id,job?.status]);
 useEffect(()=>{
  let id=0;function tick(){if(audioRef.current)setTime(audioRef.current.currentTime);id=requestAnimationFrame(tick)}
  if(playing)id=requestAnimationFrame(tick);return()=>cancelAnimationFrame(id);
 },[playing]);
 function updateStyle(patch:Partial<Style>){setStyle(prev=>({...prev,...patch}));setProject(p=>p?{...p,style:{...p.style,...patch}}:null)}
 function updateText(value:string){setText(value);setProject(p=>p?{...p,text:value}:null)}
 async function upload(file:File,example=false){
  setError('');setBusy(true);audioRef.current?.pause();setFiles(null);setJob(null);
  try{const form=new FormData();form.append('file',file);let p=await api<Project>('/projects',{method:'POST',body:form});p={...p,text:example?DEMO:text,style};p=await api<Project>('/projects/'+p.id,{method:'PUT',body:JSON.stringify(editBody(p))});apply(p);const active=await api<Job[]>(`/projects/${p.id}/jobs`);setJob(active[0]||null);setNotice('Ses hazır. Şiirinizi kontrol edip “Sesle hizala” düğmesine basın.')}
  catch(e){report((e as Error).message)}finally{setBusy(false)}
 }
 async function demo(){try{setBusy(true);const res=await fetch('/api/example/audio');if(!res.ok)throw Error('Örnek ses bulunamadı. Kendi MP3 dosyanızı yükleyin.');await upload(new File([await res.blob()],'Gece — Türkçe örnek.mp3',{type:'audio/mpeg'}),true)}catch(e){report((e as Error).message)}finally{setBusy(false)}}
 async function align(manual=false){if(!project||locked)return;setBusy(true);setError('');setFiles(null);audioRef.current?.pause();
  try{await api('/projects/'+project.id,{method:'PUT',body:JSON.stringify(editBody(project))});
   const result=await api<Project|Job>(`/projects/${project.id}/${manual?'manual':'align'}`,{method:'POST',body:JSON.stringify({text,mode,model,device})});
   if(manual){apply(result as Project);setNotice('Bu bir elle zamanlama taslağıdır. Hiçbir cümle otomatik hizalanmadı; tüm süreleri kontrol edin.')}else setJob(result as Job);
  }catch(e){report((e as Error).message)}finally{setBusy(false)}
 }
 async function save(){if(!project)return;try{const p=await api<Project>('/projects/'+project.id,{method:'PUT',body:JSON.stringify(editBody(project))});lastSaved.current=JSON.stringify(editBody(p));setSaved('Kaydedildi');setNotice(health?.mode==='cloud'?'Proje Hostinger veritabanına kaydedildi.':'Proje bu bilgisayara kaydedildi.')}catch(e){report((e as Error).message)}}
 async function exportVideo(){if(!project||locked)return;setBusy(true);setError('');setFiles(null);audioRef.current?.pause();try{await api('/projects/'+project.id,{method:'PUT',body:JSON.stringify(editBody(project))});setJob(await api<Job>(`/projects/${project.id}/export`,{method:'POST',body:JSON.stringify({...editBody(project),quality})}))}catch(e){report((e as Error).message)}finally{setBusy(false)}}
 function seek(t:number){if(audioRef.current){audioRef.current.currentTime=t;setTime(t)}}
 async function play(){const a=audioRef.current;if(!a)return;if(playing)a.pause();else{if(a.currentTime>=a.duration)a.currentTime=0;try{await a.play()}catch(e){report((e as Error).message)}}}
 function changeSentences(sentences:Sentence[]){setProject(p=>p?{...p,sentences}:p)}
 const sentence=project?.sentences.find(s=>s.id===selected);
 const reviewCount=project?.sentences.filter(s=>s.review).length||0;
 const textChanged=!!project?.sentences.length&&project.sentences.map(s=>s.text).join(' ').replace(/\s+/g,' ').trim()!==text.replace(/\[[^\]]*\]/g,'').replace(/\s+/g,' ').trim();
 return <div className="app">
  <header className="topbar"><div className="brand"><div className="brand-icon"><AudioLines size={25}/></div><div>reels<span>TYPOGRAPHY STUDIO</span></div><span className="version">{health?.mode==='cloud'?'CLOUD / 01':'LOCAL / 01'}</span></div>
   <div className="project-title"><input aria-label="Proje adı" value={project?.name||'Yeni bir hikâye'} disabled={!project||locked} onChange={e=>setProject(p=>p?{...p,name:e.target.value}:p)}/><span><i className="dot green"/>{project?saved:'Yalnızca bu bilgisayarda'}</span></div>
   <div className="header-actions"><button className="ghost" onClick={async()=>{try{setProjects(await api('/projects'));setShowProjects(true)}catch(e){report((e as Error).message)}}} disabled={locked}><FolderOpen size={16}/>Projeler</button><button className="icon ghost" title="Projeyi kaydet" disabled={!project||locked} onClick={save}><Save size={17}/></button><button className="primary small" disabled={!project?.sentences.length||locked||textChanged} onClick={exportVideo}><Download size={16}/>MP4 dışa aktar<ArrowUpRight size={14}/></button></div>
  </header>
  <div className="intro"><div><span className="eyebrow">SESİNİZDEN BİR SAHNEYE</span><h1>Şiirin ritmini görünür kılın<span>.</span></h1></div><div className="local-status"><i className={`dot ${health?.ffmpeg&&health?.alignment?'green':'amber'}`}/>{health?.mode==='cloud'?(health.worker_online?'Hostinger · video motoru bağlı':'Hostinger · video motoru çevrimdışı'):health?.ffmpeg&&health?.alignment?'Yerel stüdyo hazır':'Bağlantı kontrol ediliyor'}<span>9:16 REELS</span></div></div>
  {error&&<div className="banner error" role="alert"><AlertTriangle size={17}/><span>{error}</span><button className="icon" aria-label="Hata mesajını kapat" onClick={()=>setError('')}><X size={16}/></button></div>}
  {notice&&!error&&<div className="banner notice" role="status"><CheckCircle2 size={16}/><span>{notice}</span><button className="icon" aria-label="Bildirimi kapat" onClick={()=>setNotice('')}><X size={15}/></button></div>}
  {health?.mode==='cloud'&&!health.worker_online&&<div className="banner notice"><AlertTriangle size={16}/><span>Video motoru çevrimdışı. Bilgisayarınızda “Bulut Motorunu Aç” dosyasını çalıştırın. İşler bağlantı kurulunca işlenecek.</span></div>}
  <main className="workspace">
   <aside className="source-panel panel"><div className="panel-heading"><span className="number">01</span><h2>Ses & metin</h2><Headphones size={16}/></div>
    <div className="panel-body"><label className="field-title">SESLENDİRME</label>
     <input type="file" accept=".mp3,.wav,audio/mpeg,audio/wav" ref={inputRef} hidden onChange={e=>{const f=e.target.files?.[0];if(f)void upload(f);e.target.value=''}}/>
     <button className={`upload-zone ${project?'has-audio':''}`} disabled={locked} onClick={()=>inputRef.current?.click()} onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();if(!locked&&e.dataTransfer.files[0])void upload(e.dataTransfer.files[0])}}>
      {project?<FileAudio size={25}/>:<Upload size={25}/>}<strong>{project?project.audio.filename:'Ses dosyanızı bırakın'}</strong><span>{project?`${timeLabel(project.audio.duration)} · ${(project.audio.sample_rate/1000).toFixed(1)} kHz · ${project.audio.channels===1?'Mono':'Stereo'}`:'veya dosya seçmek için tıklayın'}</span><small>{project?'DEĞİŞTİR →':'MP3 / WAV · EN FAZLA 100 MB'}</small>
     </button>
     {!project&&<button className="demo-link" disabled={locked} onClick={demo}><Play size={12}/> Türkçe örnekle dene <ArrowUpRight size={12}/></button>}
     <div className="label-row"><label className="field-title" htmlFor="poem">ŞİİR METNİ</label><span>{text.replace(/\[[^\]]*\]/g,'').trim().split(/\s+/).filter(Boolean).length} kelime</span></div>
     <textarea id="poem" value={text} disabled={locked} maxLength={24000} placeholder={'Bir şiirle başlayın…\n\nSeslendirdiğiniz metni buraya yapıştırın.\nHer cümle kendi anını bulsun.'} onChange={e=>updateText(e.target.value)}/>
     <div className="help"><ShieldCheck size={13}/><span>[deep], [pause] gibi etiketler videoda görünmez.</span></div>
     <label className="field-title" htmlFor="split">METNİ BÖL</label><select id="split" disabled={locked} value={mode} onChange={e=>setMode(e.target.value)}><option value="sentences">Cümlelere göre · önerilen</option><option value="lines">Her satır ayrı</option></select>
     <details className="advanced"><summary>Hizalama seçenekleri<ChevronDown size={13}/></summary><div className="two-fields"><label>Model<select value={model} disabled={locked} onChange={e=>setModel(e.target.value)}><option value="tiny">Tiny · hızlı</option><option value="base">Base · dengeli</option><option value="small">Small · daha hassas</option><option value="medium">Medium · yavaş</option></select></label><label>İşlemci<select value={device} disabled={locked} onChange={e=>setDevice(e.target.value)}><option value="cpu">CPU</option><option value="cuda">NVIDIA CUDA</option></select></label></div><p>İlk kullanımda model indirilir. Sonraki hizalamalar çevrimdışı çalışır.</p></details>
     <button className="primary wide" disabled={!project||!text.trim()||locked} onClick={()=>align()}>{locked?<Loader2 className="spin" size={16}/>:<Sparkles size={16}/>}Sesle hizala</button>
     <button className="text-button" disabled={!project||!text.trim()||locked} onClick={()=>align(true)}>Zamanları kendim düzenleyeceğim</button>
     {textChanged&&<p className="warning">Metin değişti. Dışa aktarmadan önce yeniden hizalayın.</p>}
    </div><div className="source-note"><span>01 — KELİMELERİNİZ</span><p>Sesinize dokunmadan.<br/>Hikâyenizi öne çıkararak.</p></div>
   </aside>
   <section className="preview-panel"><div className="preview-heading"><span><i className="dot green"/> CANLI ÖNİZLEME</span><button className={`ghost safe-toggle ${guides?'active':''}`} onClick={()=>setGuides(!guides)} title="Güvenli alanı göster"><ShieldCheck size={14}/>Güvenli alan</button></div>
    <div className="preview-stage"><Preview project={project} style={style} time={time} guides={guides} onError={report}/><span className="frame-caption">DİKEY BİR HİKÂYE. KENDİ RİTMİNDE.</span></div>
    <div className="playback"><button className="icon ghost" title="Başa dön" disabled={!project} onClick={()=>seek(0)}><SkipBack size={16}/></button><button className="play-button" title={playing?'Duraklat':'Oynat'} disabled={!project} onClick={play}>{playing?<Pause size={19} fill="currentColor"/>:<Play size={19} fill="currentColor"/>}</button><span className="time">{timeLabel(time)} <em>/ {timeLabel(project?.audio.duration||0)}</em></span><span className="playback-mode">{project?.alignment?.engine==='stable-ts'?'METNE HİZALI':project?.sentences.length?'ELLE ZAMANLAMA':'ÖNİZLEME'}</span></div>
    <input className="scrubber" aria-label="Oynatma konumu" type="range" min="0" max={project?.audio.duration||1} step=".01" value={time} disabled={!project} onChange={e=>seek(Number(e.target.value))}/>
    {project&&<audio ref={audioRef} src={`/api/projects/${project.id}/audio`} onPlay={()=>setPlaying(true)} onPause={()=>setPlaying(false)} onEnded={()=>{setPlaying(false);setTime(project.audio.duration)}} onTimeUpdate={e=>{if(!playing)setTime(e.currentTarget.currentTime)}} onError={()=>report('Ses oynatılamadı. Dosyayı yeniden yükleyin.')} preload="auto"/>}
   </section>
   <aside className="settings-panel panel"><div className="panel-heading"><span className="number">02</span><h2>Sahneyi tasarla</h2><Settings2 size={16}/></div>
    <div className="tabs"><button className={tab==='design'?'active':''} onClick={()=>setTab('design')}><SlidersHorizontal size={14}/>Tasarım</button><button className={tab==='sentence'?'active':''} onClick={()=>setTab('sentence')}><Type size={14}/>Cümle {reviewCount>0&&<i>{reviewCount}</i>}</button></div>
    <div className="settings-body">
    {tab==='sentence'&&project?.sentences.length?<select aria-label="Cümle seç" className="sentence-picker" value={selected||''} onChange={e=>setSelected(e.target.value)}>{project.sentences.map((s,i)=><option key={s.id} value={s.id}>{i+1}. {s.review?'⚠ ':''}{s.text}</option>)}</select>:null}
    {tab==='design'?<><label className="field-title">BİR ATMOSFER SEÇİN</label><div className="templates">{templates.map(t=><button key={t.id} disabled={locked} className={`template ${style.template===t.id?'selected':''}`} onClick={()=>updateStyle({template:t.id,font:t.font,background:t.bg,foreground:t.fg,accent:t.accent})}><span className="swatch" style={{background:t.bg,color:t.fg,fontFamily:t.font==='mono'?'Plex Mono':t.font==='sans'?'Manrope':'Lora'}}>{t.mark}{style.template===t.id&&<i><Check size={10}/></i>}</span><strong>{t.name}</strong></button>)}</div>
     <div className="divider"/><label className="field-title" htmlFor="font">TİPOGRAFİ</label><select id="font" disabled={locked} value={style.font} onChange={e=>updateStyle({font:e.target.value as Style['font']})}><option value="serif">Lora — Editorial serif</option><option value="sans">Manrope — Modern sans</option><option value="mono">IBM Plex Mono — Daktilo</option></select>
     <Range label="Yazı boyutu" value={style.font_size} min={30} max={130} suffix=" px" disabled={locked} onChange={font_size=>updateStyle({font_size})}/>
     <Range label="Satır aralığı" value={style.line_height} min={1} max={1.7} step={.05} suffix="×" disabled={locked} onChange={line_height=>updateStyle({line_height})}/>
     <div className="colors">{([['background','Zemin'],['foreground','Metin'],['accent','Vurgu']] as const).map(([key,label])=><label key={key}><input type="color" aria-label={label+' rengi'} disabled={locked} value={style[key]} onChange={e=>updateStyle({[key]:e.target.value})}/><span>{label}</span></label>)}</div>
     <div className="divider"/><label className="field-title">HAREKET & KADRAJ</label><Range label="Geçiş süresi" value={style.transition} min={.2} max={1.2} step={.05} suffix=" sn" disabled={locked} onChange={transition=>updateStyle({transition})}/><Range label="Dikey konum" value={style.position} min={-.15} max={.15} step={.01} suffix="" disabled={locked} onChange={position=>updateStyle({position})}/><Range label="Film dokusu" value={style.grain} min={0} max={.08} step={.005} suffix="" disabled={locked} onChange={grain=>updateStyle({grain})}/>
     <details className="advanced"><summary>Reels güvenli alanları<ChevronDown size={13}/></summary>{([['safe_top','Üst',80,400],['safe_bottom','Alt',100,500],['safe_left','Sol',50,220],['safe_right','Sağ',50,260]] as const).map(([key,label,min,max])=><Range key={key} label={label} value={style[key]} min={min} max={max} suffix=" px" disabled={locked} onChange={v=>updateStyle({[key]:v})}/>)}</details>
    </>:sentence&&project?<SentenceEditor key={sentence.id} sentence={sentence} project={project} disabled={locked} onChange={s=>changeSentences(project.sentences.map(x=>x.id===s.id?s:x))} onSeek={seek} onError={report}/>:<div className="empty-sentence"><Type size={25}/><h3>Her cümle, kendi anında.</h3><p>Hizalama sonrası zaman çizelgesinden bir cümle seçin; süresini ve vurgusunu düzenleyin.</p></div>}
    </div>
    <div className="export-quality"><Film size={15}/><select aria-label="Dışa aktarma kalitesi" disabled={locked} value={quality} onChange={e=>setQuality(e.target.value)}><option value="final">Final · 1080 × 1920</option><option value="preview">Hızlı prova · 360 × 640</option></select></div>
   </aside>
  </main>
  {job&&['running','queued'].includes(job.status)&&<div className="job-progress" role="status"><Loader2 className="spin" size={17}/><span>{job.message}</span><progress max={1} value={job.progress}/><b>{Math.round(job.progress*100)}%</b><button className="ghost" onClick={async()=>{try{await api('/jobs/'+job.id+'/cancel',{method:'POST'});setNotice('İptal isteği alındı. İşlem güvenli noktada duracak.')}catch(e){report((e as Error).message)}}}>İptal</button></div>}
  {files&&<div className="downloads"><CheckCircle2 size={18}/><strong>Çıktılar hazır</strong>{Object.entries(files).map(([name,url])=><a href={url} key={name} download><Download size={14}/>{name==='video.mp4'?'MP4 video':name==='timing.json'?'JSON zamanlama':'SRT altyazı'}</a>)}<button className="icon" aria-label="Çıktı bağlantılarını kapat" onClick={()=>setFiles(null)}><X size={15}/></button></div>}
  <Timeline project={project} time={time} selected={selected} onSelect={id=>{setSelected(id);setTab('sentence')}} onSeek={seek} onChange={changeSentences} disabled={locked}/>
  <footer><span>REELS TYPOGRAPHY STUDIO <em>—</em> Kelimelere alan açın.</span><span><ShieldCheck size={12}/>{health?.mode==='cloud'?'Projeler Hostinger’da · Video motoru bilgisayarınızda':'Ses dosyalarınız bu bilgisayarda kalır.'}</span></footer>
  {showProjects&&<div className="modal-backdrop" onClick={()=>setShowProjects(false)}><section className="modal" role="dialog" aria-modal="true" aria-label="Kaydedilen projeler" onClick={e=>e.stopPropagation()}><div className="modal-head"><h2>Hikâyeleriniz</h2><button className="icon" aria-label="Projeleri kapat" onClick={()=>setShowProjects(false)}><X size={20}/></button></div><p>{health?.mode==='cloud'?'Projeler ve ses dosyaları Hostinger hesabınızda saklanır.':'Projeler ve ses dosyaları bu bilgisayarda saklanır.'}</p>{projects.length?projects.map(p=><button className="project-item" key={p.id} onClick={()=>open(p.id)}><FileAudio size={20}/><strong>{p.name}</strong><span>{timeLabel(p.duration)}</span><ArrowUpRight size={16}/></button>):<p>Henüz kaydedilen bir proje yok.</p>}<button className="primary wide" onClick={()=>{setShowProjects(false);inputRef.current?.click()}}><Plus size={16}/>Yeni ses dosyası</button></section></div>}
 </div>
}
function Range({label,value,min,max,step=1,suffix,disabled,onChange}:{label:string;value:number;min:number;max:number;step?:number;suffix:string;disabled:boolean;onChange:(v:number)=>void}){return <label className="range-field"><span>{label}<b>{Number(value.toFixed(3))}{suffix}</b></span><input type="range" min={min} max={max} step={step} value={value} disabled={disabled} onChange={e=>onChange(Number(e.target.value))}/></label>}
function SentenceEditor({sentence:s,project,disabled,onChange,onSeek,onError}:{sentence:Sentence;project:Project;disabled:boolean;onChange:(s:Sentence)=>void;onSeek:(t:number)=>void;onError:(s:string)=>void}){
 const [start,setStart]=useState(s.start.toFixed(2)),[end,setEnd]=useState(s.end.toFixed(2));
 const [wordIndex,setWordIndex]=useState<number|null>(null);
 useEffect(()=>{setStart(s.start.toFixed(2));setEnd(s.end.toFixed(2))},[s.start,s.end]);
 function commit(){const a=Number(start),b=Number(end),i=project.sentences.findIndex(x=>x.id===s.id);const min=i?project.sentences[i-1].end:0,max=i+1<project.sentences.length?project.sentences[i+1].start:project.audio.duration;if(!Number.isFinite(a)||!Number.isFinite(b)||a<min||b>max||b-a<.03){onError(`Zaman aralığı ${min.toFixed(2)}–${max.toFixed(2)} saniye içinde olmalı ve en az 0,03 saniye sürmeli.`);return}onChange({...s,start:a,end:b,review:true,reason:'Elle düzenlendi; dinleyerek kontrol edin.',words:[]})}
 return <div className="sentence-editor"><div className="label-row"><label className="field-title">SEÇİLİ CÜMLE</label><span>{project.sentences.findIndex(x=>x.id===s.id)+1} / {project.sentences.length}</span></div><blockquote>{s.text}</blockquote><button className="ghost listen" onClick={()=>onSeek(s.start)}><Play size={13}/>Cümleye git · {timeLabel(s.start)}</button><div className="two-fields"><label>Başlangıç (sn)<input aria-label="Cümle başlangıcı" type="number" min={0} step=".01" value={start} disabled={disabled} onChange={e=>setStart(e.target.value)}/></label><label>Bitiş (sn)<input aria-label="Cümle bitişi" type="number" min={0} step=".01" value={end} disabled={disabled} onChange={e=>setEnd(e.target.value)}/></label></div><button className="secondary wide" disabled={disabled} onClick={commit}>Zamanı uygula</button><label className="check-field"><input type="checkbox" checked={s.accent} disabled={disabled} onChange={e=>onChange({...s,accent:e.target.checked})}/>Vurgu rengini kullan</label><div className={`review-card ${s.review?'':'done'}`}>{s.review?<AlertTriangle size={17}/>:<CheckCircle2 size={17}/>}<strong>{s.review?'Dinleyerek kontrol edin':s.reason==='Kullanıcı tarafından kontrol edildi.'?'Kontrol edildi':'Eşleşme uygun'}</strong><p>{s.reason||'Kelime zamanları hizalama motorundan alındı. Son kontrol için sesle birlikte dinleyin.'}</p><button className="secondary wide" disabled={disabled} onClick={()=>onChange({...s,review:!s.review,reason:s.review?'Kullanıcı tarafından kontrol edildi.':'Yeniden kontrol isteniyor.'})}>{s.review?'Dinledim, zamanlar doğru':'Yeniden kontrol işaretle'}</button></div>{s.words.length>0&&<><label className="field-title">KELİME EŞLEŞMELERİ</label><div className="word-list">{s.words.map((w,i)=><button className={w.review?'uncertain':''} key={i} onClick={()=>{onSeek(w.start);setWordIndex(i)}} title={`${w.start.toFixed(2)}–${w.end.toFixed(2)} sn · Model skoru ${w.confidence===null?'yok':Math.round(w.confidence*100)+'%'}`}><span>{w.text}</span><small>{w.start.toFixed(2)}{w.review?' ⚠':''}</small></button>)}</div>{wordIndex!==null&&s.words[wordIndex]&&<WordEditor key={`${s.id}-${wordIndex}-${s.words[wordIndex].start}-${s.words[wordIndex].end}`} sentence={s} index={wordIndex} project={project} disabled={disabled} onChange={onChange} onError={onError}/>}<p className="help">Sarı kelimeler düşük model skoru veya sıra dışı süre nedeniyle işaretlenir. Model skoru doğruluk garantisi değildir.</p></>}</div>
}

function WordEditor({sentence:s,index,project,disabled,onChange,onError}:{sentence:Sentence;index:number;project:Project;disabled:boolean;onChange:(s:Sentence)=>void;onError:(s:string)=>void}){
 const w=s.words[index]; const [start,setStart]=useState(w.start.toFixed(2)),[end,setEnd]=useState(w.end.toFixed(2));
 function commit(){
  const a=Number(start),b=Number(end),si=project.sentences.findIndex(x=>x.id===s.id);
  const lower=index?s.words[index-1].end:si?project.sentences[si-1].end:0;
  const upper=index+1<s.words.length?s.words[index+1].start:si+1<project.sentences.length?project.sentences[si+1].start:project.audio.duration;
  if(!Number.isFinite(a)||!Number.isFinite(b)||a<lower||b>upper||b-a<.03){onError(`Kelime ${lower.toFixed(2)}–${upper.toFixed(2)} sn içinde ve en az 0,03 sn olmalı.`);return}
  const words=s.words.map((x,i)=>i===index?{...x,start:a,end:b,review:false,confidence:null}:x);
  onChange({...s,words,start:words[0].start,end:words[words.length-1].end,review:true,reason:'Kelime zamanı elle düzeltildi; cümleyi dinleyerek onaylayın.'});
 }
 return <div className="word-editor"><strong>{w.text}</strong><div className="two-fields"><label>Başlangıç<input aria-label="Kelime başlangıcı" type="number" step=".01" disabled={disabled} value={start} onChange={e=>setStart(e.target.value)}/></label><label>Bitiş<input aria-label="Kelime bitişi" type="number" step=".01" disabled={disabled} value={end} onChange={e=>setEnd(e.target.value)}/></label></div><button className="secondary wide" disabled={disabled} onClick={commit}>Kelime zamanını uygula</button></div>
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><AuthGate><App/></AuthGate></React.StrictMode>);
