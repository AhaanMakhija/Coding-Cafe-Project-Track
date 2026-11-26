"""Tests for the `flask seed-demo` command in app/demo.py."""

import os
from datetime import datetime

from app.demo import demo_pdf
from app.extensions import db
from app.models import ClassSlot, Course, Event, Post, Resource, Thread, User

DEMO_PASSWORD = "demo-pass-123"


def run_seed(app, *args):
    return app.test_cli_runner().invoke(args=["seed-demo", *args])


def test_seed_fills_every_table(app):
    result = run_seed(app, "--password", DEMO_PASSWORD)
    assert result.exit_code == 0, result.output

    def count(model):
        return len(db.session.scalars(db.select(model)).all())

    assert count(User) == 5
    assert count(Course) == 4
    assert count(Event) == 15  # 4 campus-wide + 11 course events
    assert count(ClassSlot) == 5
    assert count(Thread) == 4
    assert count(Post) == 4
    assert count(Resource) == 12  # 11 library resources + 1 board attachment
    assert "riya@orbit-demo.edu" in result.output
    assert DEMO_PASSWORD in result.output


def test_demo_files_exist_and_are_pdfs(app):
    run_seed(app, "--password", DEMO_PASSWORD)
    files = db.session.scalars(db.select(Resource).filter_by(kind="file")).all()
    assert files
    for resource in files:
        path = os.path.join(app.config["UPLOAD_FOLDER"], resource.file_path)
        with open(path, "rb") as f:
            assert f.read(5) == b"%PDF-"


def test_demo_events_are_in_the_future(app):
    run_seed(app, "--password", DEMO_PASSWORD)
    events = db.session.scalars(db.select(Event)).all()
    assert all(e.start_at > datetime.now() for e in events)


def test_demo_account_can_log_in_and_browse(app, client):
    run_seed(app, "--password", DEMO_PASSWORD)
    response = client.post("/auth/login", data={"email": "riya@orbit-demo.edu", "password": DEMO_PASSWORD})
    assert response.status_code == 302

    home = client.get("/").get_data(as_text=True)
    assert "CS101" in home and "MA102" in home
    assert client.get("/calendar/api/classes").get_json()


def test_board_attachment_matches_real_attachments(app):
    run_seed(app, "--password", DEMO_PASSWORD)
    post = db.session.scalar(db.select(Post).where(Post.attachment_resource_id.is_not(None)))
    assert post.attachment.tag_list == ["board"]
    assert post.attachment.is_official  # posted by staff


def test_seed_refuses_to_mix_with_existing_data(app, make_user):
    make_user()
    result = run_seed(app, "--password", DEMO_PASSWORD)
    assert result.exit_code == 1
    assert "--reset" in result.output
    assert len(db.session.scalars(db.select(User)).all()) == 1


def test_reset_asks_first_and_replaces_data(app, make_user):
    make_user()
    declined = run_seed(app, "--reset", "--password", DEMO_PASSWORD)  # no input -> "no"
    assert declined.exit_code == 1
    assert db.session.scalar(db.select(User)).email == "student@plaksha.edu.in"

    accepted = app.test_cli_runner().invoke(args=["seed-demo", "--reset", "--password", DEMO_PASSWORD],
                                            input="y\n")
    assert accepted.exit_code == 0, accepted.output
    emails = db.session.scalars(db.select(User.email)).all()
    assert "student@plaksha.edu.in" not in emails and len(emails) == 5


def test_short_password_is_rejected(app):
    result = run_seed(app, "--password", "short")
    assert result.exit_code == 1
    assert db.session.scalar(db.select(User)) is None


def test_random_password_when_none_given(app, client):
    result = run_seed(app)
    password = result.output.strip().rsplit(" ", 1)[-1]
    assert len(password) >= 8
    log_in_response = client.post("/auth/login", data={"email": "meera@orbit-demo.edu", "password": password})
    assert log_in_response.status_code == 302


def test_demo_pdf_is_well_formed():
    pdf = demo_pdf("Week 1 (intro)")
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    # The xref table must point at the real position of object 1.
    xref = pdf[pdf.index(b"xref"):]
    first_offset = int(xref.split(b"\n")[3][:10])
    assert pdf[first_offset:].startswith(b"1 0 obj")
