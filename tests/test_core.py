import copy
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import engine
import server

class PlanningTests(unittest.TestCase):
    def test_descriptive_does_not_invent_model(self):
        result=engine.interpret('Clean the data. Perform descriptive analysis. Present a report. Do not build predictive models.')
        self.assertNotIn('Predictive modeling',[t['title'] for t in result['tasks']])
        self.assertTrue(all(t['source'] for t in result['tasks']))

    def test_skills_and_balance(self):
        tasks=engine.interpret('Clean the data. Build predictive models. Develop business recommendations. Present slides.')['tasks']
        members=[dict(id='a',skills='Python, Machine learning',preferences=''),dict(id='b',skills='SQL, Data cleaning',preferences=''),dict(id='c',skills='Business strategy, Presentation',preferences='')]
        plans=engine.allocations(tasks,members)
        self.assertEqual(len(plans),3)
        model=next(t for t in plans[0]['tasks'] if t['title']=='Predictive modeling')
        self.assertEqual(model['owners'],['a'])
        self.assertTrue(all(len(p['tasks'])==len(tasks) for p in plans))
        self.assertGreater(len({tuple(tuple(t['owners']) for t in p['tasks']) for p in plans}),1)

    def test_duration_offsets_and_gaps(self):
        poll=dict(duration=45,ranges=[['2026-11-02T09:00:00-08:00','2026-11-02T11:00:00-08:00']])
        availability={'a':[['2026-11-02T17:00:00Z','2026-11-02T18:00:00Z']],'b':[['2026-11-02T12:00:00-05:00','2026-11-02T12:45:00-05:00']]}
        options=engine.windows(poll,availability,[dict(id='a'),dict(id='b')])
        self.assertEqual(sum(w['full'] for w in options),1)
        self.assertEqual(options[0]['start'],'2026-11-02T17:00:00+00:00')
        availability['b']=[['2026-11-02T17:00:00Z','2026-11-02T17:15:00Z'],['2026-11-02T17:30:00Z','2026-11-02T18:00:00Z']]
        self.assertFalse(any(w['full'] for w in engine.windows(poll,availability,[dict(id='a'),dict(id='b')])))

class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        server.DB=Path(cls.tmp.name)/'test.sqlite3'
        server.init_db()
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.http.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.tmp.cleanup()

    def request(self,path,payload=None,owner='',expected=200):
        headers={'Content-Type':'application/json'}
        if owner: headers['X-Owner-Key']=owner
        req=urllib.request.Request(self.base+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
        try:
            with urllib.request.urlopen(req) as r:
                self.assertEqual(r.status,expected)
                return json.load(r)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code,expected)
            return json.load(e)

    @patch.dict(os.environ,{'OPENAI_API_KEY':'','OPENAI_MODEL':''})
    def test_kickoff_and_access_boundaries(self):
        created=self.request('/api/projects',dict(name='Test team',instructions='Clean the data. Analyze patterns and present business recommendations in slides.',members=[dict(name='Alex',skills='Python'),dict(name='Sam',skills='Presentation')]),expected=201)
        p=created['project']; key=created['owner']; path='/api/projects/'+p['id']
        self.request(path,expected=404)
        tasks=p['plans'][0]['tasks']
        self.request(path+'/plan',dict(strategy='Strength-based',tasks=tasks),expected=403)
        self.request(path+'/plan',dict(strategy='Strength-based',tasks=tasks),owner=key)
        self.request(path+'/poll',dict(duration=45,timezone='UTC',ranges=[['2026-11-02T17:00:00Z','2026-11-02T19:00:00Z']]),owner=key)
        public=self.request(path)
        self.assertNotIn('instructions',public)
        self.assertNotIn('plans',public)
        self.assertNotIn('skills',public['members'][0])
        intervals=[['2026-11-02T17:00:00Z','2026-11-02T18:00:00Z']]
        for m in p['members']:
            submitted=self.request(path+'/availability',dict(member=m['id'],intervals=intervals))
            self.request(path+'/availability',dict(member=m['id'],intervals=[]),expected=403)
            self.request(path+'/availability',dict(member=m['id'],intervals=intervals,token=submitted['token']))
        result=self.request(path)
        self.assertTrue(result['windows'][0]['full'])
        self.request(path+'/confirm',dict(start=result['windows'][0]['start']),expected=403)
        self.request(path+'/confirm',dict(start=result['windows'][0]['start']),owner=key)
        self.assertIsNotNone(self.request(path)['confirmed'])
        with server.database() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM responses WHERE project=?',(p['id'],)).fetchone()[0],2)

    def test_bad_pdf_is_actionable(self):
        response=self.request('/api/extract',dict(data='bm90IGEgcGRm'),expected=400)
        self.assertIn('PDF',response['error'])

if __name__=='__main__':
    unittest.main()
