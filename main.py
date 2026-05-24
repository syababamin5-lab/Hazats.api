from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
import bcrypt
from pydantic import BaseModel
from typing import Optional, List
import models
from database import SessionLocal, engine
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os
import shutil
import uuid

# ─── Inisialisasi DB ──────────────────────────────────────────────────────
models.Base.metadata.create_all(bind=engine)

# ─── Config ───────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "hazats-adventure-secret-key-jbr-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

app = FastAPI(title="Hazats Adventure API", version="2.0.0")

# Static files untuk uploads
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ph = PasswordHasher()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, password)
    except VerifyMismatchError:
        return False
    except InvalidHashError:
        try:
            if hashed.startswith("$2b$") or hashed.startswith("$2a$"):
                return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            pass
        return False
    except Exception:
        return False


# ─── Database Dependency ──────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── JWT Helpers ──────────────────────────────────────────────────────────
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau sudah kedaluwarsa",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        contact: str = payload.get("sub")
        if contact is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(
        (models.User.email == contact) | (models.User.phone == contact)
    ).first()
    if user is None:
        raise credentials_exception
    return user


def admin_required(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses hanya untuk admin"
        )
    return current_user


# ─── Pydantic Schemas ─────────────────────────────────────────────────────
class UserCreate(BaseModel):
    name: str
    contact: str
    password: str


class UserLogin(BaseModel):
    contact: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    pendaki_id: str
    name: str
    role: str


class TripCreate(BaseModel):
    mountain_name: str
    description: Optional[str] = None
    difficulty: Optional[str] = "Pemula"
    departure_date: str
    return_date: Optional[str] = None
    max_quota: int
    transport: Optional[str] = None
    price: float
    meeting_point: Optional[str] = None
    image_url: Optional[str] = None


class TripUpdate(BaseModel):
    mountain_name: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[str] = None
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    max_quota: Optional[int] = None
    transport: Optional[str] = None
    price: Optional[float] = None
    meeting_point: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class BookingStatusUpdate(BaseModel):
    status: str  # "confirmed" atau "cancelled"


class ConfigItemCreate(BaseModel):
    name: str


class GuideCreate(BaseModel):
    name: str
    photo_url: Optional[str] = None
    history: Optional[str] = None


