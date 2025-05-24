from flask import Blueprint

visualization_bp = Blueprint('visualization', __name__)

from .dashboard import *  # Import routes from dashboard.py