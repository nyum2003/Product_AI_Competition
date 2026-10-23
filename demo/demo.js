/* Isolated usability demo. All records are local to this browser. */
(() => {
  const prefix='caseflow-demo:';
  const read=id=>JSON.parse(localStorage.getItem(prefix+id)||'null');
  const save=p=>localStorage.setItem(prefix+p.id,JSON.stringify(p));
  function interpretText(text,deadline){
    // Browser-only extraction: preserve the user's words rather than inventing a plan.
    const definitions=[
      {title:'Problem framing',pattern:/\b(objectives?|kpis?|business problem|problem statement)\b/i,skills:['Business strategy','Research'],stage:'Frame',effort:2},
      {title:'Data preparation',pattern:/\b(clean\w*|preprocess\w*|data quality|sql|missing values)\b/i,skills:['Python','SQL','Data cleaning'],stage:'Prepare',effort:5},
      {title:'Exploratory analysis',pattern:/\b(eda|explor\w*|descriptive|patterns|trends|analy[sz]e)\b/i,skills:['Statistics','Python','Data visualization'],stage:'Analyze',effort:4},
      {title:'Statistical analysis',pattern:/\b(hypothesis|regression|statistical|significance|confidence intervals?)\b/i,skills:['Statistics'],stage:'Analyze',effort:5},
      {title:'Predictive modeling',pattern:/\b(predict\w*|machine learning|classification|forecast\w*)\b/i,skills:['Machine learning','Python'],stage:'Analyze',effort:7},
      {title:'Business recommendations',pattern:/\b(recommend\w*|strateg(?:y|ic)|business implications)\b/i,skills:['Business strategy','Financial analysis','Research'],stage:'Synthesize',effort:4},
      {title:'Presentation and storytelling',pattern:/\b(present\w*|slides?|storytelling|visualiz\w*|dashboard)\b/i,skills:['Presentation','Data visualization'],stage:'Communicate',effort:4},
      {title:'Written deliverable',pattern:/\b(report|memo|write.up|executive summary|essay|paper)\b/i,skills:['Research','Presentation'],stage:'Communicate',effort:4}
    ];
    const segments=(text.match(/[^\n.!?;]+(?:[.!?;]+|$)/g)||[text]).map(s=>s.trim()).filter(Boolean);
    const tasks=[];const warnings=['Text-based interpretation, not AI. Review the extracted workstreams and add any missing requirements.','Effort and stage labels are adjustable planning suggestions; they are not assignment requirements.'];
    const constraints=[];const seen=new Set();
    for(const source of segments){
      if(/\b(do not|don't|must not|should not|without|no|not required|not include|not use|not build)\b/i.test(source)){constraints.push(source);continue;}
      const matches=definitions.filter(d=>d.pattern.test(source));
      if(matches.length){for(const d of matches){const key=d.title+'|'+source;if(seen.has(key))continue;seen.add(key);tasks.push({...d,id:'t'+(tasks.length+1),description:source,source,dependencies:[]});}}
      else if(/\b(create|design|develop|build|prepare|submit|write|produce|conduct|evaluate|compare|research|investigate|identify|assess|propose|explain|include|deliver|calculate|implement|test|interview|survey|document|outline|summari[sz]e|review|collect|define|state)\b/i.test(source)||/^\s*(?:[-*•]|\d+[.)])/.test(source)){
        const title=source.replace(/^\s*(?:[-*•]|\d+[.)])\s*/,'').replace(/[.!?;]+$/,'');
        tasks.push({id:'t'+(tasks.length+1),title:title.length>100?title.slice(0,97)+'…':title,description:source,source,skills:[],effort:3,stage:'Plan',dependencies:[]});
      }
    }
    if(!tasks.length){const source=segments[0]||text;tasks.push({id:'t1',title:'Clarify the project deliverables',description:source,source,skills:[],effort:2,stage:'Plan',dependencies:[]});warnings.push('No clear action or deliverable was recognized. Edit this workstream to describe what your team needs to produce.');}
    if(tasks.length>25)warnings.push('Only the first 25 workstreams are shown. Review the remaining assignment text for additional requirements.');
    if(constraints.length)warnings.push('Constraints to preserve: '+constraints.join(' '));
    if(!deadline&&!/\b(due|deadline|submit by)\b/i.test(text))warnings.push('No deadline was supplied. Confirm the due date with your team.');
    const selected=tasks.slice(0,25).map(({pattern,...task})=>task);
    return {tasks:selected,warnings,mode:'Text-based interpretation'};
  }
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
      const breakdown=interpretText(body.instructions,body.deadline);
      const tasks=structuredClone(breakdown.tasks);
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
          const match=t.skills.some(s=>(members[who].skills+' '+members[who].preferences).toLowerCase().includes(s.toLowerCase()));
          t.owners=[members[who].id];t.reason=k===0?(match?'Matches reported skills or preferences.':'No clear skill match; confirm this owner with your team.'):k===1?'Assigned to balance estimated effort.':'Assigned by project stage; review the handoffs with your team.';load[who]+=t.effort;
        }
        return {strategy,tasks:rows};
      });
      const id=crypto.randomUUID();
      const p={id,name:body.name,instructions:body.instructions,deadline:body.deadline,members,breakdown,plans,saved:null,poll:null,confirmed:null,availability:{}};
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
      location.href='/';
    };
  });
})();
