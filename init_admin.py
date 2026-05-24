from database import SessionLocal, engine
import models
from passlib.context import CryptContext

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

admin = db.query(models.User).filter_by(role="admin").first()
if not admin:
    admin = models.User(
        name="Admin Hazats",
        email="admin@hazats.id",
        hashed_password=pwd_context.hash("admin123"),
        pendaki_id="JBR-ADMIN-01",
        role="admin"
    )
    db.add(admin)
    db.commit()
    print("Admin user created: admin@hazats.id / admin123")
else:
    print("Admin user already exists.")
db.close()
