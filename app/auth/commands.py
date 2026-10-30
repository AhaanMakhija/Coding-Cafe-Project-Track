"""Terminal commands for managing accounts, run with `flask --app app <command>`.

Only someone with access to the server can run these, which is why promoting
a user to staff lives here and not on a web page.
"""

import click

from app.auth import bp
from app.extensions import db
from app.models import User


@bp.cli.command("make-staff")
@click.argument("email")
def make_staff(email):
    """Give the account with EMAIL the staff role."""
    user = db.session.scalar(db.select(User).filter_by(email=email.strip().lower()))
    if user is None:
        # ClickException prints the message and exits with code 1.
        raise click.ClickException(f"No account found for {email}.")

    if user.is_staff:
        click.echo(f"{user.email} is already staff.")
        return

    user.role = "staff"
    db.session.commit()
    click.echo(f"{user.email} is now staff.")
