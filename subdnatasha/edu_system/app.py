from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Group, Course, Schedule, Grade
from forms import LoginForm, RegistrationForm, GroupForm, UserForm, CourseForm, ScheduleForm, GradeForm
from config import Config
from datetime import datetime, date
from sqlalchemy import func
import logging
import hashlib  # Добавлен новый импорт

app = Flask(__name__)
app.config.from_object(Config)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Создание таблиц БД
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(email=form.email.data).first()
            
            if user and user.check_password(form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            flash('Invalid email or password', 'danger')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'danger')
    
    return render_template('auth/login.html', title='Login', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(
                username=form.username.data,
                email=form.email.data,
                full_name=form.full_name.data,
                role=form.role.data,
                birth_date=form.birth_date.data,
                contacts=form.contacts.data,
                specialization=form.specialization.data
            )
            user.set_password(form.password.data)  # Хеширование пароля
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! You can now login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error during registration: {str(e)}', 'danger')
    
    return render_template('auth/register.html', form=form)

@app.route('/', methods=['GET', 'POST'])  # Теперь принимает и GET, и POST
def index():
    if request.method == 'POST':
        # Обработка POST-запроса (например, форма входа)
        return redirect(url_for('login'))  # Или другая логика
    
    # Остальной код для GET-запроса
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    
    form = LoginForm()
    return render_template('auth/login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin/dashboard', methods=['GET'])  # Явно указываем GET
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        abort(403)
    
    stats = {
        'users': User.query.count(),
        'groups': Group.query.count(),
        'courses': Course.query.count(),
        'teachers': User.query.filter_by(role='teacher').count(),
        'students': User.query.filter_by(role='student').count()
    }
    return render_template('admin/dashboard.html', stats=stats)
# Группы
@app.route('/admin/groups')
@login_required
def admin_groups():
    if current_user.role != 'admin':
        abort(403)
    
    groups = Group.query.all()
    return render_template('admin/groups.html', groups=groups)

@app.route('/admin/group/add', methods=['GET', 'POST'])
@login_required
def add_group():
    if current_user.role != 'admin':
        abort(403)
    
    form = GroupForm()
    if form.validate_on_submit():
        group = Group(name=form.name.data)
        db.session.add(group)
        db.session.commit()
        flash('Group added successfully!', 'success')
        return redirect(url_for('admin_groups'))
    return render_template('admin/add_group.html', form=form)

@app.route('/admin/group/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_group(id):
    if current_user.role != 'admin':
        abort(403)
    
    group = Group.query.get_or_404(id)
    form = GroupForm(obj=group)
    if form.validate_on_submit():
        form.populate_obj(group)
        db.session.commit()
        flash('Group updated successfully!', 'success')
        return redirect(url_for('admin_groups'))
    return render_template('admin/edit_group.html', form=form, group=group)

@app.route('/admin/group/delete/<int:id>', methods=['POST'])
@login_required
def delete_group(id):
    if current_user.role != 'admin':
        abort(403)
    
    group = Group.query.get_or_404(id)
    if group.students.count() > 0 or group.courses.count() > 0:
        flash('Cannot delete group with students or courses!', 'danger')
    else:
        db.session.delete(group)
        db.session.commit()
        flash('Group deleted successfully!', 'success')
    return redirect(url_for('admin_groups'))

# Пользователи
@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        abort(403)
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/user/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        abort(403)
    
    form = UserForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            role=form.role.data,
            birth_date=form.birth_date.data,
            contacts=form.contacts.data,
            specialization=form.specialization.data,
            group_id=form.group_id.data if form.group_id.data != 0 else None
        )
        # Генерируем временный пароль
        user.set_password('temp123')
        db.session.add(user)
        db.session.commit()
        flash('User added successfully! Temporary password: temp123', 'success')
        return redirect(url_for('admin_users'))
    return render_template('admin/add_user.html', form=form)

@app.route('/admin/user/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if current_user.role != 'admin':
        abort(403)
    
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    form.group_id.data = user.group_id if user.group_id else 0
    
    if form.validate_on_submit():
        form.populate_obj(user)
        user.group_id = form.group_id.data if form.group_id.data != 0 else None
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin_users'))
    return render_template('admin/edit_user.html', form=form, user=user)

@app.route('/admin/user/delete/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    if current_user.role != 'admin':
        abort(403)
    
    user = User.query.get_or_404(id)
    if user.role == 'teacher' and user.taught_courses.count() > 0:
        flash('Cannot delete teacher with assigned courses!', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_users'))

# Курсы
@app.route('/admin/courses')
@login_required
def admin_courses():
    if current_user.role != 'admin':
        abort(403)
    
    courses = Course.query.join(Group).join(User).all()
    return render_template('admin/courses.html', courses=courses)

@app.route('/admin/course/add', methods=['GET', 'POST'])
@login_required
def add_course():
    if current_user.role != 'admin':
        abort(403)
    
    form = CourseForm()
    if form.validate_on_submit():
        course = Course(
            discipline=form.discipline.data,
            group_id=form.group_id.data,
            teacher_id=form.teacher_id.data,
            location=form.location.data
        )
        db.session.add(course)
        db.session.commit()
        flash('Course added successfully!', 'success')
        return redirect(url_for('admin_courses'))
    return render_template('admin/add_course.html', form=form)

@app.route('/admin/course/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_course(id):
    if current_user.role != 'admin':
        abort(403)
    
    course = Course.query.get_or_404(id)
    form = CourseForm(obj=course)
    if form.validate_on_submit():
        form.populate_obj(course)
        db.session.commit()
        flash('Course updated successfully!', 'success')
        return redirect(url_for('admin_courses'))
    return render_template('admin/edit_course.html', form=form, course=course)

@app.route('/admin/course/delete/<int:id>', methods=['POST'])
@login_required
def delete_course(id):
    if current_user.role != 'admin':
        abort(403)
    
    course = Course.query.get_or_404(id)
    db.session.delete(course)
    db.session.commit()
    flash('Course deleted successfully!', 'success')
    return redirect(url_for('admin_courses'))

# Расписание
@app.route('/admin/schedules')
@login_required
def admin_schedules():
    if current_user.role != 'admin':
        abort(403)
    
    schedules = Schedule.query.join(Course).all()
    return render_template('admin/schedules.html', schedules=schedules)

@app.route('/admin/schedule/add', methods=['GET', 'POST'])
@login_required
def add_schedule():
    if current_user.role != 'admin':
        abort(403)
    
    form = ScheduleForm()
    if form.validate_on_submit():
        schedule = Schedule(
            course_id=form.course_id.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data
        )
        db.session.add(schedule)
        db.session.commit()
        flash('Schedule added successfully!', 'success')
        return redirect(url_for('admin_schedules'))
    return render_template('admin/add_schedule.html', form=form)

@app.route('/admin/schedule/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_schedule(id):
    if current_user.role != 'admin':
        abort(403)
    
    schedule = Schedule.query.get_or_404(id)
    form = ScheduleForm(obj=schedule)
    if form.validate_on_submit():
        form.populate_obj(schedule)
        db.session.commit()
        flash('Schedule updated successfully!', 'success')
        return redirect(url_for('admin_schedules'))
    return render_template('admin/edit_schedule.html', form=form, schedule=schedule)

@app.route('/admin/schedule/delete/<int:id>', methods=['POST'])
@login_required
def delete_schedule(id):
    if current_user.role != 'admin':
        abort(403)
    
    schedule = Schedule.query.get_or_404(id)
    db.session.delete(schedule)
    db.session.commit()
    flash('Schedule deleted successfully!', 'success')
    return redirect(url_for('admin_schedules'))

# Оценки
@app.route('/admin/grades')
@login_required
def admin_grades():
    if current_user.role != 'admin':
        abort(403)
    
    grades = Grade.query.join(User).join(Course).all()
    return render_template('admin/grades.html', grades=grades)

@app.route('/admin/grade/add', methods=['GET', 'POST'])
@login_required
def add_grade():
    if current_user.role != 'admin':
        abort(403)
    
    form = GradeForm()
    if form.validate_on_submit():
        grade = Grade(
            student_id=form.student_id.data,
            course_id=form.course_id.data,
            grade=form.grade.data,
            date=form.date.data
        )
        db.session.add(grade)
        db.session.commit()
        flash('Grade added successfully!', 'success')
        return redirect(url_for('admin_grades'))
    return render_template('admin/add_grade.html', form=form)

@app.route('/admin/grade/delete/<int:id>', methods=['POST'])
@login_required
def delete_grade(id):
    if current_user.role != 'admin':
        abort(403)
    
    grade = Grade.query.get_or_404(id)
    db.session.delete(grade)
    db.session.commit()
    flash('Grade deleted successfully!', 'success')
    return redirect(url_for('admin_grades'))

# Маршруты преподавателя
@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        abort(403)
    
    stats = {
        'courses': Course.query.filter_by(teacher_id=current_user.id).count(),
        'students': db.session.query(User).join(Grade, User.id == Grade.student_id)
                    .join(Course, Grade.course_id == Course.id)
                    .filter(Course.teacher_id == current_user.id)
                    .distinct().count()
    }
    return render_template('teacher/dashboard.html', stats=stats)

@app.route('/teacher/courses')
@login_required
def teacher_courses():
    if current_user.role != 'teacher':
        abort(403)
    
    courses = Course.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher/courses.html', courses=courses)

@app.route('/teacher/grades')
@login_required
def teacher_grades():
    if current_user.role != 'teacher':
        abort(403)
    
    grades = Grade.query.join(Course).filter(Course.teacher_id == current_user.id).all()
    return render_template('teacher/grades.html', grades=grades)

@app.route('/teacher/grade/add', methods=['GET', 'POST'])
@login_required
def teacher_add_grade():
    if current_user.role != 'teacher':
        abort(403)
    
    form = GradeForm()
    # Ограничиваем выбор курсов только теми, которые ведет текущий преподаватель
    form.course_id.choices = [(c.id, f"{c.discipline} ({c.group.name})") 
                            for c in Course.query.filter_by(teacher_id=current_user.id)
                            .join(Group).order_by(Group.name, Course.discipline).all()]
    
    if form.validate_on_submit():
        grade = Grade(
            student_id=form.student_id.data,
            course_id=form.course_id.data,
            grade=form.grade.data,
            date=form.date.data
        )
        db.session.add(grade)
        db.session.commit()
        flash('Grade added successfully!', 'success')
        return redirect(url_for('teacher_grades'))
    return render_template('teacher/add_grade.html', form=form)

# Маршруты студента
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        abort(403)
    
    stats = {
        'courses': Course.query.join(Group).filter(Group.id == current_user.group_id).count(),
        'grades': Grade.query.filter_by(student_id=current_user.id).count(),
        'avg_grade': db.session.query(func.avg(Grade.grade))
                     .filter_by(student_id=current_user.id).scalar()
    }
    return render_template('student/dashboard.html', stats=stats)

@app.route('/student/schedule')
@login_required
def student_schedule():
    if current_user.role != 'student' or not current_user.group_id:
        abort(403)
    
    now = datetime.now()
    schedules = Schedule.query.join(Course).filter(
        Course.group_id == current_user.group_id,
        Schedule.start_time >= now
    ).order_by(Schedule.start_time).all()
    return render_template('student/schedule.html', schedules=schedules)

@app.route('/student/grades')
@login_required
def student_grades():
    if current_user.role != 'student':
        abort(403)
    
    grades = Grade.query.filter_by(student_id=current_user.id).join(Course).all()
    return render_template('student/grades.html', grades=grades)

if __name__ == '__main__':
    app.run(debug=True)