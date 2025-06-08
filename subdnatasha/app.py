# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone  # Изменение здесь
import os

import logging
logging.basicConfig(level=logging.DEBUG)

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, template_folder=os.path.join(basedir, 'templates'))
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:0000@localhost/education_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модели
class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    student_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date)
    contacts = db.Column(db.String(50))
    specialization = db.Column(db.String(30))
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    group = db.relationship('Group', backref='users')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    discipline = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100))
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    group = db.relationship('Group', backref='courses')
    teacher = db.relationship('User', backref='taught_courses')

class Schedule(db.Model):
    __tablename__ = 'schedules'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    start_time = db.Column(db.TIMESTAMP, nullable=False)
    end_time = db.Column(db.TIMESTAMP, nullable=False)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    course = db.relationship('Course', backref='schedules')

class Grade(db.Model):
    __tablename__ = 'grades'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    grade = db.Column(db.String(15), nullable=False)
    date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())  
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    student = db.relationship('User', foreign_keys=[student_id], backref='grades')
    course = db.relationship('Course', backref='grades')

# Маршруты
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif user.role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Вы успешно вошли в систему', 'success')
            return redirect(url_for('home'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('login.html')

# ... (остальной код остается без изменений)
@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

# Админ панель
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    users = User.query.all()
    groups = Group.query.all()
    courses = Course.query.all()
    return render_template('admin_dashboard.html', users=users, groups=groups, courses=courses)

@app.route('/admin/add_user', methods=['GET', 'POST'])
def add_user():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        full_name = request.form['full_name']
        group_id = request.form.get('group_id')
        
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'danger')
            return redirect(url_for('add_user'))
        
        user = User(
            username=username,
            email=email,
            role=role,
            full_name=full_name,
            group_id=group_id if group_id else None
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        flash('Пользователь успешно добавлен', 'success')
        return redirect(url_for('admin_dashboard'))
    
    groups = Group.query.all()
    return render_template('add_user.html', groups=groups)

# Преподаватель панель
@app.route('/teacher/dashboard')
def teacher_dashboard():
    try:
        if 'user_id' not in session or session.get('role') != 'teacher':
            return redirect(url_for('login'))
        
        teacher_id = session['user_id']
        courses = Course.query.filter_by(teacher_id=teacher_id).all()
        return render_template('teacher_dashboard.html', courses=courses)
    except Exception as e:
        print(f"Error rendering template: {str(e)}")
        return str(e), 500
    
# Маршруты для управления курсами преподавателя
@app.route('/teacher/courses')
def teacher_courses():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    teacher_id = session['user_id']
    courses = Course.query.filter_by(teacher_id=teacher_id).all()
    groups = Group.query.all()  # Для формы добавления курса
    return render_template('teacher_courses.html', courses=courses, groups=groups)

@app.route('/teacher/add_course', methods=['GET', 'POST'])
def add_course():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        discipline = request.form['discipline']
        group_id = request.form['group_id']
        location = request.form.get('location', '')
        
        course = Course(
            discipline=discipline,
            group_id=group_id,
            teacher_id=session['user_id'],
            location=location
        )
        
        db.session.add(course)
        db.session.commit()
        flash('Курс успешно добавлен', 'success')
        return redirect(url_for('teacher_courses'))
    
    groups = Group.query.all()
    return render_template('add_course.html', groups=groups)

@app.route('/teacher/edit_course/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    course = Course.query.get_or_404(course_id)
    
    # Проверяем, что курс принадлежит текущему преподавателю
    if course.teacher_id != session['user_id']:
        flash('У вас нет прав для редактирования этого курса', 'danger')
        return redirect(url_for('teacher_courses'))
    
    if request.method == 'POST':
        course.discipline = request.form['discipline']
        course.group_id = request.form['group_id']
        course.location = request.form.get('location', '')
        db.session.commit()
        flash('Курс успешно обновлен', 'success')
        return redirect(url_for('teacher_courses'))
    
    groups = Group.query.all()
    return render_template('edit_course.html', course=course, groups=groups)

@app.route('/teacher/delete_course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    course = Course.query.get_or_404(course_id)
    
    if course.teacher_id != session['user_id']:
        flash('У вас нет прав для удаления этого курса', 'danger')
        return redirect(url_for('teacher_courses'))
    
    # Удаляем связанные записи (расписание и оценки)
    Schedule.query.filter_by(course_id=course_id).delete()
    Grade.query.filter_by(course_id=course_id).delete()
    
    db.session.delete(course)
    db.session.commit()
    flash('Курс успешно удален', 'success')
    return redirect(url_for('teacher_courses'))

@app.route('/teacher/add_grade', methods=['POST'])
def add_grade():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    
    student_id = request.form['student_id']
    course_id = request.form['course_id']
    grade_value = request.form['grade']
    
    course = Course.query.get(course_id)
    if not course or course.teacher_id != session['user_id']:
        flash('Недопустимый курс', 'danger')
        return redirect(url_for('teacher_dashboard'))
    
    grade = Grade(
        student_id=student_id,
        course_id=course_id,
        grade=grade_value
    )
    
    db.session.add(grade)
    db.session.commit()
    flash('Оценка добавлена', 'success')
    return redirect(url_for('teacher_course', course_id=course_id))

# Студент панель
@app.route('/student/dashboard')
def student_dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    
    student_id = session['user_id']
    student = User.query.get(student_id)
    courses = Course.query.filter_by(group_id=student.group_id).all()
    grades = Grade.query.filter_by(student_id=student_id).all()
    
    return render_template('student_dashboard.html', student=student, courses=courses, grades=grades)

# ... (предыдущий код остается без изменений до маршрутов)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        role = 'student'  # По умолчанию регистрируем как студента
        
        # Проверка на существующего пользователя
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email уже используется', 'danger')
            return redirect(url_for('register'))
        
        # Создание пользователя
        user = User(
            username=username,
            email=email,
            role=role,
            full_name=full_name
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')




if __name__ == '__main__':
    app.run(debug=True)