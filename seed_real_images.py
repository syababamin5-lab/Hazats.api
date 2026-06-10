import json
import wikipedia
import re
from database import SessionLocal
from models import Mountain

db = SessionLocal()
wikipedia.set_lang("id")
wikipedia.set_user_agent("HazatsAdventureBot/1.0 (https://hazats.com; info@hazats.com)")

def is_good_image(url: str) -> bool:
    url_lower = url.lower()
    if not (url_lower.endswith('.jpg') or url_lower.endswith('.jpeg') or url_lower.endswith('.png')):
        return False
    bad_keywords = ['icon', 'logo', 'map', 'flag', 'locator', 'peta', 'simbol', 'commons-logo', 'wikiquote', 'wikivoyage', 'disambig']
    for bad in bad_keywords:
        if bad in url_lower:
            return False
    return True

mountains = db.query(Mountain).all()

for m in mountains:
    print(f"Mengambil foto asli untuk: {m.name}")
    try:
        page = wikipedia.page(m.name)
        images = page.images
        good_images = [img for img in images if is_good_image(img)]
        
        # Coba juga wikipedia bahasa Inggris jika fotonya kurang dari 5
        if len(good_images) < 5:
            wikipedia.set_lang("en")
            try:
                en_page = wikipedia.page(m.name)
                en_images = [img for img in en_page.images if is_good_image(img)]
                # Merge unik
                for img in en_images:
                    if img not in good_images:
                        good_images.append(img)
            except:
                pass
            wikipedia.set_lang("id")

        if len(good_images) == 0:
            print(f"Tidak ada foto ditemukan untuk {m.name}. Menggunakan fallback.")
            good_images = [m.image_url] * 5
        
        # Ambil maksimal 6 foto, jadikan foto pertama sebagai image_url
        gallery = good_images[:6]
        
        # Pastikan minimal 5 foto (duplikasi jika kurang, untuk memenuhi syarat modal slider)
        while len(gallery) < 5:
            gallery.append(gallery[0])

        m.image_url = gallery[0]
        m.gallery = json.dumps(gallery)
        print(f"Berhasil mendapatkan {len(gallery)} foto untuk {m.name}")
        
    except wikipedia.exceptions.DisambiguationError as e:
        print(f"Disambiguasi untuk {m.name}, menggunakan foto fallback.")
        m.gallery = json.dumps([m.image_url] * 5)
    except wikipedia.exceptions.PageError:
        print(f"Halaman tidak ditemukan untuk {m.name}, menggunakan foto fallback.")
        m.gallery = json.dumps([m.image_url] * 5)
    except Exception as e:
        print(f"Error {m.name}: {e}")
        m.gallery = json.dumps([m.image_url] * 5)

db.commit()
print("Selesai memperbarui galeri semua gunung!")
