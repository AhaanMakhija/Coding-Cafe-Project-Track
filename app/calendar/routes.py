"""Routes for the calendar. All URLs here start with /calendar."""

from datetime import datetime

from flask import Response, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from werkzeug.utils import secure_filename
from wtforms import SelectChoice

from app.calendar import bp
from app.calendar.feeds import event_to_fc, parse_fc_datetime, slot_to_fc
from app.calendar.forms import CAMPUS, ClassSlotForm, EventForm
from app.calendar.ics import course_calendar
from app.extensions import db
from app.models import ClassSlot, Course, Event
from app.permissions import can_add_event, can_manage_event


def my_events():
    """Events this user sees: campus-wide ones plus those of the courses they joined."""
    course_ids = [c.id for c in current_user.courses]
    return db.select(Event).where(or_(Event.course_id.is_(None), Event.course_id.in_(course_ids)))


def in_range(query):
    """Limit an events query to the range FullCalendar is showing (?start=&end=).

    An event overlaps the range if it starts before the range ends and ends
    after the range starts.
    """
    try:
        start = parse_fc_datetime(request.args.get("start"))
        end = parse_fc_datetime(request.args.get("end"))
    except ValueError:
        abort(400, "start and end must be ISO dates")
    if end:
        query = query.where(Event.start_at < end)
    if start:
        query = query.where(Event.end_at > start)
    return query


def calendar_choices(event=None):
    """The calendars this user may post to, for the form's dropdown."""
    courses = (db.session.scalars(db.select(Course).order_by(Course.code)).all()
               if current_user.is_staff else sorted(current_user.courses, key=lambda c: c.code))
    if event and event.course and event.course not in courses:
        courses.append(event.course)  # keep an event's own course when editing it
    choices = [SelectChoice(c.id, f"{c.code} · {c.name}") for c in courses]
    if current_user.is_staff:
        choices.insert(0, SelectChoice(CAMPUS, "Campus-wide (everyone)"))
    return choices


def fill_event(event, form):
    """Copy the form's values onto an Event."""
    event.title = form.title.data
    event.course_id = form.course_id.data or None  # CAMPUS (0) is stored as no course
    event.start_at = form.start_at
    event.end_at = form.end_at
    event.location = form.location.data or ""
    event.description = form.description.data or ""


@bp.route("/")
@login_required
def calendar_page():
    slots = sorted(current_user.class_slots, key=lambda s: (s.weekday, s.start_time))
    # Events are stored as local wall-clock times, so compare with local "now".
    upcoming = db.session.scalars(
        my_events().where(Event.end_at >= datetime.now()).order_by(Event.start_at).limit(8)
    ).all()
    return render_template("calendar/calendar.html", slots=slots, events=upcoming,
                           can_add_events=bool(calendar_choices()))


# --- JSON feeds for FullCalendar --------------------------------------------------

@bp.route("/api/events")
@login_required
def events_feed():
    """Campus-wide events in the visible range."""
    events = db.session.scalars(in_range(db.select(Event).where(Event.course_id.is_(None)))
                                .order_by(Event.start_at)).all()
    return jsonify([event_to_fc(e) for e in events])


@bp.route("/api/course-events")
@login_required
def course_events_feed():
    """Events of the courses the user joined, in the visible range."""
    course_ids = [c.id for c in current_user.courses]
    events = db.session.scalars(in_range(db.select(Event).where(Event.course_id.in_(course_ids)))
                                .order_by(Event.start_at)).all()
    return jsonify([event_to_fc(e) for e in events])


@bp.route("/api/classes")
@login_required
def classes_feed():
    """The logged-in user's own weekly classes. FullCalendar repeats them itself."""
    return jsonify([slot_to_fc(s) for s in current_user.class_slots])


# --- Events -----------------------------------------------------------------------

@bp.route("/events/<int:event_id>")
@login_required
def event_detail(event_id):
    event = db.get_or_404(Event, event_id)
    return render_template("calendar/event_detail.html", event=event,
                           can_manage=can_manage_event(current_user, event))


