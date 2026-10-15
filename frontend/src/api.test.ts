import test from 'node:test';
import assert from 'node:assert/strict';
import {api} from './types.ts';

test('geçici veritabanı hatasında GET yeniden denenir, üretim POST isteği çoğaltılmaz',async()=>{
 const original=globalThis.fetch;let calls=0;
 try{
  globalThis.fetch=async()=>++calls===1?new Response(JSON.stringify({detail:'Veritabanına bağlanılamadı.'}),{status:503}):Response.json({status:'completed'});
  assert.deepEqual(await api('/jobs/example'),{status:'completed'});assert.equal(calls,2);
  calls=0;globalThis.fetch=async()=>{calls++;return new Response(JSON.stringify({detail:'Geçici hata'}),{status:503});};
  await assert.rejects(api('/projects/example/export',{method:'POST',body:'{}'}),/Geçici hata/);assert.equal(calls,1);
 }finally{globalThis.fetch=original;}
});
