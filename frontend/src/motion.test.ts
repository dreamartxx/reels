import test from 'node:test';
import assert from 'node:assert/strict';
import {motion} from './motion.ts';
test('en fazla üç cümle ve uzun duraklamada sabit sahne',()=>{
 const sentences=[{start:0},{start:2},{start:12},{start:15}];
 for(let t=0;t<16;t+=.01)assert.ok(motion(sentences,t,.6).length<=3);
 assert.deepEqual(motion(sentences,5,.6),motion(sentences,10,.6));
 assert.deepEqual(motion([],0,.6),[]);
});
