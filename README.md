# ORBIT

**Organized Resources, Boards, Info & Timetable**: one place for Plaksha students to find course material, discuss it, and see campus events alongside their own classes.

> Explorer Track project for Coding Café (FM102), 2026, built by Ahaan Makhija.
> Status: **Core complete** (accounts, library, calendar). Next: course boards, then feature freeze.

---

## The problem

Course notes, slides and past papers are scattered across Drive folders, WhatsApp groups and emails. Campus events and class timetables live in separate places too. Finding the right file or remembering what's on this week takes longer than it should.

## What ORBIT does

| Module | What you can do | Status |
| --- | --- | --- |
| **Accounts** | Sign up, log in, see your profile. Two roles: student and staff. | ✅ Built |
| **Courses** | Browse the catalogue, join and leave the courses you take. Staff create courses. | ✅ Built |
| **Resource library** | Upload files (PDF, DOCX, PPTX, PNG, JPG; 10 MB max) or save links (Google Drive, OneDrive, YouTube, any web page). Staff uploads are stamped **official**. Search titles and tags, filter by type and source, edit or delete your own. | ✅ Built |
| **Calendar** | One calendar that merges campus events (posted by staff) with your own weekly classes. Week, month and list views, with layers you can switch on and off. | ✅ Built |
| **Boards** | A discussion board per course: threads, replies and file attachments. | Week 6 |

### Stretch goals (only if the core is done early)

- Pick files straight from Google Drive using Google sign-in
- Export your calendar as an `.ics` file for Google/Outlook
- Email reminders before events
- Upvotes and reporting on posts

## Getting started

Requires Python 3.11 or newer.

```bash
git clone https://github.com/AhaanMakhija/Coding-Cafe-Project-Track.git orbit
cd orbit
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

Install the dependencies and start the app:

```bash
pip install -r requirements.txt
flask --app app run --debug
```

Open <http://127.0.0.1:5000>. The database (`instance/orbit.db`) and its tables are created automatically on first run.

### Creating a staff account

Everyone signs up as a student. To make an account staff (so it can create courses, post campus events and have its uploads marked official), sign up in the browser first, then run:

```bash
flask --app app make-staff you@example.com
```

This is a terminal command on purpose: only someone with access to the server can promote an account, so there is no web page a student could use to make themselves staff.

### Configuration

Settings live in [`config.py`](config.py). For anything other than local development, set these environment variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Signs login cookies and CSRF tokens | A development-only value |
| `DATABASE_URL` | Database location (any SQLAlchemy URL) | SQLite file at `instance/orbit.db` |

### Running the tests

```bash
pytest -q
```

184 tests cover models, every route, permissions (logged out, student, staff), bad input and the upload safety rules. Tests use an in-memory database and a temporary upload folder, so they never touch your real data.

## Tech stack

| Layer | Choice |
| --- | --- |
| Web framework | Flask, one Blueprint per feature |
| Templates and styling | Jinja2 + a hand-written stylesheet (`app/static/css/orbit.css`) |
| Database | SQLite via Flask-SQLAlchemy |
| Auth | Flask-Login + Werkzeug password hashing |
| Forms | Flask-WTF (validation + CSRF protection) |
| Calendar UI | FullCalendar 6, fed by two JSON routes |
| Tests | pytest + Flask's test client |

## Architecture

```
Browser (Jinja pages + FullCalendar)
        │  HTTP requests
        ▼
┌───────────────── Flask app: create_app() ─────────────────┐
│  auth/          resources/         calendar/     forum/   │   one Blueprint per feature
│  /auth/...      /courses/...       /calendar/... (Week 6) │
└──────────────────────────┬────────────────────────────────┘
             SQLAlchemy    │   saved files
             ┌─────────────┴─────────────┐
             ▼                           ▼
     SQLite database               uploads/ folder
     (instance/orbit.db)           (random file names)
