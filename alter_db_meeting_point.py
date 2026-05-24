from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE bookings ADD COLUMN meeting_point VARCHAR NULL"))
        conn.commit()
        print("[OK] Column meeting_point added to bookings")
    except Exception as e:
        print("[ERROR] ", e)
