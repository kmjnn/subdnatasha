from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.orm import validates


db = SQLAlchemy()

class Group(db.Model):
    __tablename__ = 'groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    student_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    students = db.relationship('User', backref='group', lazy=True)
    courses = db.relationship('Course', backref='group', lazy=True)

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # Увеличьте длину для хеша
    role = db.Column(db.String(20), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date)
    contacts = db.Column(db.String(50))
    specialization = db.Column(db.String(30))
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    taught_courses = db.relationship('Course', backref='teacher', lazy=True)
    grades = db.relationship('Grade', backref='student', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(
            password,
            method='pbkdf2:sha256',
            salt_length=16
        )
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    @property
    def is_active(self):
        return True  # Можно добавить логику, например, проверку на бан

    @property
    def is_authenticated(self):
        return True  # True, если пользователь вошел в систему

    @property
    def is_anonymous(self):
        return False  # False для реальных пользователей

    def get_id(self):
        return str(self.id)  # Flask-Login ожидает строку
    

@validates('role')
def validate_role(self, key, role):
    assert role in ['admin', 'teacher', 'student']
    return role


class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    discipline = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    schedules = db.relationship('Schedule', backref='course', lazy=True)
    grades = db.relationship('Grade', backref='course', lazy=True)

class Schedule(db.Model):
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @validates('end_time')
    def validate_end_time(self, key, end_time):
        assert end_time > self.start_time
        return end_time

class Grade(db.Model):
    __tablename__ = 'grades'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    grade = db.Column(db.String(15), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date())
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Обновляем счетчик студентов в группе при изменении
@event.listens_for(User.group_id, 'set')
def update_student_count(target, value, oldvalue, initiator):
    if oldvalue:
        old_group = Group.query.get(oldvalue)
        if old_group:
            old_group.student_count = User.query.filter_by(group_id=oldvalue).count()
            db.session.add(old_group)
    
    if value:
        new_group = Group.query.get(value)
        if new_group:
            new_group.student_count = User.query.filter_by(group_id=value).count()
            db.session.add(new_group)