from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Query, WebSocket, WebSocketDisconnect
import httpx
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
from sqlalchemy import text
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE trips ADD COLUMN via VARCHAR NULL"))
        conn.commit()
    except:
        conn.rollback()
    try:
        conn.execute(text("ALTER TABLE trips ADD COLUMN trip_type VARCHAR NULL"))
        conn.commit()
    except:
        conn.rollback()
    try:
        conn.execute(text("ALTER TABLE trips ADD COLUMN packages TEXT NULL"))
        conn.commit()
    except:
        conn.rollback()

    # Tambahan kolom User Profile
    new_user_cols = ['nik', 'birth_place_date', 'gender', 'address', 'social_media', 'emergency_contact', 'medical_history', 'ktp_image_url', 'profile_image_url']
    for col in new_user_cols:
        try:
            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} VARCHAR NULL"))
            conn.commit()
        except:
            conn.rollback()

    # Tambah kolom paket trip
    try:
        conn.execute(text("ALTER TABLE private_trip_requests ADD COLUMN notes TEXT NULL"))
        conn.commit()
    except:
        conn.rollback()

    try:
        conn.execute(text("ALTER TABLE mountains ADD COLUMN gallery TEXT NULL"))
        conn.commit()
    except:
        conn.rollback()

    # Tambah kolom paket di bookings
    for col, ctype in [("package_name", "VARCHAR"), ("price_paid", "FLOAT"), ("meeting_point", "VARCHAR"), ("cancel_reason", "TEXT")]:
        try:
            conn.execute(text(f"ALTER TABLE bookings ADD COLUMN {col} {ctype} NULL"))
            conn.commit()
        except:
            conn.rollback()

    try:
        conn.execute(text("ALTER TABLE payment_proofs ADD COLUMN reject_reason VARCHAR NULL"))
        conn.commit()
    except:
        conn.rollback()

models.Base.metadata.create_all(bind=engine)

# ─── Config ───────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "hazats-adventure-secret-key-jbr-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

app = FastAPI(title="Hazats Adventure API", version="2.0.0")

# Static files untuk uploads
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://hazats-web.vercel.app",
    "https://hazats.id",
    "https://www.hazats.id",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

ph = PasswordHasher()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ─── AI Description Generator ─────────────────────────────────────────────
class DescriptionRequest(BaseModel):
    mountain_name: str
    via: Optional[str] = None

@app.post("/generate-description")
async def generate_description(req: DescriptionRequest):
    """Generate AI trip description using Groq (free, no user key needed)"""
    via_text = f" via {req.via}" if req.via else ""
    prompt = f"""Buatkan deskripsi promosi open trip pendakian untuk Gunung {req.mountain_name}{via_text}.

Deskripsi harus informatif, menarik, tidak monoton, dan terstruktur. Pastikan menyebutkan:
1. Berapa estimasi waktu tempuh pendakian (jam) dari basecamp ke puncak.
2. Ada berapa pos (shelter/pos) pendakian di jalur ini, sebutkan namanya.
3. Berapa jalur pendakian resmi yang ada di gunung ini.
4. Apa yang istimewa dan spesial dari gunung ini (pemandangan, flora, fauna, spot foto, dll).
5. Apa highlight atau momen terbaik yang akan dialami peserta.

Format dalam 3 paragraf panjang yang mengalir, memikat, dan membuat pembaca ingin langsung mendaftar.
Gunakan gaya bahasa marketing modern yang semangat dan menginspirasi dalam Bahasa Indonesia.
Jangan memotong kalimat di tengah jalan, selesaikan setiap kalimat."""

    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY belum dikonfigurasi di server.")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                    "temperature": 0.8
                }
            )
            if res.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Groq error: {res.text}")
            data = res.json()
            text = data["choices"][0]["message"]["content"].strip()
            return {"description": text}
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Timeout saat menghubungi AI server.")

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
    gender: str


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    nik: Optional[str] = None
    birth_place_date: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    social_media: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_history: Optional[str] = None
    ktp_image_url: Optional[str] = None
    profile_image_url: Optional[str] = None


