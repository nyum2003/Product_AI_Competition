"""Package the browser demo for GitHub Pages, including project-site paths."""
from pathlib import Path
import shutil

root = Path(__file__).parent
source, target = root / 'demo', root / 'docs'
target.mkdir(exist_ok=True)
for name in ('index.html', 'app.js', 'style.css', 'fixtures.js', 'demo.js'):
    text = (source / name).read_text(encoding='utf-8')
    if name == 'index.html':
        text = text.replace('href="/"', 'href="./"')
        text = text.replace('href="/style.css"', 'href="./style.css"')
        for asset in ('app', 'demo', 'fixtures'):
            text = text.replace(f'src="/{asset}.js"', f'src="./{asset}.js"')
    if name == 'demo.js':
        text = text.replace("location.href='/'", "location.href=location.pathname")
    if name == 'app.js':
        text = "const demoHome=location.origin+location.pathname;\n" + text
        text = text.replace('href="/"', 'href="${demoHome}"')
        text = text.replace("location.href='/'", 'location.href=demoHome')
        text = text.replace('`/project/${project.id}#owner=${owner}`', '`?view=project&id=${project.id}#owner=${owner}`')
        text = text.replace("location.origin+'/poll/'+project.id", "demoHome+'?view=poll&id='+project.id")
        text = text.replace('`${location.origin}/poll/${project.id}#member=', '`${demoHome}?view=poll&id=${project.id}#member=')
        text = text.replace("const match=location.pathname.match(/^\\/(project|poll)\\/([\\w-]+)$/);", "const query=new URLSearchParams(location.search);const view=query.get('view'),id=query.get('id');const match=['project','poll'].includes(view)&&/^[\\w-]+$/.test(id||'')?['',view,id]:null;")
        text = text.replace("history.replaceState(null,'',location.pathname)", "history.replaceState(null,'',location.pathname+location.search)")
    (target / name).write_text(text, encoding='utf-8')
(target / '.nojekyll').write_text('', encoding='utf-8')
print('GitHub Pages demo ready in docs/; existing documents preserved.')
