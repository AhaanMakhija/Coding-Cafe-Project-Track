"""Flask extension objects, created once and shared across the app.

They live in their own module (not in __init__.py) so that models.py and the
Blueprints can import them without a circular import back into create_app().
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
