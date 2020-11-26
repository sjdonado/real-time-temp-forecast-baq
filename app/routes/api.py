from flask import Blueprint, jsonify

from .. import app
from ..services.get_real_time_obs import run

api_bp = Blueprint('api_bp', __name__)

@api_bp.route('/fetch')
def index():
  task_in_process = run()
  
  return jsonify({ 'status': 'sent' if task_in_process == False else 'already in process' })