from database import engine, SessionLocal
from sqlalchemy import text
from models import User

def upgrade_db():
    with engine.connect() as conn:
        try:
            # Check if role column exists, if not add it
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'"))
            conn.commit()
            print("Added 'role' column.")
        except Exception as e:
            # Ignore if already exists
            print("Role column already exists or error:", e)
            
    # Set the first user to admin
    db = SessionLocal()
    first_user = db.query(User).first()
    if first_user:
        first_user.role = 'admin'
        db.commit()
        print(f"Set {first_user.name} to admin.")
    db.close()

if __name__ == "__main__":
    upgrade_db()
