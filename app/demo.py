"""`flask seed-demo`: fill the database with realistic sample data for a demo.

Dates are worked out from today, so events are always "this week" and posts are
"2 hours ago" whenever the demo runs. Everyone shares one demo password, which
is printed in the terminal and never stored in the code.
"""

import os
import secrets
import uuid
from datetime import date, datetime, time, timedelta, timezone

import click
from flask import current_app

from app.extensions import db
from app.models import ClassSlot, Course, Event, Post, Resource, Thread, User

DEMO_DOMAIN = "orbit-demo.edu"

USERS = [
    # (key, name, role)
    ("riya", "Riya Kapoor", "student"),  # the account to demo with
    ("kabir", "Kabir Singh", "student"),
    ("ananya", "Ananya Iyer", "student"),
    ("meera", "Prof. Meera Rao", "staff"),
    ("arjun", "Dr. Arjun Sethi", "staff"),
]

COURSES = [
    # (code, name, students who join)
    ("CS101", "Introduction to Programming", ["riya", "kabir", "ananya"]),
    ("MA102", "Calculus II", ["riya", "ananya"]),
    ("PH103", "Physics: Mechanics", ["riya", "kabir"]),
    ("DT104", "Design Thinking", ["kabir", "ananya"]),
]

# (course, title, type, tags, uploader, file name or URL, days ago)
RESOURCES = [
    ("CS101", "Week 1 lecture: variables and types", "slides", "week 1, basics", "meera", "lecture1.pdf", 40),
    ("CS101", "Loops cheat sheet", "notes", "week 3, loops", "kabir", "loops.pdf", 20),
    ("CS101", "Lab 2 handout", "assignment", "lab, week 2", "meera", "lab2.pdf", 30),
    ("CS101", "2025 midterm with solutions", "past paper", "midterm", "meera",
     "https://drive.google.com/drive/folders/orbit-demo-cs101-midterm", 12),
    ("CS101", "Python Tutor: see your code run", "other", "tools, debugging", "ananya",
     "https://pythontutor.com/", 8),
    ("CS101", "Recursion explained (video)", "other", "week 6, recursion", "riya",
     "https://www.youtube.com/watch?v=orbit-demo", 3),
    ("MA102", "Integration by parts: worked examples", "notes", "week 4, integration", "arjun", "integration.pdf", 18),
    ("MA102", "Problem set 3", "assignment", "week 5", "arjun",
     "https://docs.google.com/document/d/orbit-demo-ps3", 6),
    ("MA102", "Series convergence summary", "notes", "series, midterm", "ananya", "series.pdf", 2),
    ("PH103", "Newton's laws slides", "slides", "week 2, forces", "arjun",
     "https://onedrive.live.com/orbit-demo-newton", 25),
    ("PH103", "Lab report template", "other", "lab", "kabir", "lab_template.pdf", 9),
]

# (title, day offset from today, start hour, hours long, location, description)
EVENTS = [
    ("Hackathon kickoff", 1, 17, 2, "Main auditorium",
     "Form teams of up to four.\nPizza from 18:30."),
    ("Guest talk: building for India's next billion users", 3, 15, 1, "Lecture hall 2",
     "Open to all years. Questions at the end."),
    ("Midterm review: CS101", 5, 11, 2, "Room 204", "Bring your questions on loops and functions."),
    ("Career fair", 9, 10, 6, "Sports complex", "Bring printed CVs."),
    ("Founders' Day", 14, 9, 8, "Campus lawn", ""),
]

# Riya's weekly timetable: (course, weekday 0 = Monday, start, end, room)
RIYA_CLASSES = [
    ("CS101", 0, time(10), time(11, 30), "204"),
    ("CS101", 3, time(10), time(11, 30), "204"),
    ("MA102", 1, time(9), time(10, 30), "112"),
    ("MA102", 4, time(9), time(10, 30), "112"),
    ("PH103", 2, time(14), time(15, 30), "Lab 3"),
]

# (course, title, body, author, hours ago, replies: [(body, author, hours ago, attached file or None)])
THREADS = [
    ("CS101", "Lab 2, question 3: why does my loop never end?",
     "My while loop keeps running forever.\nI think the counter never changes, but I'm not sure where.", "kabir", 30,
     [("You never update i inside the loop. Add i += 1 as the last line of the loop body.", "ananya", 28, None),
      ("Ananya is right. Here's a worked version with comments.", "meera", 20, "lab2_solution.pdf"),
      ("That fixed it, thank you!", "kabir", 19, None)]),
    ("CS101", "Is the midterm open book?", "Can we bring printed notes?", "riya", 5,
     [("One A4 sheet of handwritten notes, both sides.", "meera", 2, None)]),
    ("MA102", "Study group for integration?",
     "Anyone free on Thursday evening in the library to go through problem set 3?", "ananya", 50, []),
    ("PH103", "Lab 3 rescheduled?", "Is lab 3 still on Wednesday?", "riya", 1, []),
]


