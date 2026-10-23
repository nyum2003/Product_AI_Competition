import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
import {webcrypto} from 'node:crypto';

const memory=new Map();
const context={window:{},localStorage:{getItem:k=>memory.get(k)||null,setItem:(k,v)=>memory.set(k,v)},document:{addEventListener(){}},crypto:webcrypto,structuredClone};
vm.createContext(context);
vm.runInContext(await readFile(new URL('../demo/demo.js',import.meta.url),'utf8'),context);
const api=context.window.demoAPI;
const members=[{name:'Alex',skills:'Python, SQL',preferences:''},{name:'Sam',skills:'Research, Presentation',preferences:''}];
async function create(instructions){return (await api('/api/projects',{name:'Custom test',instructions,deadline:'',members})).project;}

const analytics='Clean the retail dataset. Analyze regional sales patterns. Submit a report. No predictive models are required.';
const p=await create(analytics);
assert.equal(p.breakdown.mode,'Text-based interpretation');
assert(p.breakdown.tasks.some(t=>t.title==='Data preparation'));
assert(!p.breakdown.tasks.some(t=>t.title==='Predictive modeling'));
assert(p.breakdown.warnings.some(w=>w.includes('No predictive models')));
assert(p.breakdown.tasks.every(t=>analytics.includes(t.source)));
assert(!JSON.stringify(p.breakdown).toLowerCase().includes('churn'));
for(const plan of p.plans){assert.equal(plan.tasks.length,p.breakdown.tasks.length);assert(plan.tasks.every((t,i)=>t.source===p.breakdown.tasks[i].source));}

const history='Compare two primary sources about medieval trade. Write a 1500-word essay. Prepare an annotated bibliography.';
const h=await create(history);
assert(h.breakdown.tasks.some(t=>t.title.includes('Compare two primary sources')));
assert(h.breakdown.tasks.some(t=>t.description.includes('annotated bibliography')));
assert(!h.breakdown.tasks.some(t=>['Predictive modeling','Data preparation'].includes(t.title)));
assert(h.breakdown.tasks.every(t=>history.includes(t.source)));

const vague=await create('We have a broad group assignment about cities.');
assert(vague.breakdown.warnings.some(w=>w.includes('No clear action')));
const path='/api/projects/'+h.id;
await api(path+'/plan',h.plans[0]);
const saved=await api(path);
assert.equal(saved.saved.tasks[0].source,h.breakdown.tasks[0].source);
new vm.Script(await readFile(new URL('../docs/app.js',import.meta.url),'utf8'));
console.log('Custom-text demo checks passed: analytics, non-analytics, ambiguity, constraints, source grounding, allocation continuity, saving, and generated syntax.');
