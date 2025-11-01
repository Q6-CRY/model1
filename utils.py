import os, smtplib
from email.message import EmailMessage
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
import matplotlib.pyplot as plt
from models import User, HealthRecord

SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')

def send_email(to_email, subject, body):
    if not SMTP_SERVER or not SMTP_USER or not SMTP_PASS:
        print("SMTP not configured; skip sending email.")
        return False
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        return True
    except Exception as e:
        print("send_email error:", e)
        return False

def is_float(s):
    try:
        float(s)
        return True
    except:
        return False

def generate_health_report(user_id):
    user = User.query.get(user_id)
    if not user:
        raise ValueError("user not found")
    records = HealthRecord.query.filter_by(user_id=user_id).order_by(HealthRecord.record_time).all()
    times = [r.record_time for r in records if r.kind == 'temperature']
    values = [float(r.value) for r in records if r.kind == 'temperature' and is_float(r.value)]
    img_path = None
    if times and values:
        plt.figure(figsize=(6,3))
        plt.plot(times, values, marker='o')
        plt.title('Temperature Trend')
        plt.xlabel('Time')
        plt.ylabel('Temp')
        plt.tight_layout()
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        img_path = f'static/reports/temperature_{user_id}_{ts}.png'
        plt.savefig(img_path)
        plt.close()

    pdf_path = f'static/reports/health_report_{user_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.pdf'
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setFont("Helvetica", 14)
    c.drawString(50, 750, f"Health Report - {user.name}")
    c.setFont("Helvetica", 10)
    y = 720
    for r in records[-30:][::-1]:
        line = f"{r.record_time.strftime('%Y-%m-%d %H:%M')} | {r.kind} | {r.value} | {r.note or ''}"
        c.drawString(50, y, line)
        y -= 14
        if y < 100:
            c.showPage()
            y = 750
    if img_path:
        try:
            c.showPage()
            c.drawImage(img_path, 50, 350, width=500, height=250)
        except Exception as e:
            print("插入图片失败:", e)
    c.save()
    return pdf_path
