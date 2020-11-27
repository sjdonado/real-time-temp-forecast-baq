from datetime import datetime

from dataclasses import dataclass
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

@dataclass
class Report(db.Model):
    id: int
    prediction: float
    active: bool
    created: str
    updated: str

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(128), nullable=True)
    prediction = db.Column(db.Float, nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)