def demo_pdf(title):
    """A tiny one-page PDF showing title, so demo downloads open a real file.

    A PDF is a list of numbered objects plus a table (xref) giving each object's
    byte offset, which is why the offsets are counted while building it.
    """
    safe = title.replace("\\", "").replace("(", "").replace(")", "")
    stream = f"BT /F1 20 Tf 72 720 Td ({safe}) Tj 0 -30 Td /F1 12 Tf (ORBIT demo file) Tj ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return out


def save_demo_file(title):
    """Write a demo PDF into the uploads folder under a random name, like a real upload."""
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.pdf"
    with open(os.path.join(folder, stored_name), "wb") as f:
        f.write(demo_pdf(title))
    return stored_name


def make_resource(course, title, rtype, tags, uploader, source, created_at):
    resource = Resource(title=title, type=rtype, tags=tags, course=course, uploader=uploader,
                        is_official=uploader.is_staff, created_at=created_at)
    if source.startswith("http"):
        resource.kind, resource.url = "link", source
    else:
        resource.kind, resource.file_path = "file", save_demo_file(title)
    return resource


def seed(password):
    """Add all the demo data. Returns the users by key."""
    now = datetime.now(timezone.utc)
    users = {}
    for key, name, role in USERS:
        users[key] = User(name=name, email=f"{key}@{DEMO_DOMAIN}", role=role)
        users[key].set_password(password)
    db.session.add_all(users.values())

    courses = {}
    for code, name, members in COURSES:
        courses[code] = Course(code=code, name=name, term="Fall 2026",
                               students=[users[m] for m in members])
    db.session.add_all(courses.values())

    for code, title, rtype, tags, who, source, days in RESOURCES:
        db.session.add(make_resource(courses[code], title, rtype, tags, users[who], source,
                                     now - timedelta(days=days)))

    # Events are local wall-clock times, like the ones staff type into the form.
    today = date.today()
    for title, day, hour, length, location, description in EVENTS:
        start = datetime.combine(today + timedelta(days=day), time(hour))
        db.session.add(Event(title=title, start_at=start, end_at=start + timedelta(hours=length),
                             location=location, description=description, creator=users["meera"]))

    for code, weekday, start, end, room in RIYA_CLASSES:
        db.session.add(ClassSlot(user=users["riya"], course=courses[code], weekday=weekday,
                                 start_time=start, end_time=end, room=room))

    for code, title, body, who, hours, replies in THREADS:
        thread = Thread(title=title, body=body, course=courses[code], author=users[who],
                        created_at=now - timedelta(hours=hours))
        for reply_body, reply_who, reply_hours, attached in replies:
            post = Post(body=reply_body, thread=thread, author=users[reply_who],
                        created_at=now - timedelta(hours=reply_hours))
            if attached:
                # Same shape as a real board attachment: a library resource tagged "board".
                post.attachment = make_resource(courses[code], attached.removesuffix(".pdf"), "other",
                                                "board", users[reply_who], attached, post.created_at)
            thread.posts.append(post)
        db.session.add(thread)

    db.session.commit()
    return users


@click.command("seed-demo")
@click.option("--reset", is_flag=True, help="Delete ALL existing data first.")
@click.option("--password", help="Password for every demo account (default: a random one).")
def seed_demo_command(reset, password):
    """Fill the database with demo courses, files, events, classes and threads."""
    if reset:
        click.confirm("This deletes every account, course and post in the database. Continue?", abort=True)
        db.drop_all()
        db.create_all()
    elif db.session.scalar(db.select(User).limit(1)):
        raise click.ClickException("The database already has data. Run with --reset to replace it.")

    password = password or secrets.token_urlsafe(9)
    if len(password) < 8:
        raise click.ClickException("The password must be at least 8 characters.")

    users = seed(password)
    click.echo("Demo data added. Log in with any of these accounts:")
    for key, user in users.items():
        click.echo(f"  {user.email:<28} {user.role}")
    click.echo(f"Password for all of them: {password}")


def register(app):
    app.cli.add_command(seed_demo_command)
