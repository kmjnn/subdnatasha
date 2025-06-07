from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, DateField, DateTimeField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from datetime import datetime, date
from models import Course, User, Group

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message="Email обязателен"),
        Email(message="Некорректный email")
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message="Пароль обязателен")
    ])
    submit = SubmitField('Войти')
    
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
                                   validators=[DataRequired(), EqualTo('password')])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    role = SelectField('Role', choices=[
        ('student', 'Student'), 
        ('teacher', 'Teacher')])
    birth_date = DateField('Birth Date', format='%Y-%m-%d')
    contacts = StringField('Contacts', validators=[Length(max=50)])
    specialization = StringField('Specialization', validators=[Length(max=30)])
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')

class GroupForm(FlaskForm):
    name = StringField('Group Name', validators=[DataRequired(), Length(max=30)])

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    role = SelectField('Role', choices=[
        ('admin', 'Admin'), 
        ('teacher', 'Teacher'), 
        ('student', 'Student')])
    birth_date = DateField('Birth Date', format='%Y-%m-%d')
    contacts = StringField('Contacts', validators=[Length(max=50)])
    specialization = StringField('Specialization', validators=[Length(max=30)])
    group_id = SelectField('Group', coerce=int)
    
    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.group_id.choices = [(g.id, g.name) for g in Group.query.order_by(Group.name).all()]
        self.group_id.choices.insert(0, (0, 'No Group'))

class CourseForm(FlaskForm):
    discipline = StringField('Discipline', validators=[DataRequired(), Length(max=50)])
    group_id = SelectField('Group', coerce=int, validators=[DataRequired()])
    teacher_id = SelectField('Teacher', coerce=int, validators=[DataRequired()])
    location = StringField('Location', validators=[Length(max=100)])
    
    def __init__(self, *args, **kwargs):
        super(CourseForm, self).__init__(*args, **kwargs)
        self.group_id.choices = [(g.id, g.name) for g in Group.query.order_by(Group.name).all()]
        self.teacher_id.choices = [(t.id, t.full_name) 
                                 for t in User.query.filter_by(role='teacher').order_by(User.full_name).all()]

class ScheduleForm(FlaskForm):
    course_id = SelectField('Course', coerce=int, validators=[DataRequired()])
    start_time = DateTimeField('Start Time', format='%Y-%m-%d %H:%M', 
                             validators=[DataRequired()])
    end_time = DateTimeField('End Time', format='%Y-%m-%d %H:%M', 
                           validators=[DataRequired()])
    
    def __init__(self, *args, **kwargs):
        super(ScheduleForm, self).__init__(*args, **kwargs)
        self.course_id.choices = [(c.id, f"{c.discipline} ({c.group.name})") 
                                 for c in Course.query.join(Group).order_by(Group.name, Course.discipline).all()]
    
    def validate_end_time(self, field):
        if field.data <= self.start_time.data:
            raise ValidationError('End time must be after start time.')

class GradeForm(FlaskForm):
    student_id = SelectField('Student', coerce=int, validators=[DataRequired()])
    course_id = SelectField('Course', coerce=int, validators=[DataRequired()])
    grade = SelectField('Grade', choices=[
        ('A', 'A (Excellent)'),
        ('B', 'B (Good)'),
        ('C', 'C (Satisfactory)'),
        ('D', 'D (Poor)'),
        ('F', 'F (Fail)'),
        ('Pass', 'Pass'),
        ('Fail', 'Fail')
    ], validators=[DataRequired()])
    date = DateField('Date', default=date.today, format='%Y-%m-%d')
    
    def __init__(self, *args, **kwargs):
        super(GradeForm, self).__init__(*args, **kwargs)
        self.student_id.choices = [(s.id, s.full_name) 
                                 for s in User.query.filter_by(role='student').order_by(User.full_name).all()]
        self.course_id.choices = [(c.id, f"{c.discipline} ({c.group.name})") 
                                 for c in Course.query.join(Group).order_by(Group.name, Course.discipline).all()]