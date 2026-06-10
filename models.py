from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    pendaki_id = Column(String, unique=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, unique=True, index=True, nullable=True)
    nik = Column(String, nullable=True)
    birth_place_date = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    social_media = Column(String, nullable=True)
    emergency_contact = Column(String, nullable=True)
    medical_history = Column(Text, nullable=True)
    ktp_image_url = Column(Text, nullable=True)
    profile_image_url = Column(Text, nullable=True)
    hashed_password = Column(String)
    role = Column(String, default="user")  # "user" atau "admin"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    bookings = relationship("Booking", back_populates="user")
    chat_messages = relationship("ChatMessage", back_populates="user")


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    mountain_name = Column(String, nullable=False)
    via = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    trip_type = Column(String, nullable=True)
    difficulty = Column(String, default="Pemula")  # "Pemula", "Menengah", "Sulit"
    departure_date = Column(String, nullable=False)  # format: YYYY-MM-DD
    return_date = Column(String, nullable=True)
    max_quota = Column(Integer, nullable=False)
    remaining_quota = Column(Integer, nullable=False)
    transport = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    meeting_point = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    packages = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    bookings = relationship("Booking", back_populates="trip")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    trip_id = Column(Integer, ForeignKey("trips.id"))
    status = Column(String, default="pending")  # "pending", "confirmed", "cancelled"
    meeting_point = Column(String, nullable=True)
    payment_proof_url = Column(String, nullable=True)
    package_name = Column(String, nullable=True)
    price_paid = Column(Float, nullable=True)
    cancel_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="bookings")
    trip = relationship("Trip", back_populates="bookings")
    payment_proofs = relationship("PaymentProof", back_populates="booking", cascade="all, delete-orphan")


class PaymentProof(Base):
    __tablename__ = "payment_proofs"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    file_url = Column(String)
    amount = Column(Float, nullable=True)
    status = Column(String, default="pending")  # "pending", "verified", "rejected"
    reject_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    booking = relationship("Booking", back_populates="payment_proofs")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    sender = Column(String)  # "user" atau "admin"
    message = Column(Text)
    message_type = Column(String, default="text")
    attachment_url = Column(String, nullable=True)
    reply_to_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True)
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="chat_messages")


class Mountain(Base):
    __tablename__ = "mountains"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    elevation = Column(Integer, nullable=False)  # mdpl
    difficulty = Column(String, default="Menengah")
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    gallery = Column(Text, nullable=True) # JSON array of strings
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class PrivateTripRequest(Base):
    __tablename__ = "private_trip_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    mountain_name = Column(String, nullable=False)
    participants_count = Column(Integer, nullable=False)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, contacted, confirmed, completed, cancelled
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class GalleryImage(Base):
    __tablename__ = "gallery_images"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    url = Column(String, nullable=False)
    description = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)


class MeetingPointConfig(Base):
    __tablename__ = "meeting_point_config"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class TransportConfig(Base):
    __tablename__ = "transport_config"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Guide(Base):
    __tablename__ = "guides"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    photo_url = Column(String, nullable=True)
    history = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SiteConfig(Base):
    __tablename__ = "site_config"
    id = Column(Integer, primary_key=True, index=True)
    include_exclude = Column(Text, nullable=True)
    itinerary = Column(Text, nullable=True)