# ─── Seed Data ────────────────────────────────────────────────────────────
def seed_data(db: Session):
    # Seed admin
    admin = db.query(models.User).filter(models.User.email == "admin").first()
    if not admin:
        db.add(models.User(
            name="Admin Hazats",
            email="admin",
            phone=None,
            hashed_password=hash_password("admin"),
            pendaki_id="JBR-ADMIN",
            role="admin"
        ))
        db.commit()
        print("[OK] Admin seed berhasil: user=admin / pw=admin")

    # Seed sample trips
    if db.query(models.Trip).count() == 0:
        sample_trips = [
            models.Trip(
                mountain_name="Gunung Papandayan",
                description="Gunung berapi aktif dengan kawah belerang dan padang edelweis yang indah. Sangat cocok untuk pendaki pemula yang ingin pengalaman pertama yang tak terlupakan.",
                difficulty="Pemula",
                departure_date="2026-08-10",
                return_date="2026-08-11",
                max_quota=15,
                remaining_quota=15,
                transport="Hiace Commuter (AC)",
                price=450000,
                meeting_point="Lapangan Parkir Alun-Alun Soreang, Kab. Bandung",
                image_url="https://images.unsplash.com/photo-1544605051-fb18e9a265b4?q=80&w=2070&auto=format&fit=crop",
                is_active=True
            ),
            models.Trip(
                mountain_name="Gunung Gede",
                description="Salah satu gunung paling ikonik di Jawa Barat. Jalurnya menantang namun terbayar dengan pemandangan puncak yang luar biasa dan padang suryakencana.",
                difficulty="Menengah",
                departure_date="2026-08-17",
                return_date="2026-08-18",
                max_quota=10,
                remaining_quota=10,
                transport="Elf Long (AC)",
                price=550000,
                meeting_point="Gerbang Tol Pasteur, Bandung",
                image_url="https://images.unsplash.com/photo-1516466723877-e4ec1d736c8a?q=80&w=2134&auto=format&fit=crop",
                is_active=True
            ),
            models.Trip(
                mountain_name="Gunung Cikurai",
                description="Gunung Cikurai di Garut menawarkan jalur yang menantang menembus hutan tropis lebat dengan pemandangan puncak yang sering diselimuti kabut putih yang mistis.",
                difficulty="Menengah",
                departure_date="2026-09-05",
                return_date="2026-09-06",
                max_quota=12,
                remaining_quota=12,
                transport="Hiace Commuter (AC)",
                price=500000,
                meeting_point="Lapangan Parkir Alun-Alun Soreang, Kab. Bandung",
                image_url="https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?q=80&w=2070&auto=format&fit=crop",
                is_active=True
            ),
        ]
        db.add_all(sample_trips)
        db.commit()
        print("[OK] Trip seed berhasil: 3 trip contoh ditambahkan")

    # Seed config transports
    if db.query(models.TransportConfig).count() == 0:
        transports = [
            models.TransportConfig(name="Hiace Commuter (AC)"),
            models.TransportConfig(name="Elf Long (AC)"),
            models.TransportConfig(name="Avanza / Xenia (AC)")
        ]
        db.add_all(transports)
        db.commit()
        print("[OK] Transport seed berhasil")

    # Seed config meeting points
    if db.query(models.MeetingPointConfig).count() == 0:
        points = [
            models.MeetingPointConfig(name="Lapangan Parkir Alun-Alun Soreang, Kab. Bandung"),
            models.MeetingPointConfig(name="Gerbang Tol Pasteur, Bandung")
        ]
        db.add_all(points)
        db.commit()
        print("[OK] Meeting point seed berhasil")

    # Seed guides
    if db.query(models.Guide).count() == 0:
        guides = [
            models.Guide(
                name="Kang Ewon",
                photo_url="https://images.unsplash.com/photo-1533227260871-e08cb00fcb0d?q=80&w=2070&auto=format&fit=crop",
                history="Telah mendaki lebih dari 50 gunung di Indonesia. Berpengalaman sebagai porter dan pemandu selama 10 tahun. Spesialis di jalur Gunung Gede Pangrango."
            ),
            models.Guide(
                name="Kang Asep",
                photo_url="https://images.unsplash.com/photo-1542223189-67a03fa0f0bd?q=80&w=2074&auto=format&fit=crop",
                history="Mantan anggota SAR daerah dengan spesialisasi navigasi darat dan survival. Selalu mengutamakan keselamatan dan kenyamanan pendaki pemula."
            )
        ]
        db.add_all(guides)
        db.commit()
        print("[OK] Guides seed berhasil")


@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()


# ─── Helper Functions ─────────────────────────────────────────────────────
def get_user_by_contact(db: Session, contact: str):
    return db.query(models.User).filter(
        (models.User.email == contact) | (models.User.phone == contact)
    ).first()


def generate_pendaki_id(db: Session) -> str:
    year = datetime.utcnow().year
    count = db.query(models.User).filter(models.User.role == "user").count()
    return f"JBR-{year}-{(count + 1):04d}"


