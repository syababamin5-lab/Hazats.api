"""
Script migrasi database - tambahkan kolom baru ke tabel yang sudah ada.
Jalankan: python migrate.py
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from database import engine
from sqlalchemy import text

migrations = [
    # Tabel users - kolom baru
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'user'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",

    # Tabel trips - kolom baru
    "ALTER TABLE trips ADD COLUMN IF NOT EXISTS difficulty VARCHAR DEFAULT 'Pemula'",
    "ALTER TABLE trips ADD COLUMN IF NOT EXISTS image_url VARCHAR",
    "ALTER TABLE trips ADD COLUMN IF NOT EXISTS return_date VARCHAR",

    # Tabel bookings - kolom baru
    "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_proof_url VARCHAR",

    # Tabel baru: gallery_images
    """
    CREATE TABLE IF NOT EXISTS gallery_images (
        id SERIAL PRIMARY KEY,
        filename VARCHAR NOT NULL,
        url VARCHAR NOT NULL,
        description VARCHAR,
        uploaded_at TIMESTAMP DEFAULT NOW()
    )
    """,
]

def run_migrations():
    with engine.connect() as conn:
        for i, sql in enumerate(migrations, 1):
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"[OK] Migrasi {i}/{len(migrations)} berhasil")
            except Exception as e:
                print(f"[SKIP] Migrasi {i} dilewati: {e}")
    print("\n[DONE] Semua migrasi selesai!")

if __name__ == "__main__":
    run_migrations()
