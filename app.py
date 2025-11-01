import os
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from datetime import datetime
from models import db, User, Medication, Reminder, HealthRecord
from utils import generate_health_report
from dotenv import load_dotenv

load_dotenv()

scheduler = None  # 全局引用，便于优雅关停

def start_scheduler_if_needed(app):
    """只在未启动时启动 APScheduler；把 app 透传给任务函数。"""
    global scheduler
    if scheduler and getattr(scheduler, "running", False):
        return scheduler

    scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
    from tasks import send_due_reminders
    scheduler.add_job(
        send_due_reminders,
        'interval',
        seconds=30,              # 示例：每 30 秒扫描未来 24h
        id='reminder',
        coalesce=True,
        max_instances=1,
        replace_existing=True,
        kwargs={'app': app}
    )
    scheduler.start()
    app.logger.info("[APS] scheduler started")
    atexit.register(lambda: scheduler.shutdown(wait=False))
    return scheduler

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///med_reminder.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'devkey')

    db.init_app(app)
    with app.app_context():
        db.create_all()

    @app.route('/')
    def index():
        users = User.query.all()
        now = datetime.now()
        upcoming = (Reminder.query
                    .filter(Reminder.remind_time >= now)
                    .order_by(Reminder.remind_time)
                    .limit(20).all())
        sample_records = []
        if users:
            u = users[0]
            records = (HealthRecord.query
                       .filter_by(user_id=u.id)
                       .order_by(HealthRecord.record_time.desc())
                       .limit(10).all())
            sample_records = [
                {'time': r.record_time.strftime("%Y-%m-%d %H:%M"),
                 'kind': r.kind, 'value': r.value}
                for r in reversed(records)
            ]
        return render_template('index.html',
                               users=users,
                               upcoming=upcoming,
                               sample_records=sample_records)

    @app.route('/medication/add', methods=('GET', 'POST'))
    def add_medication():
        if request.method == 'POST':
            user_id = int(request.form['user_id'])
            name = request.form['name']
            dose = request.form.get('dose', '')
            times = request.form['times']
            start = datetime.strptime(request.form['start_date'], "%Y-%m-%d").date()
            end = datetime.strptime(request.form['end_date'], "%Y-%m-%d").date()
            med = Medication(user_id=user_id, name=name, dose=dose,
                             times=times, start_date=start, end_date=end)
            db.session.add(med)
            db.session.commit()
            return redirect(url_for('index'))
        users = User.query.all()
        return render_template('add_medication.html', users=users)

    @app.route('/reminder/confirm/<int:reminder_id>', methods=('POST',))
    def confirm_reminder(reminder_id):
        r = Reminder.query.get_or_404(reminder_id)
        r.confirmed = True
        db.session.commit()
        return jsonify({'status': 'ok'})

    @app.route('/health/add', methods=('POST',))
    def add_health():
        user_id = int(request.form['user_id'])
        kind = request.form['kind']
        value = request.form['value']
        hr = HealthRecord(user_id=user_id, kind=kind, value=value)
        db.session.add(hr)
        db.session.commit()
        return redirect(url_for('index'))

    @app.route('/report/<int:user_id>')
    def report(user_id):
        pdf_path = generate_health_report(user_id)
        return send_file(pdf_path, as_attachment=True)

    @app.route('/_create_sample_user')
    def create_sample_user():
        u = User(name="家庭管理员", email=os.getenv('ADMIN_EMAIL', ''))
        db.session.add(u); db.session.commit()
        return f'created user id={u.id}'

    # 注意：这里不启动 scheduler（避免 Debug 下重复）
    return app

# —— 关键：模块级先创建 app，便于 flask CLI 查找，也供 __main__ 使用 ——
app = create_app()

if __name__ == "__main__":
    DEBUG = True
    is_child = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    if is_child or not DEBUG:
        start_scheduler_if_needed(app)
    app.run(debug=DEBUG)
