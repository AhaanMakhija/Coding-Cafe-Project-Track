# ORBIT

**Organized Resources, Boards, Info & Timetable**: one place for Plaksha students to find course material, discuss it, and see campus events alongside their own classes.

> Explorer Track project for Coding Café (FM102), 2026, built by Ahaan Makhija.
> Status: **Complete and polished.** All modules built, 320 tests at 99% coverage, demo data ready. After the Week 6 freeze, user testing led to course calendars, AM/PM time pickers, venue clash checks, `.ics` export and an admin role.

---

## The problem

Course notes, slides and past papers are scattered across Drive folders, WhatsApp groups and emails. Campus events and class timetables live in separate places too. Finding the right file or remembering what's on this week takes longer than it should.

## What ORBIT does

| Module | What you can do | Status |
| --- | --- | --- |
| **Accounts** | Sign up, log in, see your profile. Three roles: student, staff and admin. | ✅ Built |
| **Courses** | Browse the catalogue, join and leave the courses you take. Staff create courses. | ✅ Built |
| **Resource library** | Upload files (PDF, DOCX, PPTX, PNG, JPG; 10 MB max) or save links (Google Drive, OneDrive, YouTube, any web page). Staff uploads are stamped **official**. Search titles and tags, filter by type and source, edit or delete your own. | ✅ Built |
| **Calendar** | One calendar that merges campus events (posted by staff), your courses' events (exams, deadlines, study groups, added by anyone in the course) and your own weekly classes. Week, month and list views, with layers you can switch on and off. Times are picked and shown with AM/PM. Two events can't book the same venue at the same time. Download any course's calendar as an `.ics` file for Google Calendar, Outlook or Apple Calendar. | ✅ Built |
| **Boards** | A discussion board per course. Start threads, reply, and attach files to replies (attachments also appear in the library, tagged `#board`). Staff replies are stamped so answers stand out. Authors and staff can delete. | ✅ Built |
| **Admin** | Admins see every account with its courses and activity, search and filter them, and change any account's name, email, role or password. | ✅ Built |

### Stretch goals

- ~~Export your calendar as an `.ics` file for Google/Outlook~~ ✅ done, per course
- Pick files straight from Google Drive using Google sign-in
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

### Roles: student, staff and admin

| Role | Can do |
| --- | --- |
| Student | Join courses, add resources and course events, post on boards, keep a timetable |
| Staff | Everything a student can, plus create courses, post campus-wide events, and have uploads stamped official |
| Admin | Everything staff can, plus see and change every account on the **Admin** page |

**Becoming an admin:** on the sign-up page choose **Admin** and type the admin code. The code is the `ADMIN_SIGNUP_CODE` setting, which is `admin` for local demos. Set it to a long secret anywhere real, or anyone could make themselves admin.

**Becoming staff:** an admin changes the account's role on the Admin page. Or, from a terminal on the server:

```bash
flask --app app make-staff you@example.com
```

### Loading demo data

To try ORBIT without typing everything in, fill an empty database with sample courses, files, links, campus events, a weekly timetable and board threads:

```bash
flask --app app seed-demo
```

It prints six demo accounts (three students, two staff, one admin) and one shared password:

| Log in as | To see |
| --- | --- |
| `riya@orbit-demo.edu` | A student with three courses, a full timetable and board posts |
| `meera@orbit-demo.edu` | Staff: create courses, post campus-wide events |
| `admin@orbit-demo.edu` | Admin: the Admin page with every account |

Every course has its own sample events (exams, deadlines, office hours, a study group). Dates are worked out from today, so events are always coming up and posts are always recent. Log in as two accounts in two different browsers to see one account's changes appear for the other on refresh.

> **Upgrading from an earlier version?** The database layout changed (events can belong to a course; accounts record when they joined). Run `flask --app app seed-demo --reset`, or delete `instance/orbit.db`, so the tables are recreated.

The command refuses to run on a database that already has accounts. `--reset` replaces everything after asking for confirmation, and `--password` sets the password instead of generating a random one.

### Configuration

