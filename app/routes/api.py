from flask import Blueprint, jsonify, redirect

from .. import app
from ..services.get_real_time_obs import run

api_bp = Blueprint('api_bp', __name__)

@api_bp.route('/fetch')
def fetch():
  status = run()
  return jsonify({ 'status': 'sent' if status else 'already in process' })


@api_bp.route('/')
def index():
  return redirect('/dashboard', code=302)