class UserLogin(BaseModel):
    contact: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    pendaki_id: str
    name: str
    role: str


class MountainBase(BaseModel):
    name: str
    location: str
    elevation: int
    difficulty: str = "Menengah"
    description: Optional[str] = None
    image_url: Optional[str] = None
    gallery: Optional[str] = None
    is_active: bool = True


class MountainCreate(BaseModel):
    name: str
    location: str
    elevation: int
    difficulty: Optional[str] = "Menengah"
    description: Optional[str] = None
    image_url: Optional[str] = None
    gallery: Optional[str] = None
    is_active: Optional[bool] = True

class MountainUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    elevation: Optional[int] = None
    difficulty: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    gallery: Optional[str] = None
    is_active: Optional[bool] = None

class PrivateTripRequestCreate(BaseModel):
    name: str
    phone: str
    mountain_name: str
    participants_count: int
    start_date: str
    end_date: Optional[str] = None
    notes: Optional[str] = None

class PrivateTripRequestUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class TripCreate(BaseModel):
    mountain_name: str
    via: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[str] = "Pemula"
    departure_date: str
    return_date: Optional[str] = None
    trip_type: Optional[str] = None
    max_quota: int
    transport: Optional[str] = None
    price: float
    meeting_point: Optional[str] = None
    image_url: Optional[str] = None
    packages: Optional[str] = None


class TripUpdate(BaseModel):
    mountain_name: Optional[str] = None
    via: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[str] = None
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    trip_type: Optional[str] = None
    max_quota: Optional[int] = None
    transport: Optional[str] = None
    price: Optional[float] = None
    meeting_point: Optional[str] = None
    image_url: Optional[str] = None
    packages: Optional[str] = None
    is_active: Optional[bool] = None


class BookingStatusUpdate(BaseModel):
    status: str  # "confirmed" atau "cancelled"

class UserCancelRequest(BaseModel):
    reason: str

class ProofStatusUpdate(BaseModel):
    status: str  # "verified" or "rejected"
    reject_reason: Optional[str] = None

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


def generate_pendaki_id(db: Session, gender: str) -> str:
    now = datetime.utcnow()
    year_short = str(now.year)[-2:]
    gender_code = "1" if gender == "Laki-laki" else "2" if gender == "Perempuan" else "0"
    count = db.query(models.User).filter(models.User.role == "user").count()
    return f"HZT-{year_short}-{(count + 1):04d}"


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
        gender=user.gender,
        pendaki_id=generate_pendaki_id(db, user.gender)
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
        "nik": getattr(current_user, 'nik', None),
        "birth_place_date": getattr(current_user, 'birth_place_date', None),
        "gender": getattr(current_user, 'gender', None),
        "address": getattr(current_user, 'address', None),
        "social_media": getattr(current_user, 'social_media', None),
        "emergency_contact": getattr(current_user, 'emergency_contact', None),
        "medical_history": getattr(current_user, 'medical_history', None),
        "ktp_image_url": getattr(current_user, 'ktp_image_url', None),
        "profile_image_url": getattr(current_user, 'profile_image_url', None),
        "role": current_user.role,
        "created_at": current_user.created_at.isoformat()
    }


