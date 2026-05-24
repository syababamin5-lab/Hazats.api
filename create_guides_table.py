from database import engine
from models import Base
import models

# Create tables if they don't exist
models.Base.metadata.create_all(bind=engine)
print("[OK] Tables created/verified")
