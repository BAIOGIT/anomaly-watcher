from flask import Blueprint

visualization_bp = Blueprint('visualization', __name__)

from .routes import dashboard  # Import routes to register them with the blueprint

