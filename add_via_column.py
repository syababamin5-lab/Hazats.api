from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE trips ADD COLUMN via VARCHAR NULL"))
        conn.commit()
        print("[OK] Column via added to trips")
    except Exception as e:
        print("[INFO] Column via might already exist:", e)
