"""Routes for the calendar. All URLs here start with /calendar."""

from datetime import datetime

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from wtforms import SelectChoice

from app.auth.decorators import staff_required
from app.calendar import bp
from app.calendar.feeds import event_to_fc, parse_fc_datetime, slot_to_fc
from app.calendar.forms import ClassSlotForm, EventForm
from app.extensions import db
from app.models import ClassSlot, Event


def fill_event(event, form):
    """Copy the form's values onto an Event."""
    event.title = form.title.data
    event.start_at = form.start_at.data
    event.end_at = form.end_at.data
    event.location = form.location.data or ""
    event.description = form.description.data or ""


@bp.route("/")
@login_required
def calendar_page():
    slots = sorted(current_user.class_slots, key=lambda s: (s.weekday, s.start_time))
    # Events are stored as local wall-clock times, so compare with local "now".
    upcoming = db.session.scalars(
        db.select(Event).where(Event.end_at >= datetime.now()).order_by(Event.start_at).limit(8)
    ).all()
    return render_template("calendar/calendar.html", slots=slots, events=upcoming)


# --- JSON feeds for FullCalendar --------------------------------------------------

@bp.route("/api/events")
@login_required
def events_feed():
    """Campus events overlapping the range FullCalendar is showing (?start=&end=)."""
    try:
        start = parse_fc_datetime(request.args.get("start"))
        end = parse_fc_datetime(request.args.get("end"))
    except ValueError:
        abort(400, "start and end must be ISO dates")

    query = db.select(Event)
    # An event overlaps the visible range if it starts before the range ends
    # and ends after the range starts.
    if end:
        query = query.where(Event.start_at < end)
    if start:
        query = query.where(Event.end_at > start)
    events = db.session.scalars(query.order_by(Event.start_at)).all()
    return jsonify([event_to_fc(e) for e in events])


@bp.route("/api/classes")
@login_required
def classes_feed():
    """The logged-in user's own weekly classes. FullCalendar repeats them itself."""
    return jsonify([slot_to_fc(s) for s in current_user.class_slots])


# --- Campus events (staff only, except viewing) ------------------------------------

@bp.route("/events/<int:event_id>")
@login_required
def event_detail(event_id):
    event = db.get_or_404(Event, event_id)
    return render_template("calendar/event_detail.html", event=event)


@bp.route("/events/new", methods=["GET", "POST"])
@staff_required
def new_event():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(creator=current_user)
        fill_event(event, form)
        db.session.add(event)
        db.session.commit()
        flash(f"Posted “{event.title}”.", "success")
        return redirect(url_for("calendar.event_detail", event_id=event.id))
    return render_template("calendar/event_form.html", form=form, event=None)


@bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@staff_required
def edit_event(event_id):
    event = db.get_or_404(Event, event_id)
    form = EventForm(obj=event)  # obj= fills the form from the event on GET
    if form.validate_on_submit():
        fill_event(event, form)
        db.session.commit()
        flash(f"Saved “{event.title}”.", "success")
        return redirect(url_for("calendar.event_detail", event_id=event.id))
    return render_template("calendar/event_form.html", form=form, event=event)


@bp.route("/events/<int:event_id>/delete", methods=["POST"])
@staff_required
def delete_event(event_id):
    event = db.get_or_404(Event, event_id)
    db.session.delete(event)
    db.session.commit()
    flash(f"Deleted “{event.title}”.", "info")
    return redirect(url_for("calendar.calendar_page"))


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