@app.put("/me")
def update_me(update_data: UserProfileUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    update_dict = update_data.dict(exclude_unset=True)
    for k, v in update_dict.items():
        setattr(current_user, k, v)
    db.commit()
    db.refresh(current_user)
    return {"detail": "Profil berhasil diperbarui"}


# ─── TRIP Endpoints ───────────────────────────────────────────────────────
@app.get("/trips")
def get_trips(db: Session = Depends(get_db)):
    today_str = datetime.now().strftime("%Y-%m-%d")
    return db.query(models.Trip).filter(
        models.Trip.is_active == True,
        models.Trip.departure_date >= today_str
    ).order_by(models.Trip.departure_date.asc()).all()


@app.get("/trips/all")
def get_all_trips(db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    trips = db.query(models.Trip).order_by(models.Trip.departure_date.asc()).all()
    result = []
    for t in trips:
        confirmed_count = db.query(models.Booking).filter(
            models.Booking.trip_id == t.id,
            models.Booking.status == "confirmed"
        ).count()
        pending_count = db.query(models.Booking).filter(
            models.Booking.trip_id == t.id,
            models.Booking.status == "pending"
        ).count()
        trip_dict = {c.name: getattr(t, c.name) for c in t.__table__.columns}
        trip_dict["confirmed_participants"] = confirmed_count
        trip_dict["pending_participants"] = pending_count
        result.append(trip_dict)
    return result


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
    # Periksa apakah sudah ada pendaftar
    booking_count = db.query(models.Booking).filter(models.Booking.trip_id == trip_id).count()
    if booking_count > 0:
        raise HTTPException(status_code=400, detail="Tidak dapat menghapus trip ini karena sudah ada peserta yang mendaftar. Silakan ubah trip ini menjadi Nonaktif saja.")
    try:
        # Hapus trip secara permanen
        db.delete(db_trip)
        db.commit()
        return {"message": "Trip berhasil dihapus secara permanen"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Gagal menghapus di database: {str(e)}")


# ─── BOOKING Endpoints ────────────────────────────────────────────────────
@app.post("/bookings", status_code=201)
def create_booking(trip_id: int = Query(...), meeting_point: Optional[str] = Query(None), package_name: Optional[str] = Query(None), price_paid: Optional[float] = Query(None), db: Session = Depends(get_db),
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

    booking = models.Booking(user_id=current_user.id, trip_id=trip_id, status="pending", meeting_point=meeting_point, package_name=package_name, price_paid=price_paid)
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
            "payment_proof_url": b.payment_proof_url, # Legacy
            "payment_proofs": [{"id": p.id, "file_url": p.file_url, "amount": p.amount, "status": p.status, "created_at": p.created_at.isoformat()} for p in b.payment_proofs],
            "created_at": b.created_at.isoformat(),
            "meeting_point": b.meeting_point,
            "package_name": b.package_name,
            "price_paid": float(b.price_paid) if b.price_paid else None,
            "user": {
                 "name": current_user.name,
                 "email": current_user.email,
                 "phone": current_user.phone,
                 "nik": getattr(current_user, 'nik', None),
                 "emergency_contact": getattr(current_user, 'emergency_contact', None),
                 "medical_history": getattr(current_user, 'medical_history', None)
            },
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
                "via": getattr(b.trip, 'via', None),
            }
        }
        for b in bookings
    ]


@app.post("/bookings/{booking_id}/payment-proof")
async def upload_payment_proof(
    booking_id: int,
    file: UploadFile = File(...),
    amount: float = Form(0),
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

    # Simpan ke tabel payment_proofs
    new_proof = models.PaymentProof(
        booking_id=booking.id,
        file_url=f"/uploads/{filename}",
        amount=amount
    )
    db.add(new_proof)
    db.commit()
    db.refresh(new_proof)
    
    return {
        "id": new_proof.id,
        "file_url": new_proof.file_url,
        "amount": new_proof.amount,
        "created_at": new_proof.created_at.isoformat()
    }


@app.get("/bookings")
def get_all_bookings(db: Session = Depends(get_db),
                     admin: models.User = Depends(admin_required)):
    bookings = db.query(models.Booking).order_by(
        models.Booking.created_at.desc()).all()
    return [
        {
            "id": b.id,
            "status": b.status,
            "payment_proof_url": b.payment_proof_url, # Legacy
            "payment_proofs": [{"id": p.id, "file_url": p.file_url, "amount": p.amount, "status": p.status, "created_at": p.created_at.isoformat()} for p in b.payment_proofs],
            "created_at": b.created_at.isoformat(),
            "meeting_point": b.meeting_point,
            "user": {
                "name": b.user.name,
                "pendaki_id": getattr(b.user, 'pendaki_id', '-'),
                "email": getattr(b.user, 'email', '-'),
                "phone": getattr(b.user, 'phone', '-'),
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

@app.put("/bookings/{booking_id}/cancel")
def cancel_my_booking(
    booking_id: int,
    req: UserCancelRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.user_id == current_user.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking tidak ditemukan")
    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="Booking sudah dibatalkan")

    # Kelola perubahan kuota jika sebelumnya sudah mengambil kuota
    if booking.status in ["confirmed", "dp"]:
        booking.trip.remaining_quota += 1
    
    booking.status = "cancelled"
    booking.cancel_reason = req.reason
    db.commit()
    return {"id": booking.id, "status": booking.status, "cancel_reason": booking.cancel_reason}


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
    # Kelola perubahan kuota
    if update.status == "cancelled" and booking.status != "cancelled":
        booking.trip.remaining_quota += 1
    elif update.status in ["confirmed", "dp"] and booking.status == "cancelled":
        booking.trip.remaining_quota -= 1
    
    # Auto-verify pending proofs
    if update.status in ["confirmed", "dp"]:
        for proof in booking.payment_proofs:
            if proof.status == "pending":
                proof.status = "verified"
                
    booking.status = update.status
    db.commit()
    return {"id": booking.id, "status": booking.status}

@app.put("/admin/payment-proofs/{proof_id}/status")
def update_payment_proof_status(
    proof_id: int,
    update: ProofStatusUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(admin_required)
):
    proof = db.query(models.PaymentProof).filter(models.PaymentProof.id == proof_id).first()
    if not proof:
        raise HTTPException(status_code=404, detail="Bukti pembayaran tidak ditemukan")
    
    proof.status = update.status
    if update.reject_reason is not None:
        proof.reject_reason = update.reject_reason
    db.commit()
    return {"id": proof.id, "status": proof.status, "reject_reason": proof.reject_reason}

# ─── ADMIN: Trip Manifest ────────────────────────────────────────────────────
@app.get("/admin/trips/{trip_id}/manifest")
def get_trip_manifest(trip_id: int, db: Session = Depends(get_db),
                      admin: models.User = Depends(admin_required)):
    trip = db.query(models.Trip).filter(models.Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip tidak ditemukan")

    bookings = db.query(models.Booking).filter(
        models.Booking.trip_id == trip_id
    ).all()

    # Sort: confirmed first, then dp, then awaiting_payment, then pending, then cancelled — then by meeting_point
    status_order = {"confirmed": 0, "dp": 1, "awaiting_payment": 2, "pending": 3, "cancelled": 4}
    bookings.sort(key=lambda b: (
        status_order.get(b.status, 9),
        (b.meeting_point or "").lower()
    ))

    result = []
    for idx, b in enumerate(bookings):
        u = b.user
        has_proof = bool(b.payment_proof_url) or len(b.payment_proofs) > 0
        total_paid = sum(p.amount for p in b.payment_proofs if p.amount and p.status != "rejected")
        result.append({
            "no": idx + 1,
            "booking_id": b.id,
            "status": b.status,
            "has_payment_proof": has_proof,
            "total_paid": total_paid,
            "meeting_point": b.meeting_point or "-",
            "package_name": b.package_name or "-",
            "price_paid": float(b.price_paid) if b.price_paid else None,
            "created_at": b.created_at.isoformat(),
            "user": {
                "id": u.id,
                "name": u.name,
                "pendaki_id": u.pendaki_id or "-",
                "email": u.email or "-",
                "phone": u.phone or "-",
                "nik": u.nik or "-",
                "gender": u.gender or "-",
                "birth_place_date": u.birth_place_date or "-",
                "address": u.address or "-",
                "emergency_contact": u.emergency_contact or "-",
                "medical_history": u.medical_history or "-",
                "profile_image_url": u.profile_image_url,
            }
        })

    return {
        "trip": {
            "id": trip.id,
            "mountain_name": trip.mountain_name,
            "via": trip.via,
            "departure_date": trip.departure_date,
            "return_date": trip.return_date,
            "max_quota": trip.max_quota,
            "remaining_quota": trip.remaining_quota,
        },
        "total": len(bookings),
        "confirmed": sum(1 for b in bookings if b.status == "confirmed"),
        "dp": sum(1 for b in bookings if b.status == "dp"),
        "pending": sum(1 for b in bookings if b.status == "pending"),
        "awaiting_payment": sum(1 for b in bookings if b.status == "awaiting_payment"),
        "cancelled": sum(1 for b in bookings if b.status == "cancelled"),
        "participants": result
    }


# ─── ADMIN: Dashboard Stats ─────────────────────────────────────────────────
@app.get("/admin/stats")
def get_admin_stats(db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    today_str = datetime.now().strftime("%Y-%m-%d")
    next_week_str = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    # 1. Menunggu konfirmasi: Booking "pending"
    pending_verifications = db.query(models.Booking).filter(
        models.Booking.status == "pending"
    ).count()

    # 2. Belum membayar: Booking "awaiting_payment"
    unpaid_bookings = db.query(models.Booking).filter(
        models.Booking.status == "awaiting_payment"
    ).count()

    # 2b. DP: Booking status dp
    dp_bookings = db.query(models.Booking).filter(
        models.Booking.status == "dp"
    ).count()

    # 3. Trip Tersedia (belum berangkat)
    available_trips = db.query(models.Trip).filter(models.Trip.departure_date >= today_str).count()

    # 4. Trip Sudah Lewat
    past_trips = db.query(models.Trip).filter(models.Trip.departure_date < today_str).count()

    # 5. Trip Berangkat Minggu Ini (antara hari ini dan 7 hari ke depan)
    upcoming_trips = db.query(models.Trip).filter(
        models.Trip.departure_date >= today_str,
        models.Trip.departure_date <= next_week_str
    ).count()

    # 6. Total peserta yang sudah ikut (status confirmed pada trip yang sudah lewat)
    total_past_participants = db.query(models.Booking).join(models.Trip).filter(
        models.Booking.status == "confirmed",
        models.Trip.departure_date < today_str
    ).count()

    return {
        "pending_verifications": pending_verifications,
        "unpaid_bookings": unpaid_bookings,
        "dp_bookings": dp_bookings,
        "available_trips": available_trips,
        "past_trips": past_trips,
        "upcoming_trips": upcoming_trips,
        "total_past_participants": total_past_participants
    }


# ─── ADMIN: Users ─────────────────────────────────────────────────────────
@app.get("/admin/users")
def get_all_users(db: Session = Depends(get_db),
                  admin: models.User = Depends(admin_required)):
    users = db.query(models.User).filter(models.User.role == "user").all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "pendaki_id": u.pendaki_id or "-",
            "email": u.email,
            "phone": u.phone,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "total_bookings": len(u.bookings) if u.bookings else 0
        }
        for u in users
    ]


@app.get("/admin/users/{user_id}")
def get_user_detail(user_id: int, db: Session = Depends(get_db),
                    admin: models.User = Depends(admin_required)):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return {
        "id": u.id, "name": u.name, "pendaki_id": u.pendaki_id, "email": u.email,
        "phone": u.phone, "nik": u.nik, "birth_place_date": u.birth_place_date,
        "gender": u.gender, "address": u.address, "social_media": u.social_media,
        "emergency_contact": u.emergency_contact, "medical_history": u.medical_history,
        "ktp_image_url": u.ktp_image_url, "profile_image_url": u.profile_image_url,
        "is_active": u.is_active, "created_at": u.created_at.isoformat() if u.created_at else None,
        "total_bookings": len(u.bookings) if u.bookings else 0,
    }


class AdminUserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    nik: Optional[str] = None
    birth_place_date: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    social_media: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_history: Optional[str] = None
    ktp_image_url: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_active: Optional[bool] = None


@app.put("/admin/users/{user_id}")
def admin_update_user(user_id: int, data: AdminUserUpdate,
                      db: Session = Depends(get_db),
                      admin: models.User = Depends(admin_required)):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    for field, value in data.dict(exclude_none=True).items():
        setattr(u, field, value)
    db.commit()
    db.refresh(u)
    return {"message": "Data berhasil diperbarui"}


class AdminPasswordReset(BaseModel):
    new_password: str


@app.put("/admin/users/{user_id}/password")
def admin_reset_password(user_id: int, data: AdminPasswordReset,
                         db: Session = Depends(get_db),
                         admin: models.User = Depends(admin_required)):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    u.hashed_password = pwd_context.hash(data.new_password)
    db.commit()
    return {"message": "Password berhasil diubah"}


# ─── GALLERY Endpoints ────────────────────────────────────────────────────
@app.post("/gallery", status_code=201)
async def upload_gallery_image(
    file: UploadFile = File(...),
    description: str = "",
    db: Session = Depends(get_db),
    admin: models.User = Depends(admin_required)
):
    import base64
    file_bytes = await file.read()
    b64_encoded = base64.b64encode(file_bytes).decode('utf-8')
    mime_type = file.content_type or "image/jpeg"
    data_url = f"data:{mime_type};base64,{b64_encoded}"

    gallery_image = models.GalleryImage(
        filename=file.filename,
        url=data_url,
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
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.admin_connections: dict[str, WebSocket] = {}
        self.last_seen: dict[str, str] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id.startswith("admin"):
            self.admin_connections[client_id] = websocket
        else:
            self.active_connections[client_id] = websocket
            self.last_seen[client_id] = "online"
            await self.broadcast_to_admins(json.dumps({
                "type": "status",
                "session_id": client_id,
                "status": "online"
            }))

    async def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id.startswith("admin"):
            if client_id in self.admin_connections:
                del self.admin_connections[client_id]
        else:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
                last_seen_time = datetime.utcnow().isoformat() + "Z"
                self.last_seen[client_id] = last_seen_time
                await self.broadcast_to_admins(json.dumps({
                    "type": "status",
                    "session_id": client_id,
                    "status": last_seen_time
                }))

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

    async def broadcast_to_admins(self, message: str):
        for connection in self.admin_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/chat/{client_id}")
async def websocket_chat_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                msg_type = payload.get("type", "chat_message")
                
                if msg_type == "typing":
                    await manager.broadcast_to_admins(json.dumps({
                        "type": "typing",
                        "session_id": client_id,
                        "is_typing": payload.get("is_typing", False)
                    }))
                elif msg_type == "read":
                    db = SessionLocal()
                    db.query(models.ChatMessage).filter(
                        models.ChatMessage.session_id == client_id,
                        models.ChatMessage.sender == "admin",
                        models.ChatMessage.is_read == False
                    ).update({"is_read": True})
                    db.commit()
                    db.close()
                    await manager.broadcast_to_admins(json.dumps({
                        "type": "read_receipt",
                        "session_id": client_id
                    }))
                elif msg_type == "edit_message":
                    db = SessionLocal()
                    msg_id = payload.get("id")
                    new_text = payload.get("message")
                    msg_record = db.query(models.ChatMessage).filter(models.ChatMessage.id == msg_id).first()
                    if msg_record and msg_record.sender == "user":
                        time_diff = datetime.utcnow() - msg_record.created_at
                        if time_diff.total_seconds() <= 300:
                            msg_record.message = new_text
                            msg_record.is_edited = True
                            db.commit()
                            update_data = {
                                "type": "message_updated",
                                "id": msg_record.id,
                                "session_id": client_id,
                                "message": new_text,
                                "is_edited": True
                            }
                            await manager.send_personal_message(json.dumps(update_data), client_id)
                            await manager.broadcast_to_admins(json.dumps(update_data))
                    db.close()
                elif msg_type == "delete_message":
                    db = SessionLocal()
                    msg_id = payload.get("id")
                    msg_record = db.query(models.ChatMessage).filter(models.ChatMessage.id == msg_id).first()
                    if msg_record and msg_record.sender == "user":
                        msg_record.is_deleted = True
                        db.commit()
                        update_data = {
                            "type": "message_deleted",
                            "id": msg_record.id,
                            "session_id": client_id,
                            "is_deleted": True
                        }
                        await manager.send_personal_message(json.dumps(update_data), client_id)
                        await manager.broadcast_to_admins(json.dumps(update_data))
                    db.close()
                elif msg_type == "chat_message":
                    db = SessionLocal()
                    text_msg = payload.get("message", "")
                    message_type = payload.get("message_type", "text")
                    attachment_url = payload.get("attachment_url", None)
                    reply_to_id = payload.get("reply_to_id", None)
                    
                    chat_msg = models.ChatMessage(
                        session_id=client_id, 
                        sender="user", 
                        message=text_msg,
                        message_type=message_type,
                        attachment_url=attachment_url,
                        reply_to_id=reply_to_id
                    )
                    db.add(chat_msg)
                    db.commit()
                    db.refresh(chat_msg)
                    
                    msg_data = {
                        "type": "chat_message",
                        "id": chat_msg.id,
                        "session_id": client_id,
                        "sender": "user",
                        "message": text_msg,
                        "message_type": message_type,
                        "attachment_url": attachment_url,
                        "reply_to_id": reply_to_id,
                        "created_at": chat_msg.created_at.isoformat() + "Z",
                        "is_read": False,
                        "is_edited": False,
                        "is_deleted": False
                    }
                    db.close()
                    
                    await manager.send_personal_message(json.dumps(msg_data), client_id)
                    await manager.broadcast_to_admins(json.dumps(msg_data))
                    
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await manager.disconnect(websocket, client_id)

class ChatReply(BaseModel):
    session_id: str
    message: str
    message_type: str = "text"
    attachment_url: Optional[str] = None
    reply_to_id: Optional[int] = None
    
class AdminChatAction(BaseModel):
    id: int
    action: str # "edit" or "delete"
    message: Optional[str] = None

@app.post("/admin/chat/action")
async def admin_chat_action(data: AdminChatAction, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    msg_record = db.query(models.ChatMessage).filter(models.ChatMessage.id == data.id).first()
    if not msg_record or msg_record.sender != "admin":
        raise HTTPException(status_code=403, detail="Tindakan ditolak")
        
    if data.action == "delete":
        msg_record.is_deleted = True
        db.commit()
        update_data = {
            "type": "message_deleted",
            "id": msg_record.id,
            "session_id": msg_record.session_id,
            "is_deleted": True
        }
        await manager.send_personal_message(json.dumps(update_data), msg_record.session_id)
        await manager.broadcast_to_admins(json.dumps(update_data))
        return {"status": "deleted"}
        
    elif data.action == "edit":
        time_diff = datetime.utcnow() - msg_record.created_at
        if time_diff.total_seconds() > 300:
            raise HTTPException(status_code=400, detail="Batas waktu edit (5 menit) telah lewat")
        msg_record.message = data.message
        msg_record.is_edited = True
        db.commit()
        update_data = {
            "type": "message_updated",
            "id": msg_record.id,
            "session_id": msg_record.session_id,
            "message": data.message,
            "is_edited": True
        }
        await manager.send_personal_message(json.dumps(update_data), msg_record.session_id)
        await manager.broadcast_to_admins(json.dumps(update_data))
        return {"status": "edited"}

@app.post("/admin/chat/reply")
async def reply_chat(reply: ChatReply, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    chat_msg = models.ChatMessage(
        session_id=reply.session_id, 
        sender="admin", 
        message=reply.message,
        message_type=reply.message_type,
        attachment_url=reply.attachment_url,
        reply_to_id=reply.reply_to_id
    )
    db.add(chat_msg)
    db.commit()
    db.refresh(chat_msg)
    
    msg_data = {
        "type": "chat_message",
        "id": chat_msg.id,
        "session_id": reply.session_id,
        "sender": "admin",
        "message": reply.message,
        "message_type": reply.message_type,
        "attachment_url": reply.attachment_url,
        "reply_to_id": reply.reply_to_id,
        "created_at": chat_msg.created_at.isoformat() + "Z",
        "is_read": False,
        "is_edited": False,
        "is_deleted": False
    }
    
    await manager.send_personal_message(json.dumps(msg_data), reply.session_id)
    await manager.broadcast_to_admins(json.dumps(msg_data))
    return msg_data

@app.post("/api/chat/upload")
async def upload_chat_attachment(file: UploadFile = File(...)):
    os.makedirs("uploads/chat", exist_ok=True)
    filename = f"{uuid.uuid4()}-{file.filename}"
    file_path = f"uploads/chat/{filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"url": f"/uploads/chat/{filename}"}

@app.get("/admin/chat/history")
def get_chat_history(db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    return db.query(models.ChatMessage).order_by(models.ChatMessage.created_at.asc()).all()

@app.get("/api/chat/history/{client_id}")
def get_user_chat_history(client_id: str, db: Session = Depends(get_db)):
    return db.query(models.ChatMessage).filter(models.ChatMessage.session_id == client_id).order_by(models.ChatMessage.created_at.asc()).all()

class SiteConfigUpdate(BaseModel):
    include_exclude: Optional[str] = None
    itinerary: Optional[str] = None

@app.get("/admin/config/site")
def get_site_config(db: Session = Depends(get_db)):
    config = db.query(models.SiteConfig).first()
    if not config:
        config = models.SiteConfig(include_exclude="", itinerary="")
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

@app.put("/admin/config/site")
def update_site_config(item: SiteConfigUpdate, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    config = db.query(models.SiteConfig).first()
    if not config:
        config = models.SiteConfig(include_exclude=item.include_exclude, itinerary=item.itinerary)
        db.add(config)
    else:
        if item.include_exclude is not None:
            config.include_exclude = item.include_exclude
        if item.itinerary is not None:
            config.itinerary = item.itinerary
    db.commit()
    db.refresh(config)
    return config



@app.get("/api/mountains")
def get_mountains(db: Session = Depends(get_db)):
    return db.query(models.Mountain).order_by(models.Mountain.name.asc()).all()

@app.post("/api/mountains")
def create_mountain(item: MountainCreate, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    db_item = models.Mountain(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.put("/api/mountains/{m_id}")
def update_mountain(m_id: int, item: MountainUpdate, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    db_item = db.query(models.Mountain).filter(models.Mountain.id == m_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Mountain not found")
    for key, value in item.dict(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/mountains/{m_id}")
def delete_mountain(m_id: int, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    db_item = db.query(models.Mountain).filter(models.Mountain.id == m_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Mountain not found")
    db.delete(db_item)
    db.commit()
    return {"status": "deleted"}

# ─── Private Trips API ────────────────────────────────────────────────────
class PrivateTripCreate(BaseModel):
    name: str
    phone: str
    mountain_name: str
    participants_count: int
    start_date: str
    end_date: Optional[str] = None
    notes: Optional[str] = None

class PrivateTripUpdateStatus(BaseModel):
    status: str

@app.post("/api/private-trips")
def create_private_trip(item: PrivateTripCreate, db: Session = Depends(get_db)):
    db_item = models.PrivateTripRequest(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/api/private-trips")
def get_private_trips(db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    return db.query(models.PrivateTripRequest).order_by(models.PrivateTripRequest.created_at.desc()).all()

@app.put("/api/private-trips/{req_id}")
def update_private_trip_status(req_id: int, item: PrivateTripUpdateStatus, db: Session = Depends(get_db), admin: models.User = Depends(admin_required)):
    db_item = db.query(models.PrivateTripRequest).filter(models.PrivateTripRequest.id == req_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Request not found")
    db_item.status = item.status
    db.commit()
    db.refresh(db_item)
    return db_item

@app.post("/api/upload-multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    token: str = Form(...),
    db: Session = Depends(get_db)
):
    # Manual token validation for multipart (OAuth2 doesn't work with multipart)
    from jose import JWTError
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        contact: str = payload.get("sub")
        if contact is None:
            raise HTTPException(status_code=401, detail="Token tidak valid")
        user = db.query(models.User).filter(
            (models.User.email == contact) | (models.User.phone == contact)
        ).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Akses hanya untuk admin")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token tidak valid")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maksimal 10 foto dalam satu kali upload")
        
    os.makedirs("uploads/mountains", exist_ok=True)
    urls = []
    
    for file in files:
        ctype = file.content_type or ""
        if not ctype.startswith("image/"):
            continue
            
        raw_name = file.filename or "photo"
        ext = raw_name.rsplit('.', 1)[-1] if '.' in raw_name else 'jpg'
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = f"uploads/mountains/{filename}"
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        urls.append(f"{base_url}/uploads/mountains/{filename}")
        
    return {"urls": urls}
