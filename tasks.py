from datetime import datetime, timedelta, time as dtime
import re
from models import db, Medication, Reminder

def _parse_times(times_str: str):
    """兼容中英文标点的时间串，输出去重排序后的 (hh, mm) 列表。"""
    if not times_str:
        return []
    # 标点归一化：中文逗号/分号/顿号 → 英文逗号；中文冒号 → 英文冒号
    s = re.sub(r"[，、；;]", ",", times_str.strip())
    s = s.replace("：", ":")
    out = []
    for item in s.split(","):
        item = item.strip()
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", item)
        if not m:
            continue
        h, mnt = int(m.group(1)), int(m.group(2))
        if 0 <= h < 24 and 0 <= mnt < 60:
            out.append((h, mnt))
    # 去重 + 排序
    return sorted(set(out))

def send_due_reminders(app):
    """在未来 24 小时内，为处于用药周期的药品生成提醒（若尚不存在）。"""
    with app.app_context():
        now = datetime.now()
        horizon = now + timedelta(hours=24)
        created = 0

        # 仅处理 active 的用药
        meds = Medication.query.filter_by(active=True).all()

        for med in meds:
            for day in (now.date(), (now + timedelta(days=1)).date()):
                if med.start_date and day < med.start_date:
                    continue
                if med.end_date and day > med.end_date:
                    continue

                for (hh, mm) in _parse_times(med.times):
                    dt = datetime.combine(day, dtime(hh, mm))
                    # 仅生成“未来 ≤24h”内的提醒；等于 now 的边界也跳过
                    if dt <= now or dt > horizon:
                        continue

                    # 轻量存在性检查：只取 id，避免加载整行
                    exists = (db.session.query(Reminder.id)
                              .filter(Reminder.medication_id == med.id,
                                      Reminder.remind_time == dt)
                              .limit(1).first())
                    if exists:
                        continue

                    db.session.add(Reminder(
                        user_id=med.user_id,
                        medication_id=med.id,
                        remind_time=dt,
                        confirmed=False
                    ))
                    created += 1

        if created:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                app.logger.exception(f"[APS] commit failed: {e}")
            else:
                app.logger.info(f"[APS] created {created} reminder(s) up to {horizon:%Y-%m-%d %H:%M}")
        else:
            app.logger.info(f"[APS] tick @ {now:%H:%M:%S} (no new reminders)")
