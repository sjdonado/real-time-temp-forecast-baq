from datetime import datetime

from dataclasses import dataclass
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

@dataclass
class Report(db.Model):
    id: int
    forecast: float
    active: bool
    path: str
    url: str
    created: str
    updated: str

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(512), nullable=True)
    url = db.Column(db.String(512), nullable=True)
    forecast = db.Column(db.Float, nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


@dataclass
class ModelData(db.Model):
    id: int
    path: str
    url: str
    created: str
    updated: str

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(512), nullable=True)
    url = db.Column(db.String(512), nullable=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)