# ─── AUTH Endpoints ───────────────────────────────────────────────────────
@app.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_contact(db, user.contact):
        raise HTTPException(status_code=400, detail="Kontak sudah terdaftar")

    email = user.contact if "@" in user.contact else None
    phone = user.contact if "@" not in user.contact else None

    db_user = models.User(
        name=user.name,
        email=email,
        phone=phone,
        hashed_password=hash_password(user.password),
        pendaki_id=generate_pendaki_id(db)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    token = create_access_token({"sub": user.contact, "role": db_user.role})
    return {"access_token": token, "token_type": "bearer",
            "pendaki_id": db_user.pendaki_id, "name": db_user.name, "role": db_user.role}


@app.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = get_user_by_contact(db, user.contact)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Username atau password salah")
    
    # Auto-migrate password hash to argon2 if it is currently bcrypt
    if db_user.hashed_password.startswith(("$2b$", "$2a$")):
        try:
            db_user.hashed_password = hash_password(user.password)
            db.commit()
            db.refresh(db_user)
        except Exception:
            pass  # Jangan ganggu login jika migrasi gagal
            
    token = create_access_token({"sub": user.contact, "role": db_user.role})
    return {"access_token": token, "token_type": "bearer",
            "pendaki_id": db_user.pendaki_id, "name": db_user.name, "role": db_user.role}


@app.get("/me")
def get_me(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "pendaki_id": current_user.pendaki_id,
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role,
        "created_at": current_user.created_at.isoformat()
    }


# ─── TRIP Endpoints ───────────────────────────────────────────────────────
@app.get("/trips")
def get_trips(db: Session = Depends(get_db)):
    return db.query(models.Trip).filter(models.Trip.is_active == True).all()


@app.get("/trips/all")
def get_all_trips(db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    return db.query(models.Trip).order_by(models.Trip.created_at.desc()).all()


@app.get("/trips/{trip_id}")
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(models.Trip).filter(models.Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip tidak ditemukan")
    return trip


@app.post("/trips", status_code=201)
def create_trip(trip: TripCreate, db: Session = Depends(get_db),
                admin: models.User = Depends(admin_required)):
    db_trip = models.Trip(**trip.dict(), remaining_quota=trip.max_quota)
    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)
    return db_trip


@app.put("/trips/{trip_id}")
def update_trip(trip_id: int, trip_update: TripUpdate, db: Session = Depends(get_db),
                admin: models.User = Depends(admin_required)):
    db_trip = db.query(models.Trip).filter(models.Trip.id == trip_id).first()
    if not db_trip:
        raise HTTPException(status_code=404, detail="Trip tidak ditemukan")
    for key, value in trip_update.dict(exclude_unset=True).items():
        setattr(db_trip, key, value)
    db.commit()
    db.refresh(db_trip)
    return db_trip


@app.delete("/trips/{trip_id}")
def delete_trip(trip_id: int, db: Session = Depends(get_db),
                admin: models.User = Depends(admin_required)):
    db_trip = db.query(models.Trip).filter(models.Trip.id == trip_id).first()
    if not db_trip:
        raise HTTPException(status_code=404, detail="Trip tidak ditemukan")
    db_trip.is_active = False
    db.commit()
    return {"message": "Trip berhasil dinonaktifkan"}


# ─── BOOKING Endpoints ────────────────────────────────────────────────────
@app.post("/bookings", status_code=201)
def create_booking(trip_id: int = Query(...), meeting_point: Optional[str] = Query(None), db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)):
    trip = db.query(models.Trip).filter(
        models.Trip.id == trip_id, models.Trip.is_active == True).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip tidak ditemukan")
    if trip.remaining_quota <= 0:
        raise HTTPException(status_code=400, detail="Kuota trip sudah penuh")
        
    if not meeting_point:
        raise HTTPException(status_code=400, detail="Titik kumpul wajib dipilih")

    existing = db.query(models.Booking).filter(
        models.Booking.user_id == current_user.id,
        models.Booking.trip_id == trip_id,
        models.Booking.status != "cancelled"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Anda sudah memesan trip ini")

    booking = models.Booking(user_id=current_user.id, trip_id=trip_id, status="pending", meeting_point=meeting_point)
    db.add(booking)
    trip.remaining_quota -= 1
    db.commit()
    db.refresh(booking)

    return {
        "id": booking.id,
        "status": booking.status,
        "trip": {
            "mountain_name": trip.mountain_name,
            "departure_date": trip.departure_date,
            "price": trip.price
        }
    }


@app.get("/bookings/me")
def get_my_bookings(db: Session = Depends(get_db),
                    current_user: models.User = Depends(get_current_user)):
    bookings = db.query(models.Booking).filter(
        models.Booking.user_id == current_user.id
    ).order_by(models.Booking.created_at.desc()).all()

    return [
        {
            "id": b.id,
            "status": b.status,
            "payment_proof_url": b.payment_proof_url,
            "created_at": b.created_at.isoformat(),
            "meeting_point": b.meeting_point,
            "trip": {
                "id": b.trip.id,
                "mountain_name": b.trip.mountain_name,
                "difficulty": b.trip.difficulty,
                "departure_date": b.trip.departure_date,
                "return_date": b.trip.return_date,
                "price": b.trip.price,
                "transport": b.trip.transport,
                "meeting_point": b.trip.meeting_point,
                "image_url": b.trip.image_url,
            }
        }
        for b in bookings
    ]


@app.post("/bookings/{booking_id}/payment-proof")
async def upload_payment_proof(
    booking_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.user_id == current_user.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking tidak ditemukan")

    ext = os.path.splitext(file.filename)[1]
    filename = f"payment_{booking_id}_{uuid.uuid4().hex}{ext}"
    filepath = f"uploads/{filename}"
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    booking.payment_proof_url = f"/uploads/{filename}"
    db.commit()
    return {"payment_proof_url": booking.payment_proof_url}


@app.get("/bookings")
def get_all_bookings(db: Session = Depends(get_db),
                     admin: models.User = Depends(admin_required)):
    bookings = db.query(models.Booking).order_by(
        models.Booking.created_at.desc()).all()
    return [
        {
            "id": b.id,
            "status": b.status,
            "payment_proof_url": b.payment_proof_url,
            "created_at": b.created_at.isoformat(),
            "meeting_point": b.meeting_point,
            "user": {
                "name": b.user.name,
                "pendaki_id": b.user.pendaki_id,
                "email": b.user.email,
                "phone": b.user.phone,
            },
            "trip": {
                "id": b.trip.id,
                "mountain_name": b.trip.mountain_name,
                "departure_date": b.trip.departure_date,
                "price": b.trip.price,
            }
        }
        for b in bookings
    ]


@app.put("/bookings/{booking_id}/status")
def update_booking_status(
    booking_id: int,
    update: BookingStatusUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(admin_required)
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking tidak ditemukan")
    # Kembalikan kuota jika dibatalkan
    if update.status == "cancelled" and booking.status != "cancelled":
        booking.trip.remaining_quota += 1
    booking.status = update.status
    db.commit()
    return {"id": booking.id, "status": booking.status}


# ─── ADMIN: Users ─────────────────────────────────────────────────────────
@app.get("/admin/users")
def get_all_users(db: Session = Depends(get_db),
                  admin: models.User = Depends(admin_required)):
    users = db.query(models.User).filter(models.User.role == "user").all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "pendaki_id": u.pendaki_id,
            "email": u.email,
            "phone": u.phone,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
            "total_bookings": len(u.bookings)
        }
        for u in users
    ]


# ─── GALLERY Endpoints ────────────────────────────────────────────────────
@app.post("/gallery", status_code=201)
async def upload_gallery_image(
    file: UploadFile = File(...),
    description: str = "",
    db: Session = Depends(get_db),
    admin: models.User = Depends(admin_required)
):
    ext = os.path.splitext(file.filename)[1]
    filename = f"gallery_{uuid.uuid4().hex}{ext}"
    filepath = f"uploads/{filename}"
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    gallery_image = models.GalleryImage(
        filename=filename,
        url=f"/uploads/{filename}",
        description=description
    )
    db.add(gallery_image)
    db.commit()
    db.refresh(gallery_image)
    return gallery_image


@app.get("/gallery")
def get_gallery(db: Session = Depends(get_db),
                admin: models.User = Depends(admin_required)):
    return db.query(models.GalleryImage).order_by(
        models.GalleryImage.uploaded_at.desc()).all()


@app.delete("/gallery/{image_id}")
def delete_gallery_image(image_id: int, db: Session = Depends(get_db),
                          admin: models.User = Depends(admin_required)):
    img = db.query(models.GalleryImage).filter(
        models.GalleryImage.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Gambar tidak ditemukan")
    filepath = f"uploads/{img.filename}"
    if os.path.exists(filepath):
        os.remove(filepath)
    db.delete(img)
    db.commit()
    return {"message": "Gambar berhasil dihapus"}


# ─── CONFIG Endpoints ─────────────────────────────────────────────────────
@app.get("/admin/config/transports")
def get_transports(db: Session = Depends(get_db)):
    return db.query(models.TransportConfig).order_by(models.TransportConfig.created_at.asc()).all()


@app.post("/admin/config/transports", status_code=201)
def create_transport(item: ConfigItemCreate, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    db_item = models.TransportConfig(name=item.name)
    db.add(db_item)
    try:
        db.commit()
        db.refresh(db_item)
        return db_item
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Transportasi sudah ada")


@app.delete("/admin/config/transports/{item_id}")
def delete_transport(item_id: int, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    db_item = db.query(models.TransportConfig).filter(models.TransportConfig.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item tidak ditemukan")
    db.delete(db_item)
    db.commit()
    return {"message": "Item berhasil dihapus"}


@app.get("/admin/config/meeting-points")
def get_meeting_points(db: Session = Depends(get_db)):
    return db.query(models.MeetingPointConfig).order_by(models.MeetingPointConfig.created_at.asc()).all()


@app.post("/admin/config/meeting-points", status_code=201)
def create_meeting_point(item: ConfigItemCreate, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    db_item = models.MeetingPointConfig(name=item.name)
    db.add(db_item)
    try:
        db.commit()
        db.refresh(db_item)
        return db_item
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Titik Kumpul sudah ada")


# ─── GUIDES Endpoints ─────────────────────────────────────────────────────
@app.get("/guides")
def get_guides(db: Session = Depends(get_db)):
    return db.query(models.Guide).order_by(models.Guide.created_at.desc()).all()


@app.post("/guides", status_code=201)
def create_guide(guide: GuideCreate, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    db_guide = models.Guide(**guide.dict())
    db.add(db_guide)
    db.commit()
    db.refresh(db_guide)
    return db_guide


@app.put("/guides/{guide_id}")
def update_guide(guide_id: int, update_data: GuideCreate, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    db_guide = db.query(models.Guide).filter(models.Guide.id == guide_id).first()
    if not db_guide:
        raise HTTPException(status_code=404, detail="Pemandu tidak ditemukan")
    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(db_guide, key, value)
    db.commit()
    db.refresh(db_guide)
    return db_guide


@app.delete("/guides/{guide_id}")
def delete_guide(guide_id: int, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    db_guide = db.query(models.Guide).filter(models.Guide.id == guide_id).first()
    if not db_guide:
        raise HTTPException(status_code=404, detail="Pemandu tidak ditemukan")
    db.delete(db_guide)
    db.commit()
    return {"message": "Pemandu berhasil dihapus"}

@app.delete("/admin/config/meeting-points/{item_id}")
def delete_meeting_point(item_id: int, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    db_item = db.query(models.MeetingPointConfig).filter(models.MeetingPointConfig.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item tidak ditemukan")
    db.delete(db_item)
    db.commit()
    return {"message": "Item berhasil dihapus"}

# ─── LIVE CHAT (WebSockets) ───────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/chat/{client_id}")
async def websocket_chat_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            db = SessionLocal()
            chat_msg = models.ChatMessage(session_id=client_id, sender="user", message=data)
            db.add(chat_msg)
            db.commit()
            db.close()
            await manager.broadcast(f"{client_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")

@app.get("/admin/chat/history")
def get_chat_history(db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    return db.query(models.ChatMessage).order_by(models.ChatMessage.created_at.desc()).limit(100).all()
