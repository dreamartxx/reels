/** Same normalized choreography as backend/render.py; verified by cross-language tests. */
export function motion(sentences:{start:number}[],t:number,transition:number){
 if(!sentences.length)return [];
 const next = sentences.findIndex(s=>s.start>t);
 const i = Math.max(0,next===-1?sentences.length-1:next-1);
 let u=0;
 if(i+1<sentences.length){const duration=Math.min(transition,(sentences[i+1].start-sentences[i].start)*.45);if(duration>0){const x=Math.max(0,Math.min(1,(t-sentences[i+1].start+duration)/duration));u=x*x*(3-2*x)}}
 return [
  {index:i-1,offset:-1-u,opacity:.3*Math.max(0,1-2*u),scale:.72},
  {index:i,offset:-u,opacity:1-.7*u,scale:1-.28*u},
  {index:i+1,offset:1-u,opacity:.22+.78*u,scale:.72+.28*u},
  {index:i+2,offset:2-u,opacity:.22*Math.max(0,2*u-1),scale:.72},
 ].filter(x=>x.index>=0&&x.index<sentences.length&&x.opacity>.00001);
}