```

`create_app()` in [`app/__init__.py`](app/__init__.py) is an **application factory**: it builds the app from a config class, so tests can create a separate app with `TestConfig`. Shared extension objects (`db`, `login_manager`, `csrf`) live in [`app/extensions.py`](app/extensions.py) to avoid circular imports.

### Data model

`Course` is the hub most other tables point to.

| Table | Key fields | Rules enforced by the database |
| --- | --- | --- |
| `User` | name, email, password_hash, role | Email unique (stored lower-case); role is student or staff |
| `Course` | code, name, term | Code unique per term |
| `enrollment` | user_id, course_id | Many-to-many link between users and courses |
| `Resource` | title, kind, file_path *or* url, type, tags, is_official | Exactly one of file_path / url, matching kind |
| `Event` | title, start_at, end_at, location, description | Ends after it starts |
| `ClassSlot` | weekday (0 = Monday), start_time, end_time, room | Weekday 0–6; ends after it starts |
| `Thread` | course_id, author_id, title, body | |
| `Post` | thread_id, author_id, body, attachment_resource_id | Attachment is a `Resource`, reusing the upload code |

### Project structure

```
app/
  __init__.py        create_app(): config, extensions, Blueprints, error pages
  extensions.py      db, login_manager, csrf
  models.py          the eight tables
  auth/              sign up, log in, log out, profile, `flask make-staff`
  resources/         courses, enrollment, uploads and links, search, edit/delete
    storage.py         safe file saving (allow-list, random names)
    queries.py         search and filter logic
    links.py           "Google Drive", "YouTube"... labels for saved links
  calendar/          campus events, weekly classes, JSON feeds
    feeds.py           converts events/classes to FullCalendar's format
  templates/         Jinja pages, one folder per Blueprint
  static/            orbit.css, calendar.js
tests/               pytest, one file per area
uploads/             saved files (git-ignored)
instance/            SQLite database (git-ignored)
config.py
requirements.txt
```

## Security

| Risk | How ORBIT handles it |
| --- | --- |
| Stolen passwords | Only salted hashes are stored (Werkzeug) |
| Forged form submissions | CSRF token on every form; logout, join, leave and delete are POST-only |
| Students acting as staff | Staff role only via `flask make-staff`; staff pages return 403 for students |
| Dangerous uploads | Allow-list of file types, 10 MB limit, random stored names (no `../` tricks or overwrites), always served as downloads |
| Malicious links | Only `http://` and `https://` links are accepted, so `javascript:` links are rejected |
| Redirect to a fake site after login | `?next=` only accepts paths on ORBIT itself |
| Account discovery | Wrong email and wrong password give the same login error |
| Script injection | Jinja escapes all user text; user text is never placed inside JavaScript |

## Roadmap

| Explorer week | Course week | Goal | Status |
| --- | --- | --- | --- |
| 1 | 5 | Proposal, repo, Flask skeleton, models | ✅ Done |
| 2 | 6 | Design doc, accounts and roles | ✅ Accounts done; design doc in progress |
| 3 | 7 | Courses, upload and save links (first prototype) | ✅ Done |
| 4 | 8 | Browse, filter, search, official badge, edit/delete | ✅ Done |
| 5 | 9 | **Midpoint checkpoint.** Calendar: events + classes | ✅ Done |
| 6 | 10 | Boards. **Feature freeze** | Next |
| 7 | 11 | Testing, error handling, upload limits | Ongoing (184 tests) |
| 8 | 12 | Bug fixes, cleanup, polish, demo seed data | |
| 9 | 13 | Documentation | |
| 10 | 14 | Demo prep and buffer | |
| — | 15 | Final presentation | |

## Design decisions

- **Drive links instead of the Drive API.** Saving a share link covers "keep your documents in one place" without Google sign-in setup, which could take weeks. Links also have no size limit, so they're the fallback for files over 10 MB. Full Drive integration is a stretch goal.
- **SQLite first.** A single file with zero setup; the models are written with SQLAlchemy so moving to Postgres later is a config change.
- **Blueprint per feature.** Keeps code modular and lets each part be tested and demoed on its own.
- **Rules in the database as well as the forms.** Forms give friendly error messages; database constraints (unique emails, file *or* link, end after start) are the safety net if a bug ever skips a form check.
- **Weekly classes are stored once.** A class slot is a weekday plus times, and FullCalendar repeats it every week, instead of storing a row for every date.
- **Staff promotion is a terminal command.** An admin web page would need its own permission checks; a command only someone with server access can run is simpler and safer.
- **Own stylesheet instead of a CSS framework.** A "campus catalogue" look (paper, ink, index cards, rubber stamps) that is specific to ORBIT; colours and fonts are variables at the top of `orbit.css`.

## Author

Ahaan Makhija, Plaksha University. Coding Café (FM102) Explorer Track, 2026.
