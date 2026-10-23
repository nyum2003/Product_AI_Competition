/* Isolated usability demo. All records are local to this browser. */
(() => {
  const prefix='caseflow-demo:';
  const read=id=>JSON.parse(localStorage.getItem(prefix+id)||'null');
  const save=p=>localStorage.setItem(prefix+p.id,JSON.stringify(p));
  function results(p){
    if(!p.poll)return [];
    const output=[],duration=p.poll.duration*60000;
    for(const [a,b] of p.poll.ranges){for(let start=Date.parse(a);start+duration<=Date.parse(b);start+=900000){
      const ids=p.members.filter(m=>(p.availability[m.id]||[]).some(([x,y])=>Date.parse(x)<=start&&Date.parse(y)>=start+duration)).map(m=>m.id);
      output.push({start:new Date(start).toISOString(),end:new Date(start+duration).toISOString(),members:ids,count:ids.length,full:ids.length===p.members.length});
    }}
    return output.sort((a,b)=>b.count-a.count||a.start.localeCompare(b.start));
  }
  window.demoAPI=async(path,body)=>{
    if(path==='/api/config')return {ai:false};
    if(path==='/api/extract')throw Error('PDF upload is available in the full app. Use the example for this demo.');
    if(path==='/api/projects'&&body){
      const members=body.members.map((m,i)=>({...m,id:'m'+i}));
      if(members.length<2||members.some(m=>!m.name.trim()))throw Error('Enter at least two member names, or use Try an example.');
      const tasks=structuredClone(window.demoFixture.tasks);
      const labels=['Strength-based','Balanced workload','Project-stage'];
      const plans=labels.map((strategy,k)=>{
        const load=members.map(()=>0),stages={};
        const rows=structuredClone(tasks);
        const order=k===1?[...rows].sort((a,b)=>b.effort-a.effort):rows;
        for(const [index,t] of order.entries()){
          let who;
          if(k===0){who=members.map((m,i)=>({i,score:t.skills.filter(s=>(m.skills+' '+m.preferences).toLowerCase().includes(s.toLowerCase())).length-load[i]/10})).sort((a,b)=>b.score-a.score)[0].i;}
          else if(k===1)who=load.indexOf(Math.min(...load));
          else {if(stages[t.stage]===undefined)stages[t.stage]=Object.keys(stages).length%members.length;who=stages[t.stage];}
          t.owners=[members[who].id];t.reason='Sample '+strategy.toLowerCase()+' recommendation. Edit it to explore the interface.';load[who]+=t.effort;
        }
        return {strategy,tasks:rows};
      });
      const id=crypto.randomUUID();
      const p={id,name:body.name,instructions:body.instructions,deadline:body.deadline,members,breakdown:{tasks,warnings:['Demo: these are sample customer-churn workstreams, not AI interpretation of your pasted text.','Effort estimates are illustrative. Everything here is saved only in this browser.'],mode:'Sample demo plan'},plans,saved:null,poll:null,confirmed:null,availability:{}};
      save(p);return {project:p,owner:'demo-local'};
    }
    const parts=path.split('/'),id=parts[3],p=read(id);
    if(!p)throw Error('This demo project exists only in the browser where it was created. Open the homepage and try an example.');
    if(body===undefined)return {...p,submitted:Object.keys(p.availability),windows:results(p)};
    const action=parts[4];
    if(action==='plan'){
      if(!body.tasks.length||body.tasks.some(t=>!t.title.trim()||!t.owners.length||!(t.effort>0)))throw Error('Give each task a title, an owner, and a positive effort estimate.');
      p.saved=structuredClone(body);
    }
    else if(action==='poll'){
      if(body.ranges.some(([a,b])=>Date.parse(b)-Date.parse(a)<body.duration*60000))throw Error('The daily window must fit the requested meeting duration.');
      p.poll=body;p.availability={};p.confirmed=null;
    }
    else if(action==='availability'){
      p.availability[body.member]=body.intervals;p.confirmed=null;save(p);return {token:'demo-local'};
    }
    else if(action==='confirm')p.confirmed=results(p).find(w=>w.start===body.start);
    else throw Error('Unknown demo action');
    save(p);return {ok:true};
  };
  document.addEventListener('DOMContentLoaded',()=>{
    document.querySelector('#reset-demo').onclick=()=>{
      for(const key of Object.keys(localStorage))if(key.startsWith(prefix))localStorage.removeItem(key);
      location.href=location.pathname;
    };
  });
})();
