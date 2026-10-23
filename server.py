"""CaseFlow MVP: Python standard-library server + SQLite; no frontend build."""
import base64
import io
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from engine import ai_interpret, allocations, instant, windows

ROOT = Path(__file__).parent
DB = Path(os.getenv('CASEFLOW_DB', str(ROOT/'data'/'caseflow.sqlite3')))

@contextmanager
def database():
    conn=sqlite3.connect(DB,timeout=15)
    try:
        with conn:
            yield conn
    finally:
        conn.close()

def init_db():
    DB.parent.mkdir(parents=True,exist_ok=True)
    with database() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, owner TEXT NOT NULL, body TEXT NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS responses (project TEXT, member TEXT, token TEXT NOT NULL, intervals TEXT NOT NULL, PRIMARY KEY(project,member))')

def require(condition, message, status=400):
    if not condition:
        raise APIError(message,status)

class APIError(Exception):
    def __init__(self,message,status=400):
        super().__init__(message)
        self.status=status

def text(value, limit=1000):
    require(isinstance(value,str) and len(value)<=limit,'Invalid or oversized text')
    return value.strip()

def validate_tasks(tasks, members):
    require(isinstance(tasks,list) and 1<=len(tasks)<=40,'Include 1–40 tasks')
    ids={m['id'] for m in members}
    for i,t in enumerate(tasks):
        require(isinstance(t,dict),'Invalid task')
        t['title']=text(t.get('title'),200)
        require(t['title'],'Task title is required')
        t['description']=text(t.get('description',''),3000)
        require(isinstance(t.get('effort'),(int,float)) and not isinstance(t['effort'],bool) and 0.25<=t['effort']<=100,'Effort must be between 0.25 and 100 hours')
        require(isinstance(t.get('owners'),list) and 1<=len(t['owners'])<=len(ids) and set(t['owners'])<=ids and len(set(t['owners']))==len(t['owners']),'Choose valid task owners')
        t['id']=f't{i+1}'
        t['source']=text(t.get('source',''),3000)
        t['stage']=text(t.get('stage','Plan'),100)
        t['dependencies']=[text(d,200) for d in t.get('dependencies',[])[:20]]
    return tasks

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass  # Capability URLs and assignment contents must not appear in access logs.

    def send(self,value,status=200):
        raw=json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path.startswith('/api/'):
            self.api('GET')
            return
        path=urlparse(self.path).path
        filename={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}.get(path,'index.html' if path.startswith(('/project/','/poll/')) else None)
        if not filename:
            self.send({'error':'Not found'},404)
            return
        raw=(ROOT/'static'/filename).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type',{'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css; charset=utf-8'}[filename.split('.')[-1]])
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        self.api('POST')

    def api(self,method):
        try:
            origin=self.headers.get('Origin')
            require(not origin or urlparse(origin).netloc==self.headers.get('Host'),'Cross-origin request denied',403)
            n=int(self.headers.get('Content-Length','0'))
            require(0<=n<=8_000_000,'Request exceeds 8 MB',413)
            payload=json.loads(self.rfile.read(n)) if n else {}
            require(isinstance(payload,dict),'Invalid JSON object')
            parts=urlparse(self.path).path.strip('/').split('/')
            if parts==['api','config'] and method=='GET':
                self.send({'ai':bool(os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_MODEL'))})
                return
            if parts==['api','extract'] and method=='POST':
                try:
                    from pypdf import PdfReader
                    data=base64.b64decode(payload.get('data',''),validate=True)
                    require(len(data)<=5_000_000 and data.startswith(b'%PDF'),'Upload a PDF under 5 MB')
                    reader=PdfReader(io.BytesIO(data))
                    require(len(reader.pages)<=60,'Use a PDF with 60 pages or fewer')
                    extracted='\n'.join(p.extract_text() or '' for p in reader.pages)
                    require(len(extracted.strip())>=30,'No readable text found. Paste the instructions or use a text-based PDF.')
                    require(len(extracted)<=50000,'Document too long. Paste the relevant assignment sections.')
                    self.send({'text':extracted})
                except APIError:
                    raise
                except Exception:
                    raise APIError('Could not read this PDF. Try an unlocked, text-based PDF or paste the instructions.')
                return
            if parts==['api','projects'] and method=='POST':
                name=text(payload.get('name'),150)
                instructions=text(payload.get('instructions'),50000)
                require(name and len(instructions)>=30,'Enter a project name and at least 30 characters of instructions')
                raw=payload.get('members')
                require(isinstance(raw,list) and 2<=len(raw)<=12,'Enter 2–12 team members')
                members=[dict(id=secrets.token_urlsafe(9),name=text(m.get('name'),100),skills=text(m.get('skills',''),500),preferences=text(m.get('preferences',''),500)) for m in raw]
                require(all(m['name'] for m in members) and len({m['name'].casefold() for m in members})==len(members),'Use a unique name for every member')
                interpreted=ai_interpret(instructions)
                project=dict(id=secrets.token_urlsafe(24),name=name,instructions=instructions,deadline=text(payload.get('deadline',''),30),members=members,breakdown=interpreted,plans=allocations(interpreted['tasks'],members),saved=None,poll=None,confirmed=None)
                owner=secrets.token_urlsafe(32)
                with database() as c:
                    c.execute('INSERT INTO projects VALUES (?,?,?)',(project['id'],owner,json.dumps(project)))
                self.send({'project':project,'owner':owner},201)
                return
            require(len(parts)>=3 and parts[:2]==['api','projects'],'Not found',404)
            pid=parts[2]
            with database() as conn:
                # Serialize read/modify/write operations, avoiding lost availability updates.
                conn.execute('BEGIN IMMEDIATE')
                row=conn.execute('SELECT owner,body FROM projects WHERE id=?',(pid,)).fetchone()
                require(row,'Project not found',404)
                project=json.loads(row[1])
                owner=secrets.compare_digest(self.headers.get('X-Owner-Key',''),row[0])
                response_rows=conn.execute('SELECT member,intervals FROM responses WHERE project=?',(pid,)).fetchall()
                availability={m:json.loads(a) for m,a in response_rows}
                action=parts[3] if len(parts)>3 else ''
                if method=='GET':
                    if not owner:
                        require(project['poll'],'Poll not available',404)
                        project.pop('instructions',None)
                        project.pop('breakdown',None)
                        project.pop('plans',None)
                        project['members']=[dict(id=m['id'],name=m['name']) for m in project['members']]
                    project['submitted']=list(availability)
                    project['windows']=windows(project['poll'],availability,project['members']) if project['poll'] else []
                    self.send(project)
                    return
                if action=='availability':
                    require(project['poll'],'Create a poll first')
                    member=payload.get('member')
                    require(member in {m['id'] for m in project['members']},'Unknown participant')
                    old=conn.execute('SELECT token FROM responses WHERE project=? AND member=?',(pid,member)).fetchone()
                    require(not old or secrets.compare_digest(old[0],str(payload.get('token',''))),'This name already has a response. Use the original browser or participant edit link.',403)
                    intervals=payload.get('intervals')
                    require(isinstance(intervals,list) and len(intervals)<=300,'Too many availability intervals')
                    normalized=[]
                    for pair in intervals:
                        require(isinstance(pair,list) and len(pair)==2,'Invalid interval')
                        a,b=map(instant,pair)
                        require(a<b and any(instant(x)<=a<b<=instant(y) for x,y in project['poll']['ranges']),'Availability must fall within proposed times')
                        normalized.append([a.isoformat(),b.isoformat()])
                    token=old[0] if old else secrets.token_urlsafe(32)
                    conn.execute('INSERT INTO responses VALUES (?,?,?,?) ON CONFLICT(project,member) DO UPDATE SET intervals=excluded.intervals',(pid,member,token,json.dumps(normalized)))
                    project['confirmed']=None
                    result={'token':token}
                else:
                    require(owner,'Organizer access required',403)
                    if action=='plan':
                        strategy=text(payload.get('strategy'),100)
                        project['saved']={'strategy':strategy,'tasks':validate_tasks(payload.get('tasks'),project['members'])}
                    elif action=='poll':
                        require(project['saved'],'Save an allocation first')
                        require(payload.get('duration') in [30,45,60],'Choose 30, 45, or 60 minutes')
                        ranges=payload.get('ranges')
                        require(isinstance(ranges,list) and 1<=len(ranges)<=14,'Propose 1–14 dates')
                        valid=[]
                        for pair in ranges:
                            require(isinstance(pair,list) and len(pair)==2,'Invalid poll range')
                            a,b=map(instant,pair)
                            require(timedelta(minutes=payload['duration'])<=b-a<=timedelta(hours=16),'Date windows must fit the meeting and be at most 16 hours')
                            valid.append([a.isoformat(),b.isoformat()])
                        valid.sort()
                        require(all(instant(valid[i-1][1])<=instant(valid[i][0]) for i in range(1,len(valid))),'Poll dates overlap')
                        project['poll']={'duration':payload['duration'],'ranges':valid,'timezone':text(payload.get('timezone','UTC'),100),'purpose':text(payload.get('purpose','Kickoff meeting'),200)}
                        project['confirmed']=None
                        conn.execute('DELETE FROM responses WHERE project=?',(pid,))
                    elif action=='confirm':
                        require(project['poll'],'Create a poll first')
                        found=next((w for w in windows(project['poll'],availability,project['members']) if w['start']==payload.get('start') and w['count']>0),None)
                        require(found,'Select a valid window with available participants')
                        project['confirmed']=found
                    else:
                        raise APIError('Not found',404)
                    result={'ok':True}
                conn.execute('UPDATE projects SET body=? WHERE id=?',(json.dumps(project),pid))
            self.send(result)
        except APIError as e:
            self.send({'error':str(e)},e.status)
        except (ValueError,TypeError,KeyError,AttributeError):
            self.send({'error':'Invalid request. Check the supplied fields and times.'},400)
        except Exception:
            self.send({'error':'The request could not be completed. Please try again.'},500)

if __name__=='__main__':
    init_db()
    host=os.getenv('HOST','127.0.0.1')
    port=int(os.getenv('PORT','8000'))
    print(f'CaseFlow AI is running at http://{host}:{port}',flush=True)
    ThreadingHTTPServer((host,port),Handler).serve_forever()
