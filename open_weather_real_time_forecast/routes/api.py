from flask import Blueprint, jsonify

from .. import app

api_bp = Blueprint('api_bp', __name__)

@api_bp.route('/fetch')
def index():
  return jsonify({ 'status': 'ok' })