Settings live in [`config.py`](config.py). For anything other than local development, set these environment variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Signs login cookies and CSRF tokens | A development-only value |
| `DATABASE_URL` | Database location (any SQLAlchemy URL) | SQLite file at `instance/orbit.db` |
| `ADMIN_SIGNUP_CODE` | Code needed to sign up as an admin | `admin` (demo only) |

### Running the tests

```bash
pytest -q
```

320 tests cover the models, every route, permissions (logged out, student, staff, admin), bad input, the upload safety rules, venue clashes, the `.ics` format, error pages and the demo command. Tests use an in-memory database and a temporary upload folder, so they never touch your real data.

To see which lines the tests run:

```bash
pytest -q --cov=app --cov-report=term-missing
```

Coverage is 99%. The only lines not run are the `__repr__` methods used when debugging. Failure paths are tested on purpose, for example a database save that fails after a file was written, to check the file is cleaned up.

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
│  auth/        resources/     calendar/     forum/    admin/   │  one Blueprint
│  /auth/...    /courses/...   /calendar/... /board/   /admin/  │  per feature
└──────────────────────────────┬────────────────────────────────┘
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
| `User` | name, email, password_hash, role, created_at | Email unique (stored lower-case); role is student, staff or admin |
| `Course` | code, name, term | Code unique per term |
| `enrollment` | user_id, course_id | Many-to-many link between users and courses |
| `Resource` | title, kind, file_path *or* url, type, tags, is_official | Exactly one of file_path / url, matching kind |
| `Event` | title, start_at, end_at, location, description, course_id (empty = campus-wide) | Ends after it starts |
| `ClassSlot` | weekday (0 = Monday), start_time, end_time, room | Weekday 0–6; ends after it starts |
| `Thread` | course_id, author_id, title, body | |
| `Post` | thread_id, author_id, body, attachment_resource_id | Attachment is a `Resource`, reusing the upload code |

### Project structure

```
app/
  __init__.py        create_app(): config, extensions, Blueprints, security headers
  extensions.py      db, login_manager, csrf
  errors.py          friendly 400/403/404/405/413/500 pages
  demo.py            `flask seed-demo` sample data
  models.py          the eight tables
  auth/              sign up, log in, log out, profile, `flask make-staff`
  resources/         courses, enrollment, uploads and links, search, edit/delete
    storage.py         safe file saving (allow-list, random names)
    queries.py         search and filter logic
    links.py           "Google Drive", "YouTube"... labels for saved links
  calendar/          campus and course events, weekly classes, JSON feeds
    feeds.py           converts events/classes to FullCalendar's format
    venues.py          the "one event per venue at a time" rule
    ics.py             builds .ics calendar files
  forum/             course boards: threads, replies, attachments
  admin/             all accounts, details and editing (admins only)
  permissions.py     who may post, edit and delete (shared by library and boards)
  template_filters.py  "3 files", "3 hours ago" helpers for templates
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
| Students acting as staff or admin | Sign-up only creates students, or admins who know the admin code (compared in constant time); roles change only on the Admin page or with `flask make-staff`; staff and admin pages return 403 to everyone else |
| Locking everyone out | The last admin can't be demoted |
| Admins reading passwords | Impossible: only hashes are stored. Admins can set a new password, never see one |
| Dangerous uploads | Allow-list of file types, 10 MB limit, random stored names (no `../` tricks or overwrites), always served as downloads |
| Malicious links | Only `http://` and `https://` links are accepted, so `javascript:` links are rejected |
| Redirect to a fake site after login | `?next=` only accepts paths on ORBIT itself |
| Account discovery | Wrong email and wrong password give the same login error |
| Script injection | Jinja escapes all user text; user text is never placed inside JavaScript |
| Cookie theft and cross-site requests | Login cookies are `HttpOnly` (hidden from JavaScript) and `SameSite=Lax` (not sent with forms from other sites) |
| Browser guessing file types, clickjacking | `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` on every response |
| Leaking internals | Error pages never show error details; a failed request rolls back its database changes |

## Roadmap

