from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120))
    role = db.Column(db.String(20), default="member")
    allergies = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 统一用 back_populates，避免 backref 重复
    medications   = db.relationship("Medication", back_populates="user", cascade="all, delete-orphan")
    reminders     = db.relationship("Reminder",  back_populates="user", cascade="all, delete-orphan")
    health_records= db.relationship("HealthRecord", back_populates="user", cascade="all, delete-orphan")

class Medication(db.Model):
    __tablename__ = "medication"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    dose = db.Column(db.String(50))
    times = db.Column(db.String(200), nullable=False)  # 例如 "08:00,12:00,20:00"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="medications")
    reminders = db.relationship("Reminder", back_populates="medication", cascade="all, delete-orphan")

class Reminder(db.Model):
    __tablename__ = "reminder"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    medication_id = db.Column(db.Integer, db.ForeignKey("medication.id"), nullable=False)
    remind_time = db.Column(db.DateTime, nullable=False, index=True)
    sent = db.Column(db.Boolean, default=False)
    confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="reminders")
    medication = db.relationship("Medication", back_populates="reminders")

class HealthRecord(db.Model):
    __tablename__ = "health_record"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    record_time = db.Column(db.DateTime, default=datetime.utcnow)
    kind = db.Column(db.String(50))
    value = db.Column(db.String(50))
    note = db.Column(db.String(255))

    user = db.relationship("User", back_populates="health_records")
