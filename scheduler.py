from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from models import db, Medication, Reminder
from utils import send_email
import pytz

def check_and_create_reminders(app):
    with app.app_context():
        now = datetime.now()
        today = now.date()
        meds = Medication.query.filter_by(active=True).all()
        for med in meds:
            if med.start_date <= today <= med.end_date:
                times = [t.strip() for t in med.times.split(',') if t.strip()]
                for t in times:
                    try:
                        hhmm = datetime.strptime(t, "%H:%M").time()
                    except:
                        continue
                    remind_dt = datetime.combine(today, hhmm)
                    delta = (remind_dt - now).total_seconds()
                    # 如果在未来 60 秒内到点，则创建提醒（适用于演示）
                    if 0 <= delta < 60:
                        existing = Reminder.query.filter_by(medication_id=med.id, remind_time=remind_dt).first()
                        if not existing:
                            r = Reminder(medication_id=med.id, remind_time=remind_dt, sent=False, confirmed=False)
                            db.session.add(r); db.session.commit()
                            user = med.user
                            subject = f'用药提醒：{med.name}'
                            body = f'请在 {remind_dt.strftime("%Y-%m-%d %H:%M")} 服用 {med.name}，剂量：{med.dose}'
                            if user and user.email:
                                send_email(user.email, subject, body)
                            r.sent = True
                            db.session.commit()

def start_scheduler(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: check_and_create_reminders(app), 'interval', seconds=60, id='reminder_checker')
    scheduler.start()
