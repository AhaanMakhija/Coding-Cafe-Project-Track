"""Flask extension objects, created once and shared across the app.

They live in their own module (not in __init__.py) so that models.py and the
Blueprints can import them without a circular import back into create_app().
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()

login_manager = LoginManager()
# Where @login_required sends visitors who are not signed in.
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"
