import json
from database import SessionLocal
from models import Mountain

db = SessionLocal()

mountains_data = [
    {
        "name": "Gunung Gede",
        "location": "Cianjur, Jawa Barat",
        "elevation": 2958,
        "difficulty": "Menengah",
        "image_url": "https://images.unsplash.com/photo-1549887552-cb1071d3e5ca?w=800&q=80",
        "description": "Salah satu gunung paling ikonik di Jawa Barat. Pemandangan Surya Kencana yang dihiasi edelweis menjadi primadona bagi para pendaki. Untuk Tektok, via Cibodas membutuhkan waktu sekitar 8-10 jam PP. Jika Camp, direkomendasikan menginap 2D1N di Surya Kencana untuk menikmati lautan bintang dan matahari terbit yang magis. Jalur via Gunung Putri lebih curam namun lebih cepat, sangat cocok bagi pencari tantangan ekstra."
    },
    {
        "name": "Gunung Pangrango",
        "location": "Cianjur, Jawa Barat",
        "elevation": 3019,
        "difficulty": "Menengah",
        "image_url": "https://images.unsplash.com/photo-1596788062973-77be95804245?w=800&q=80",
        "description": "Menjulang tinggi di sebelah Gunung Gede, Pangrango menawarkan ketenangan hutan tropis dan lembah Mandalawangi yang eksotis. Pendakian tektok membutuhkan waktu 10-12 jam, sangat direkomendasikan bagi yang sudah berpengalaman. Untuk Anda yang ingin menikmati harmoni alam, ambil paket Camp 2D1N dan nikmati kabut pagi menyelimuti Mandalawangi."
    },
    {
        "name": "Gunung Ciremai",
        "location": "Kuningan, Jawa Barat",
        "elevation": 3078,
        "difficulty": "Ekstrem",
        "image_url": "https://images.unsplash.com/photo-1627883441618-c2b534cf5f95?w=800&q=80",
        "description": "Atap Jawa Barat! Gunung Ciremai menyajikan jalur pendakian yang menguji fisik dan mental. Via Apuy atau Palutungan menjadi favorit. Pendakian tektok sangat menantang (12-14 jam), hanya untuk fast packer sejati. Paket Camp 2D1N atau 3D2N di Pos Goa Walet adalah pilihan terbaik untuk mempersiapkan summit attack menuju kawah kembar yang menakjubkan."
    },
    {
        "name": "Gunung Cikuray",
        "location": "Garut, Jawa Barat",
        "elevation": 2821,
        "difficulty": "Ekstrem",
        "image_url": "https://images.unsplash.com/photo-1563204944-771bebf039a0?w=800&q=80",
        "description": "Dikenal dengan trek 'lutut ketemu dada', Cikuray menawarkan samudera awan terbaik di Garut! Tanpa ampun dari titik awal hingga puncak. Waktu tempuh tektok via Pemancar sekitar 8-10 jam PP. Untuk menikmati sunrise berlatar lautan awan yang tak terlupakan, paket Camp 2D1N adalah jawaban mutlak bagi Anda para penikmat lelah."
    },
    {
        "name": "Gunung Papandayan",
        "location": "Garut, Jawa Barat",
        "elevation": 2665,
        "difficulty": "Pemula",
        "image_url": "https://images.unsplash.com/photo-1610996152865-c335e38d4a94?w=800&q=80",
        "description": "Surga bagi pendaki pemula! Menyajikan pesona kawah aktif, Hutan Mati yang instagenic, hingga padang Edelweis di Tegal Alun. Tektok bisa diselesaikan dalam 5-7 jam dengan sangat santai. Namun, sensasi camping di Pondok Saladah dengan udara sejuk Garut adalah keharusan untuk pengalaman pertama mendaki yang sempurna."
    },
    {
        "name": "Gunung Slamet",
        "location": "Jawa Tengah",
        "elevation": 3428,
        "difficulty": "Ekstrem",
        "image_url": "https://images.unsplash.com/photo-1616422896502-3c2d6f5f3e9c?w=800&q=80",
        "description": "Atap Jawa Tengah yang gagah dan mengintimidasi! Menawarkan jalur panjang nan epik via Bambangan. Tektok tidak direkomendasikan kecuali Anda seorang atlet trail run (14-18 jam). Ikuti paket Camp 3D2N kami untuk aklimatisasi sempurna, menembus batas diri, dan berdiri di bibir kawah raksasa yang masih mengepulkan asap belerang."
    },
    {
        "name": "Gunung Lawu",
        "location": "Karanganyar, Jawa Tengah",
        "elevation": 3265,
        "difficulty": "Menengah",
        "image_url": "https://images.unsplash.com/photo-1578339846383-9b578c772c5b?w=800&q=80",
        "description": "Gunung spiritual dengan warisan budaya dan kuliner legendaris 'Mbok Yem' di puncaknya. Waktu tempuh tektok via Cemoro Sewu (batu tertata) sekitar 9-11 jam. Namun, kami sangat merekomendasikan Camp 2D1N agar Anda bisa menikmati secangkir teh hangat di warung tertinggi di Indonesia sambil menanti fajar menyingsing di ufuk timur."
    },
    {
        "name": "Gunung Merbabu",
        "location": "Boyolali, Jawa Tengah",
        "elevation": 3142,
        "difficulty": "Menengah",
        "image_url": "https://images.unsplash.com/photo-1612351239563-31fba8933b9e?w=800&q=80",
        "description": "Kecantikan tiada tara! Sabana membentang luas di via Selo membuat Merbabu selalu dirindukan. Pendakian tektok membutuhkan 8-10 jam. Tetapi, berkemah di Sabana 2 adalah sebuah kemewahan; bangun tidur disambut kemegahan Gunung Merapi tepat di hadapan tenda Anda. Momen epik yang wajib ada di feed Instagram Anda!"
    },
    {
        "name": "Gunung Sindoro",
        "location": "Wonosobo, Jawa Tengah",
        "elevation": 3136,
        "difficulty": "Menengah",
        "image_url": "https://images.unsplash.com/photo-1588662998393-2771239c4383?w=800&q=80",
        "description": "Kembaran Sumbing dengan trek bebatuan vulkanik yang menantang. Tektok via Kledung (menggunakan ojek basecamp) memakan waktu 7-9 jam. Paket Camp kami akan membawa Anda bermalam di batas vegetasi, bersiap untuk summit attack pendek menikmati sunrise keemasan dan kawah lapang Sindoro yang megah."
    },
    {
        "name": "Gunung Sumbing",
        "location": "Wonosobo, Jawa Tengah",
        "elevation": 3371,
        "difficulty": "Ekstrem",
        "image_url": "https://images.unsplash.com/photo-1614769062322-2a4bdfa4ed02?w=800&q=80",
        "description": "Terbesar kedua di Jawa Tengah. Jalurnya seolah tak pernah ada ujungnya! Via Garung sangat populer. Tektok sangat menguras tenaga (10-12 jam). Dengan paket Camp 2D1N dari Hazats Adventure, Anda akan kami pandu melewati lautan debu dan tanjakan PHP dengan aman, untuk meraih Puncak Buntu atau Rajawali dengan penuh kebanggaan."
    },
    {
        "name": "Gunung Prau",
        "location": "Dieng, Jawa Tengah",
        "elevation": 2590,
        "difficulty": "Pemula",
        "image_url": "https://images.unsplash.com/photo-1596707328905-24892c90c793?w=800&q=80",
        "description": "Golden Sunrise terindah se-Asia Tenggara! Sangat ramah pemula dengan durasi pendakian via Patak Banteng hanya 2-3 jam saja. Sangat cocok untuk tektok santai. Jika memilih Camp, Anda akan bermalam di hamparan sabana bukit teletubbies berbintang, lalu bangun pagi disambut jajaran lima gunung sekaligus!"
    },
    {
        "name": "Gunung Argopuro",
        "location": "Probolinggo, Jawa Timur",
        "elevation": 3088,
        "difficulty": "Ekstrem",
        "image_url": "https://images.unsplash.com/photo-1568294711126-df820aeb9531?w=800&q=80",
        "description": "Trek terpanjang di Pulau Jawa! Menawarkan nuansa mistis Cikasur dan keindahan Danau Taman Hidup. Tidak memungkinkan untuk tektok. Hazats Adventure menyediakan paket premium 4D3N atau 5D4N untuk mengeskplorasi keeksotisan Argopuro tanpa beban berat, ditemani porter profesional dan hidangan istimewa di setiap camp."
    },
    {
        "name": "Gunung Agung",
        "location": "Karangasem, Bali",
        "elevation": 3142,
        "difficulty": "Ekstrem",
        "image_url": "https://images.unsplash.com/photo-1536647180183-f5424df23351?w=800&q=80",
        "description": "Gunung suci tertinggi di Bali. Jalur yang didominasi batuan vulkanik tajam ini menuntut fokus tinggi. Pendakian malam hari (tektok) via Pasar Agung memakan waktu 8-10 jam PP untuk mengejar sunrise spektakuler dengan latar belakang Gunung Rinjani di kejauhan. Sensasi pendakian spiritual yang memacu adrenalin!"
    },
    {
        "name": "Gunung Rinjani",
        "location": "Lombok, NTB",
        "elevation": 3726,
        "difficulty": "Ekstrem",
        "image_url": "https://images.unsplash.com/photo-1591851213054-05bbaf0914de?w=800&q=80",
        "description": "Salah satu gunung terindah di dunia! Rinjani menjanjikan paket komplit: Sabana Sembalun, Danau Segara Anak, dan pemandian air panas alami. Ekspedisi ini wajib Camp (3D2N atau 4D3N). Bersama Hazats, kami siapkan setup kemah VIP di Pelawangan dengan layanan bak hotel bintang 5 di atas awan, menanti summit attack ke 3726 mdpl."
    },
    {
        "name": "Gunung Kerinci",
        "location": "Jambi, Sumatera",
        "elevation": 3805,
        "difficulty": "Ekstrem",
        "image_url": "https://images.unsplash.com/photo-1552554766-3d237190f898?w=800&q=80",
        "description": "Atap Sumatera dan gunung berapi tertinggi di Indonesia! Jalur tanah basah dan terowongan akar pohon menjadi ciri khasnya. Tektok tidak diperbolehkan. Bergabunglah dalam ekspedisi eksklusif 3D2N Hazats Adventure; taklukkan Puncak Indrapura dan buktikan ketangguhan Anda di hadapan rimba Sumatera."
    },
    {
        "name": "Gunung Sunan Ibu",
        "location": "Bandung, Jawa Barat",
        "elevation": 2240,
        "difficulty": "Pemula",
        "image_url": "https://images.unsplash.com/photo-1571406981882-628d086cbdb8?w=800&q=80",
        "description": "Berada di kawasan Kawah Putih, spot ini merupakan hidden gem untuk menyaksikan keindahan matahari terbit menyinari danau belerang dari ketinggian. Sangat mudah, cukup tektok santai 30-45 menit dari area parkir. Pilihan tepat bagi rombongan keluarga yang menginginkan foto estetik dengan usaha minimal!"
    },
    {
        "name": "Gunung Sunan Rama",
        "location": "Bandung, Jawa Barat",
        "elevation": 2300,
        "difficulty": "Pemula",
        "image_url": "https://images.unsplash.com/photo-1518098268026-4e89f1a2cd8e?w=800&q=80",
        "description": "Berdekatan dengan Gunung Patuha, Sunan Rama menyuguhkan lanskap hutan pinus dan kesejukan Ciwidey yang asri. Pendakian tektok (2-3 jam) sangat direkomendasikan untuk pelarian akhir pekan dari penatnya kota. Rasakan healing instan yang menyegarkan bersama pemandu berpengalaman kami."
    },
    {
        "name": "Gunung Sanggar",
        "location": "Bandung, Jawa Barat",
        "elevation": 2500,
        "difficulty": "Menengah",
        "image_url": "https://images.unsplash.com/photo-1469521669194-babb45599def?w=800&q=80",
        "description": "Puncak eksotis yang sering disebut-sebut sebagai atap Bandung! Dikelilingi rimbunnya hutan tropis Jawa Barat yang mistis namun menakjubkan. Jalurnya cocok untuk latihan endurance (tektok 5-7 jam). Jika Camp, siapkan perlengkapan ekstra karena suhu malam harinya akan menguji nyali Anda!"
    },
    {
        "name": "Gunung Burangrang",
        "location": "Bandung, Jawa Barat",
        "elevation": 2050,
        "difficulty": "Pemula",
        "image_url": "https://images.unsplash.com/photo-1506148386345-4df3372c0c7a?w=800&q=80",
        "description": "Berada di sisa kawah raksasa Sunda Purba, Burangrang menyuguhkan jalur akar dan tanjakan tanah yang khas. Tektok via Legok Haji bisa diselesaikan dalam 4-6 jam PP. Menawarkan pemandangan Situ Lembang dari puncaknya. Pendakian tektok sehari penuh yang sempurna untuk mengisi akhir pekan!"
    },
    {
        "name": "Gunung Malabar",
        "location": "Bandung, Jawa Barat",
        "elevation": 2343,
        "difficulty": "Menengah",
        "image_url": "https://images.unsplash.com/photo-1582967160759-4d3ee12431fa?w=800&q=80",
        "description": "Gugusan pegunungan bersejarah di selatan Bandung! Malabar terkenal dengan Puncak Besar, Puncak Haruman, dan Puncak Puntang. Jalurnya lebat, basah, dan menantang (tektok 7-9 jam). Rasakan sensasi ekspedisi menembus hutan tropis perawan layaknya petualang sejati. Tidak begitu direkomendasikan untuk camp tanpa pemandu ahli."
    },
    {
        "name": "Upas Hill",
        "location": "Bandung, Jawa Barat",
        "elevation": 2200,
        "difficulty": "Pemula",
        "image_url": "https://images.unsplash.com/photo-1518331647614-7a1f04cd34bc?w=800&q=80",
        "description": "Bukit Upas terletak di area Gunung Tangkuban Perahu. Menawarkan padang sabana yang unik dengan pemandangan langsung ke kawah vulkanik yang mengepul! Pendakian tektok sangat mudah, sering dijadikan area rekreasi. Sangat cocok bagi Anda yang ingin piknik gunung dan ngopi santai di tengah kesejukan Lembang."
    },
    {
        "name": "Artapela",
        "location": "Bandung, Jawa Barat",
        "elevation": 2194,
        "difficulty": "Pemula",
        "image_url": "https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=800&q=80",
        "description": "Gunung mungil di Pangalengan dengan Puncak Sulibra-nya yang ikonik. Medannya di dominasi perkebunan dan sabana luas nan hijau. Tektok hanya 3-4 jam PP. Tapi tunggu dulu, rasakan magisnya mendirikan tenda (Camp) di rerumputan hijaunya; sangat romantis, instagramable, dan sangat family-friendly!"
    },
    {
        "name": "Gunung Tampomas",
        "location": "Sumedang, Jawa Barat",
        "elevation": 1684,
        "difficulty": "Pemula",
        "image_url": "https://images.unsplash.com/photo-1501555088652-021faa106b9b?w=800&q=80",
        "description": "Bintangnya kota Sumedang! Menyajikan jalur bebatuan (Sanghyang Taraje) dan lubang-lubang asap belerang aktif di puncaknya. Tektok membutuhkan waktu 5-7 jam PP. Sangat direkomendasikan untuk uji fisik ringan (tektok) di akhir pekan, sembari menikmati hangatnya tahu Sumedang sepulang dari pendakian."
    }
]

added = 0
for data in mountains_data:
    existing = db.query(Mountain).filter(Mountain.name == data['name']).first()
    if not existing:
        m = Mountain(**data)
        db.add(m)
        added += 1
    else:
        existing.description = data['description']
        existing.difficulty = data['difficulty']
        existing.elevation = data['elevation']
        existing.image_url = data['image_url']
        existing.location = data['location']

db.commit()
print(f"Berhasil memproses {len(mountains_data)} gunung. Ditambahkan: {added}")