| Explorer week | Course week | Goal | Status |
| --- | --- | --- | --- |
| 1 | 5 | Proposal, repo, Flask skeleton, models | ✅ Done |
| 2 | 6 | Design doc, accounts and roles | ✅ Accounts done; design doc in progress |
| 3 | 7 | Courses, upload and save links (first prototype) | ✅ Done |
| 4 | 8 | Browse, filter, search, official badge, edit/delete | ✅ Done |
| 5 | 9 | **Midpoint checkpoint.** Calendar: events + classes | ✅ Done |
| 6 | 10 | Boards. **Feature freeze** | ✅ Done |
| 7 | 11 | Testing, error handling, upload limits | ✅ Done: 99% coverage, friendly error pages |
| 8 | 12 | Bug fixes, cleanup, polish, demo seed data | ✅ Done: `flask seed-demo`, security headers, mobile polish |
| 9 | 13 | Documentation | ✅ README done; design doc in progress |
| 10 | 14 | Demo prep and buffer. Buffer used for changes from user testing: course calendars, AM/PM times, venue clashes, `.ics` export, admin role | ✅ Changes done (320 tests); demo rehearsal next |
| — | 15 | Final presentation | |

## Known limitations

Honest notes on what ORBIT does not do yet, and what would come next:

- **No database migrations.** Tables are created on first run; changing a model means recreating the database. Flask-Migrate would fix this.
- **File types are checked by extension, not content.** A renamed file passes the check, but it is always served as a download with `nosniff`, so it never runs in the browser.
- **One time zone.** Events are stored as campus wall-clock times, which suits a single campus. `.ics` files use the same "floating" local times.
- **Events fit within one day.** The form has one date with a start and end time; multi-day events aren't supported.
- **Weekly classes don't block venues.** Many students list the same lecture in the same room, so only one-off events take part in the clash check.
- **No pagination.** Long libraries and boards show every item on one page.
- **No password reset or email.** These would need an email service.

## Design decisions

- **Drive links instead of the Drive API.** Saving a share link covers "keep your documents in one place" without Google sign-in setup, which could take weeks. Links also have no size limit, so they're the fallback for files over 10 MB. Full Drive integration is a stretch goal.
- **SQLite first.** A single file with zero setup; the models are written with SQLAlchemy so moving to Postgres later is a config change.
- **Blueprint per feature.** Keeps code modular and lets each part be tested and demoed on its own.
- **Rules in the database as well as the forms.** Forms give friendly error messages; database constraints (unique emails, file *or* link, end after start) are the safety net if a bug ever skips a form check.
- **Weekly classes are stored once.** A class slot is a weekday plus times, and FullCalendar repeats it every week, instead of storing a row for every date.
- **Staff promotion is a terminal command.** An admin web page would need its own permission checks; a command only someone with server access can run is simpler and safer.
- **Board attachments are library resources.** A file attached to a reply is saved as a `Resource` by the library's upload code, so it gets the same type allow-list, size limit and safe file names, and stays findable in the library. Deleting the reply removes the file; deleting the file from the library keeps the reply.
- **Relative times on the boards.** "3 hours ago" is worked out from UTC timestamps, so it's right for every viewer without converting time zones.
- **Times picked from a dropdown, not the browser's time box.** `<input type="time">` looks different on every computer, and some show 24-hour time with no AM/PM, which made people save 2 AM when they meant 2 PM. A list of 15-minute slots labelled "2:30 PM" reads the same everywhere.
- **Venue clashes are checked against the whole database.** The rule lives in `calendar/venues.py` and runs in the form, so it applies to every account and to edits as well as new events. Two events overlap when each starts before the other ends, so back-to-back bookings are allowed.
- **`.ics` written by hand.** The iCalendar format is plain text; ORBIT needs only a handful of its rules (escaping, line folding, weekly repeats), so a small module is easier to explain than a library.
- **Admin code from config.** It defaults to `admin` for demos, but a real deployment sets `ADMIN_SIGNUP_CODE` to a secret, so the code in a public repository unlocks nothing.
- **Demo data is generated, not copied in.** `flask seed-demo` builds data relative to today, so the demo always looks current, and it refuses to overwrite real data unless told to.
- **Own stylesheet instead of a CSS framework.** A "campus catalogue" look (paper, ink, index cards, rubber stamps) that is specific to ORBIT; colours and fonts are variables at the top of `orbit.css`.

## Author

Ahaan Makhija, Plaksha University. Coding Café (FM102) Explorer Track, 2026.
