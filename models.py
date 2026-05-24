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
    description = Column(Text, nullable=True)
    difficulty = Column(String, default="Pemula")  # "Pemula", "Menengah", "Sulit"
    departure_date = Column(String, nullable=False)  # format: YYYY-MM-DD
    return_date = Column(String, nullable=True)
    max_quota = Column(Integer, nullable=False)
    remaining_quota = Column(Integer, nullable=False)
    transport = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    meeting_point = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    bookings = relationship("Booking", back_populates="trip")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    trip_id = Column(Integer, ForeignKey("trips.id"))
    status = Column(String, default="pending")  # "pending", "confirmed", "cancelled"
    payment_proof_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="bookings")
    trip = relationship("Trip", back_populates="bookings")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    sender = Column(String)  # "user" atau "admin"
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="chat_messages")


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