@bp.route("/events/new", methods=["GET", "POST"])
@login_required
def new_event():
    choices = calendar_choices()
    if not choices:
        flash("Join a course first, then you can add events to its calendar.", "warning")
        return redirect(url_for("resources.course_list"))

    form = EventForm()
    form.course_id.choices = choices
    # /events/new?course_id=3 (from a course page) preselects that course.
    if request.method == "GET" and request.args.get("course_id", type=int):
        form.course_id.data = request.args.get("course_id", type=int)

    if form.validate_on_submit():
        course = db.session.get(Course, form.course_id.data) if form.course_id.data else None
        if not can_add_event(current_user, course):
            abort(403)
        event = Event(creator=current_user)
        fill_event(event, form)
        db.session.add(event)
        db.session.commit()
        flash(f"Added “{event.title}” to the {event.course.code if event.course else 'campus'} calendar.",
              "success")
        return redirect(url_for("calendar.event_detail", event_id=event.id))
    return render_template("calendar/event_form.html", form=form, event=None)


@bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    event = db.get_or_404(Event, event_id)
    if not can_manage_event(current_user, event):
        abort(403)

    # data= fills the form from the event on GET; on POST the submitted values take over.
    form = EventForm(event_id=event.id, data={
        "title": event.title, "course_id": event.course_id or CAMPUS,
        "day": event.start_at.date(), "start_time": event.start_at.time(),
        "end_time": event.end_at.time(), "location": event.location,
        "description": event.description,
    })
    form.course_id.choices = calendar_choices(event)
    if form.validate_on_submit():
        course = db.session.get(Course, form.course_id.data) if form.course_id.data else None
        if course != event.course and not can_add_event(current_user, course):
            abort(403)
        fill_event(event, form)
        db.session.commit()
        flash(f"Saved “{event.title}”.", "success")
        return redirect(url_for("calendar.event_detail", event_id=event.id))
    return render_template("calendar/event_form.html", form=form, event=event)


@bp.route("/events/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_event(event_id):
    event = db.get_or_404(Event, event_id)
    if not can_manage_event(current_user, event):
        abort(403)
    course_id = event.course_id
    db.session.delete(event)
    db.session.commit()
    flash(f"Deleted “{event.title}”.", "info")
    if course_id:
        return redirect(url_for("resources.course_detail", course_id=course_id))
    return redirect(url_for("calendar.calendar_page"))


@bp.route("/courses/<int:course_id>.ics")
@login_required
def course_ics(course_id):
    """Download a course's calendar for Google Calendar, Outlook or Apple Calendar."""
    course = db.get_or_404(Course, course_id)
    my_slots = [s for s in current_user.class_slots if s.course_id == course.id]
    filename = secure_filename(f"{course.code}-{course.term}.ics".replace(" ", "-"))  # CS101-Fall-2026.ics
    return Response(
        course_calendar(course, course.events, my_slots),
        mimetype="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- Your weekly classes --------------------------------------------------------

@bp.route("/classes/new", methods=["GET", "POST"])
@login_required
def new_class():
    if not current_user.courses:
        flash("Join a course first, then add its class times.", "warning")
        return redirect(url_for("resources.course_list"))

    form = ClassSlotForm()
    # Only courses you've joined. WTForms rejects any other course_id as
    # "Not a valid choice", so nobody can add classes to someone else's course list.
    form.course_id.choices = [SelectChoice(c.id, f"{c.code} · {c.name}") for c in current_user.courses]

    if form.validate_on_submit():
        slot = ClassSlot(
            user=current_user, course_id=form.course_id.data, weekday=form.weekday.data,
            start_time=form.start_time.data, end_time=form.end_time.data,
            room=form.room.data or "",
        )
        db.session.add(slot)
        db.session.commit()
        flash(f"Added {slot.course.code} on {slot.weekday_name}s.", "success")
        return redirect(url_for("calendar.calendar_page"))
    return render_template("calendar/class_form.html", form=form)


@bp.route("/classes/<int:slot_id>/delete", methods=["POST"])
@login_required
def delete_class(slot_id):
    slot = db.get_or_404(ClassSlot, slot_id)
    if slot.user_id != current_user.id:
        abort(403)
    db.session.delete(slot)
    db.session.commit()
    flash("Removed that class from your timetable.", "info")
    return redirect(url_for("calendar.calendar_page"))
