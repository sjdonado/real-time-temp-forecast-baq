from flask import Blueprint, jsonify

from .. import app
from ..services.get_real_time_obs import run

api_bp = Blueprint('api_bp', __name__)

@api_bp.route('/fetch')
def index():
  sent = run()
  
  return jsonify({ 'status': 'sent' if sent else 'already in process' })