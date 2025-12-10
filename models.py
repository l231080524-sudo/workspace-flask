from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)               
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    user_type = db.Column(db.String(20))  
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def id(self):
        return self.user_id

    employee = db.relationship("Employee", backref="user", uselist=False, cascade="all, delete")
    boss = db.relationship("Boss", backref="user", uselist=False, cascade="all, delete")

class Employee(db.Model):
    __tablename__ = "employees"
    employee_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    skills = db.Column(db.Text)
    experience = db.Column(db.Text)
    resume = db.Column(db.Text)

    applications = db.relationship("Application", backref="employee", cascade="all, delete")

class Boss(db.Model):
    __tablename__ = "bosses"
    boss_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))

    job_offers = db.relationship("JobOffer", backref="boss", cascade="all, delete")

class JobOffer(db.Model):
    __tablename__ = "job_offers"
    offer_id = db.Column(db.Integer, primary_key=True)
    boss_id = db.Column(db.Integer, db.ForeignKey("bosses.boss_id", ondelete="SET NULL"))
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    salary = db.Column(db.Numeric(10,2))
    location = db.Column(db.String(100))
    publish_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="open")  

    applications = db.relationship("Application", backref="job_offer", cascade="all, delete")

class Application(db.Model):
    __tablename__ = "applications"
    application_id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    offer_id = db.Column(db.Integer, db.ForeignKey("job_offers.offer_id", ondelete="CASCADE"), nullable=False)
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="pending")  

    __table_args__ = (db.UniqueConstraint('employee_id', 'offer_id', name='uix_employee_offer'), )
