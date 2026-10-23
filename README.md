# CaseFlow AI

A working student-team kickoff MVP: assignment → grounded workstreams → three editable allocations → shared availability poll → confirmed meeting.

## Public browser demo

Open https://nyum2003.github.io/Product_AI_Competition/ . The GitHub Pages demo runs entirely in the browser and now extracts workstreams from custom pasted text, instead of using a fixed customer-churn plan. It preserves source sentences, identifies familiar analytics workstreams and other explicit action sentences, flags negative constraints and unclear prompts, and carries the same tasks through all three allocations and the meeting-purpose suggestion.

This is **text-based interpretation, not AI**. Effort and stage labels are editable suggestions. It may miss requirements or split them imperfectly; review the breakdown. It sends no assignment text to an AI provider. Plans and poll responses remain local to each visitor's browser. PDF uploads and multi-device collaboration require the Python app below. Existing saved demo projects retain their previous breakdown; start a new project to use the updated interpreter.

Run `python build_demo.py` and `python build_pages.py` to regenerate the static files. Publish `docs/` through GitHub Pages. Run `node tests/test_demo.mjs` for custom-text demo checks. Real LLM interpretation requires a separately hosted backend and a provider API key; the optional Python integration below is not active on GitHub Pages.

## Run locally

Python 3.11+ is required. No Node.js or frontend build is needed.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python server.py
```

Open **http://127.0.0.1:8000** and choose **Try an example**, or paste your own assignment. With uv installed, `uv run --with pypdf python server.py` also works.

## What works

- Pasted assignment text and text-based PDF upload (5 MB, 60 pages).
- Team names, optional custom skills and preferences, optional deadline.
- Assignment breakdown with source excerpts and uncertainty flags.
- Strength-based, balanced-workload, and project-stage allocation strategies.
- Editable titles, descriptions, effort, stages, dependencies, and shared ownership; add/remove tasks.
- Saved allocation and Markdown export; estimated workload by member.
- Database-backed participant polls with 30/45/60-minute meetings and 15-minute availability blocks.
- Independent participant responses and revisions without accounts.
- UTC interval calculations, selectable display zones, full-team/partial-team results.
- Organizer meeting confirmation and downloadable `.ics` calendar event.

## AI interpretation (optional)

The app runs without an API key, visibly labeled **Local planning rules**. This fallback matches explicit text to analytical workstreams; it is not an LLM and cannot interpret arbitrary assignments reliably. Review its source excerpts and edit missing deliverables. It excludes modeling unless predictive/modeling terms are present and flags uncertain requirements.

For LLM interpretation, set both variables **in the server environment** before launch:

```powershell
$env:OPENAI_API_KEY = '<your key>'
$env:OPENAI_MODEL = '<a model supporting Responses structured outputs>'
.venv\Scripts\python server.py
```

Never put the key in frontend code or commit it. When configured, assignment text is sent to OpenAI with `store: false`. The backend requests a strict JSON schema, checks exact source grounding, and falls back visibly on API failure. No live AI call was made during development; this integration requires your key and model to validate against your account. API implementation follows the [official structured outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).

## Links and privacy

- Bookmark the organizer URL, including `#owner=…`. It grants edit and confirmation access; keep it private.
- Share **Copy poll link** with teammates. It excludes the organizer key and exposes the saved team plan, names, response status, and aggregate overlap. Original assignment text and raw skills remain organizer-only.
- Each participant response gets a private edit key stored in that browser. **Copy my private edit link** lets that participant move devices. Keep it private. A lost key requires organizer poll recreation in this prototype; there is no identity recovery.
- Responses are first-claim by participant name. This is a small trusted-team capability-link prototype, not verified identity or enterprise authentication. Do not use it for sensitive assignments or untrusted public teams.
- There is no public project listing. Records live in `data/caseflow.sqlite3`, which is excluded from Git. PDF bytes are processed in memory and not retained; extracted assignment text is retained in the project.
- Editing availability clears meeting confirmation so the organizer can reconfirm against current responses.

## Hosting and collaboration

Loopback links only work on the same computer. For teammates on other devices, deploy the Python app behind an HTTPS reverse proxy with a persistent disk, or run on a trusted LAN using `HOST=0.0.0.0` and share the machine's LAN address. No firewall settings are changed by this project. Configure `PORT` as needed and `CASEFLOW_DB` to a durable database path. A sample Dockerfile is included; it needs HTTPS termination and persistent storage in the hosting platform.

Sites hosting uses a Cloudflare Worker runtime and cannot execute this Python server directly. This MVP has not been deployed to Sites. A Worker/D1 port or Python hosting is required for a remote URL. The local preview is fully functional and backed by SQLite.

## Verify

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

Tests cover skill matching, non-invention of predictive modeling for descriptive prompts, duration-aware overlap, time-zone offsets, interval gaps, saved plans, participant response protection, organizer authorization, and privacy of participant reads. Browser QA covers the example kickoff workflow.

## MVP boundaries

No task tracking, team chat, calendar API integrations, reminders, grading, or dataset processing. PDF OCR is not included. Effort is an adjustable planning assumption, not measured time. For production use, add authenticated membership, rate limiting, recovery, expiration/deletion controls, backups, and a production server. `http.server` is intended for the local pilot.

## Structure

`server.py` handles JSON APIs, SQLite persistence, PDF extraction and access control. `engine.py` handles interpretation, allocation and overlap. `static/` contains the responsive build-free interface. `tests/` contains isolated integration and engine tests.
