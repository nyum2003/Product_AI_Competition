"""Build the static, browser-only usability demo. No credentials or user data."""
import json
from pathlib import Path
from engine import interpret

root=Path(__file__).parent
out=root/'demo'
out.mkdir(exist_ok=True)
sample='Define the business problem and KPIs. Clean the dataset. Perform exploratory analysis. Build a predictive classification model. Develop business recommendations. Present slides. Submit an executive summary.'
fixture=interpret(sample)
(out/'fixtures.js').write_text('window.demoFixture='+json.dumps(fixture)+';',encoding='utf-8')
(out/'style.css').write_text((root/'static/style.css').read_text(encoding='utf-8')+'\n.demo-banner{padding:12px 24px;background:#e6edda;text-align:center;font-size:13px;border-bottom:1px solid #cbd9bc}.demo-banner button{padding:3px 10px;margin-left:12px;font-size:12px}\n',encoding='utf-8')
html=(root/'static/index.html').read_text(encoding='utf-8').replace('<script src="/app.js" defer>','<script src="/fixtures.js" defer></script><script src="/demo.js" defer></script><script src="/app.js" defer>')
html=html.replace('<div class="app-shell">','<div class="demo-banner">Clickable demo · Sample plans · Changes stay in this browser · No shared responses <button id="reset-demo">Reset demo</button></div><div class="app-shell">')
(out/'index.html').write_text(html,encoding='utf-8')
js=(root/'static/app.js').read_text(encoding='utf-8').replace('async function api(path,body){','async function api(path,body){return window.demoAPI(path,body);}\nasync function unusedServerAPI(path,body){')
js=js.replace('Text-based PDFs supported. You can review the extracted text before continuing.','PDF upload is available in the full app. For this demo, paste text or try the example.')
js=js.replace('type="file" accept=', 'type="file" disabled accept=')
js=js.replace('No assignment text is sent to an AI service.','No assignment text is sent to an AI service. Plans use sample workstreams in this demo.')
js=js.replace('Share this link with your team. Your organizer key is never included.','Demo links work only in this browser. To simulate responses, select each sample member and save availability.')
js=js.replace('Only people with your private links can access this project. Keep the organizer link to yourself.','This is a browser-only demo. Use sample information; changes are not shared with other visitors.')
(out/'app.js').write_text(js,encoding='utf-8')
(out/'vercel.json').write_text(json.dumps({'framework':None,'buildCommand':None,'outputDirectory':'.','rewrites':[{'source':'/project/:path*','destination':'/index.html'},{'source':'/poll/:path*','destination':'/index.html'}]},indent=2),encoding='utf-8')
print('Built demo/ for static hosting.')
