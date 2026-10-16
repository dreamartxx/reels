/** Same normalized choreography as backend/render.py; verified by cross-language tests. */
export function motion(sentences:{start:number}[],t:number,transition:number,duration?:number){
 if(!sentences.length)return [];
 const next = sentences.findIndex(s=>s.start>t);
 const i = Math.max(0,next===-1?sentences.length-1:next-1);
 let u=0;
 if(i+1<sentences.length){const duration=Math.min(transition,(sentences[i+1].start-sentences[i].start)*.45);if(duration>0){const x=Math.max(0,Math.min(1,(t-sentences[i+1].start+duration)/duration));u=x*x*(3-2*x)}}
 const items = [
  {index:i-1,offset:-1-u,opacity:.3*Math.max(0,1-2*u),scale:.72},
  {index:i,offset:-u,opacity:1-.7*u,scale:1-.28*u},
  {index:i+1,offset:1-u,opacity:.22+.78*u,scale:.72+.28*u},
  {index:i+2,offset:2-u,opacity:.22*Math.max(0,2*u-1),scale:.72},
 ];
 return items.filter(x=>x.index>=0&&x.index<sentences.length&&x.opacity>.00001).map(item=>{
  let phase=0;
  if(item.index===i-1)phase=.55+.45*Math.max(0,Math.min(1,(t-sentences[i].start)/Math.max(.5,transition)));
  else if(item.index===i){phase=.55*u;if(i===sentences.length-1&&duration!==undefined){const fade=Math.min(Math.max(.8,transition),Math.max(.01,duration-sentences[i].start));phase=Math.max(0,Math.min(1,(t-duration+fade)/fade))}}
  return {...item,dissolve:phase};
 }).filter(item=>item.dissolve<1);
}

export function letterMotion(index:number,phase:number){
 const delay=((index*37+11)%101)/101*.16;
 const p=Math.max(0,Math.min(1,(phase-delay)/(1-delay))),eased=p*p*(3-2*p);
 return {x:(((index*73+19)%101)/100-.5)*140*eased,y:-(28+((index*43+7)%83))*eased,opacity:1-eased};
}
