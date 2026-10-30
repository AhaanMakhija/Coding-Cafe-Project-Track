# ORBIT

**Organized Resources, Boards, Info & Timetable**: one place for Plaksha students to find course material, discuss it, and see campus events alongside their own classes.

> Explorer Track project for Coding Café (FM102), 2026, built by Ahaan Makhija.
> Status: **planning** (Explorer Week 1). Sections marked *planned* describe how things will work once built.

---

## The problem

Course notes, slides and past papers are scattered across Drive folders, WhatsApp groups and emails. Campus events and class timetables live in separate places too. Finding the right file or remembering what's on this week takes longer than it should.

## What ORBIT does

| Module | What you can do |
| --- | --- |
| **Accounts** | Sign up, log in, join the courses you take. Two roles: student and staff. |
| **Resource library** | Upload files (PDF, DOCX, PPTX, images; 10 MB max) or save links (Google Drive, OneDrive, any URL) to a course. Staff uploads are marked **official**; student uploads are **unofficial**. Filter by course, type and tag, or search by title. |
| **Calendar** | One calendar that merges campus events (posted by staff) with your own weekly classes. Month and week views, with layers you can toggle. |
| **Boards** | A discussion board per course: threads, replies and file attachments. |

### Stretch goals (only if the core is done early)

- Pick files straight from Google Drive using Google sign-in
- Export your calendar as an `.ics` file for Google/Outlook
- Email reminders before events
- Upvotes and reporting on posts

## Tech stack

| Layer | Choice |
| --- | --- |
| Web framework | Flask, split into Blueprints |
| Templates and styling | Jinja2 + Pico.css |
| Database | SQLite via Flask-SQLAlchemy |
| Auth | Flask-Login + Werkzeug password hashing |
| Forms | Flask-WTF (validation + CSRF protection) |
| Calendar UI | FullCalendar (JavaScript), fed by a JSON API route |
| Tests | pytest + Flask test client |

## Architecture

```
Browser (Jinja pages + FullCalendar)
        │  HTTP requests
        ▼
┌──────────────── Flask app ────────────────┐
│  auth/   resources/   calendar/   boards/ │   one Blueprint per feature
└─────────────────────┬─────────────────────┘
          SQLAlchemy  │  saved files
          ┌───────────┴───────────┐
          ▼                       ▼
   SQLite database          uploads/ folder
```

Each feature is its own Blueprint, so it can be built and tested on its own. All Blueprints share one database; Resources and Boards also save files to `uploads/`.

### Data model

| Table | Key fields |
| --- | --- |
| `User` | name, email, password_hash, role |
| `Course` | code, name, term |
| `Enrollment` | user_id, course_id |
| `Resource` | title, kind (file/link), file_path or url, type, tags, is_official, course_id, uploader_id |
| `Event` | title, start, end, location, description, created_by |
| `ClassSlot` | user_id, course_id, weekday, start_time, end_time, room |
| `Thread` | course_id, author_id, title, body |
| `Post` | thread_id, author_id, body, attachment_resource_id |

## Project structure *(planned)*

```
orbit/
  app/
    __init__.py      # create_app(): config, database, login, blueprints
    models.py        # database tables
    auth/            # signup, login, logout, profile
    resources/       # upload, links, browse, search
    calendar/        # events, class slots, /api/events
    boards/          # threads, replies, attachments
    templates/
    static/
  uploads/           # user files (git-ignored)
  tests/             # one test file per blueprint
  seed.py            # demo courses, users and events
  config.py
  requirements.txt
  README.md
```

## Getting started *(planned)*

Requires Python 3.11+.

```bash
git clone <repo-url>
cd orbit
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python seed.py                    # create the database with demo data
flask --app app run --debug       # open http://127.0.0.1:5000
```

Run the tests:

```bash
pytest
```

## Roadmap

| Explorer week | Course week | Goal | Status |
| --- | --- | --- | --- |
| 1 | 5 | Proposal, repo, Flask skeleton, models draft | In progress |
| 2 | 6 | Design doc, all tables, accounts and roles | |
| 3 | 7 | Courses, upload and save links (first prototype) | |
| 4 | 8 | Browse, filter, search, official badge | |
| 5 | 9 | **Midpoint checkpoint.** Calendar: events + classes | |
| 6 | 10 | Boards. **Feature freeze** | |
| 7 | 11 | Testing, error handling, upload limits | |
| 8 | 12 | Bug fixes, cleanup, polish | |
| 9 | 13 | Documentation | |
| 10 | 14 | Demo prep and buffer | |
| — | 15 | Final presentation | |

## Design decisions

- **Drive links instead of the Drive API.** Saving a share link covers "keep your documents in one place" without Google sign-in setup, which could take weeks. Full Drive integration is a stretch goal.
- **SQLite first.** A single file with zero setup; the models are written with SQLAlchemy so moving to Postgres later is a config change.
- **Blueprint per feature.** Keeps code modular and lets each part be tested and demoed on its own.
- **Uploads are restricted.** Allow-listed file types, 10 MB cap and `secure_filename()`; uploaded files are never executed.

## Author

Ahaan Makhija, Plaksha University. Coding Café (FM102) Explorer Track, 2026.
