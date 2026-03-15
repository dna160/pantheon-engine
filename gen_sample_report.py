"""Generate a sample Human Whisperer DOCX for visual review."""
import os, sys
sys.path.insert(0, ".")
from client_whisperer.docx_builder import build_whisper_docx

MOCK_STRATEGY = {
    "prospect_name": "Budi Santoso",
    "sanity_check_summary": (
        "[TRUE_FIT] — Produk secara langsung mengatasi tekanan arus kas yang diidentifikasi "
        "dalam genom Budi. Skor decision-making tinggi (73) berarti dia membutuhkan angka "
        "konkret sebelum berkomitmen, dan produk menyediakan dashboard real-time yang memenuhi "
        "hal itu. Tidak ada sinyal NO_FIT yang terdeteksi."
    ),
    "plain_language_brief": (
        "Budi adalah manajer keuangan mid-level di perusahaan manufaktur yang sedang tumbuh "
        "cepat. Secara teknis dia sangat kompeten, tapi dia merasa kehilangan kendali karena "
        "sistemnya tidak bisa mengikuti kecepatan bisnis. Yang benar-benar dia butuhkan bukan "
        "fitur baru — dia butuh satu sumber kebenaran yang bisa dipercaya saat laporan harus "
        "masuk jam 8 pagi. Yang akan menggerakkannya adalah bukti dari perusahaan yang mirip "
        "dengannya. Yang perlu diwaspadai: dia akan terlihat setuju tapi belum tentu "
        "committed — executive flexibility-nya tinggi (68)."
    ),
    "section_0_quick_brief": {
        "engagement_hook_card": {
            "hook": "Bayangkan bisa tutup buku akhir bulan tanpa harus lembur sampai jam 11 malam.",
            "stay": "Tunjukkan satu case study dari perusahaan manufaktur dengan skala mirip — angka konkret, bukan testimonial umum.",
            "close": "Tanyakan satu pertanyaan yang memaksa dia menyebut angka kerugiannya sendiri, lalu diam.",
        },
        "key_talking_points": [
            {
                "point": "Sistem yang benar seharusnya memberi kamu waktu untuk berpikir, bukan waktu untuk input data.",
                "why_it_lands": "Conscientiousness tinggi (79) — Budi lelah membuang energinya untuk hal-hal yang harusnya otomatis.",
                "example_phrasing": "Kamu sudah terlalu baik untuk sistem yang memaksamu jadi entry clerk.",
                "genome_driver": "conscientiousness: 79, decision_making: 73",
            },
            {
                "point": "Ketidakpastian data adalah risiko bisnis yang bisa dikuantifikasi.",
                "why_it_lands": "Decision-making analitis (73) — dia sudah menghitung biaya errornya, tinggal bantu mengungkapkannya.",
                "example_phrasing": "Berapa kali bulan lalu kamu harus re-check laporan sebelum presentasi ke direksi?",
                "genome_driver": "decision_making: 73, neuroticism: 62",
            },
            {
                "point": "Ini bukan tentang software — ini tentang mengembalikan otoritasmu atas angka.",
                "why_it_lands": "Identity stake Budi ada di kompetensi profesionalnya. Sistem yang tidak bisa dipercaya mengancam identitas itu.",
                "example_phrasing": "Sebagai orang yang bertanggung jawab atas akurasi laporan, kamu seharusnya tidak perlu khawatir tentang konsistensi data.",
                "genome_driver": "pride_point: kompetensi teknis, real_fear: terlihat tidak kompeten di depan direksi",
            },
        ],
    },
    "section_1_human_snapshot": {
        "who_they_are": "Manajer keuangan 38 tahun di perusahaan manufaktur skala menengah. Pendidikan akuntansi, karir linear, dihormati karena ketelitiannya.",
        "how_they_see_themselves": "Profesional yang kompeten dan dipercaya — tapi belakangan merasa tertinggal dari perubahan yang terlalu cepat.",
        "what_they_want": "Sistem pelaporan keuangan yang lebih cepat dan akurat untuk mendukung keputusan bisnis yang makin dinamis.",
        "what_they_actually_need": "Kepercayaan diri kembali bahwa angka yang dia sajikan ke direksi bisa dipertanggungjawabkan tanpa lembur.",
        "how_they_make_decisions": "Analitis dan berbasis bukti. Butuh data perbandingan, referensi, dan waktu sebelum berkomitmen. Tidak bisa di-close dengan urgency.",
        "what_makes_them_trust": "Angka konkret dari kasus yang relevan. Orang yang mengakui keterbatasan produk sebelum dia menanyakannya.",
        "what_makes_them_shut_down": "Overselling, klaim yang tidak bisa dibuktikan, atau pertanyaan yang terasa seperti interogasi.",
        "pride_point": "Track record akurasi laporannya — tidak pernah ada temuan audit material selama 6 tahun terakhir.",
        "real_fear": "Menyajikan angka yang salah ke direksi dan kehilangan kredibilitas yang dibangun bertahun-tahun.",
        "readiness_level": 3,
        "one_thing_to_remember": "Dia sudah hampir yakin — yang dia butuhkan adalah izin untuk percaya, bukan argumen baru.",
    },
    "section_2_conversation_architecture": {
        "stage_1_arrive": {
            "stage_name": "Tiba",
            "duration_minutes": "3–5 mnt",
            "purpose": "Tunjukkan bahwa kamu sudah membaca situasinya sebelum dia berkata apa-apa.",
            "content": (
                "TALKING POINT: Akui beban kerja di balik akurasi yang dia pertahankan.\n\n"
                "CONTOH KALIMAT: 'Enam tahun tanpa temuan audit — itu bukan keberuntungan, itu disiplin. "
                "Dan saya penasaran, berapa banyak jam lembur yang ada di balik angka itu setiap bulannya?'\n\n"
                "APA YANG PERLU DIPERHATIKAN: Kalau dia langsung menjawab dengan angka spesifik, itu sinyal "
                "dia sudah menghitung biayanya sendiri. Lanjut ke Stage 3 lebih cepat."
            ),
        },
        "stage_2_common_ground": {
            "stage_name": "Kesamaan",
            "duration_minutes": "5 mnt",
            "purpose": "Normalkan pengalamannya. Buat dia merasa situasinya bukan kegagalan pribadi.",
            "content": (
                "TALKING POINT: Banyak manajer keuangan di industri manufaktur menghadapi gap yang sama "
                "antara kecepatan bisnis dan kecepatan sistem.\n\n"
                "CONTOH KALIMAT: 'Yang sering kami dengar dari orang di posisi kamu adalah — sistemnya "
                "dibangun untuk bisnis lima tahun lalu, tapi bisnisnya sudah berubah. Kamu pernah merasakan itu?'"
            ),
        },
        "stage_3_probe": [
            {
                "question": "Kalau kamu bayangkan satu bulan ke depan tanpa perubahan — situasinya seperti apa?",
                "purpose": "Membuka aspirasi dan mengukur readiness untuk berubah",
                "depth_level": 1,
                "open_follow_up": "Lanjut: 'Dan apa yang paling kamu inginkan berbeda dari situasi itu?'",
                "back_out": "Kalau dia abstrak: 'Coba lebih spesifik — proses apa yang paling menyita waktu kamu?'",
                "genome_link": "chronesthesia_capacity: 45",
            },
            {
                "question": "Berapa kali bulan lalu kamu harus re-check laporan sebelum bisa percaya datanya?",
                "purpose": "Kuantifikasi friction dan buka pintu ke real pain",
                "depth_level": 2,
                "open_follow_up": "'Dan waktu itu — berapa jam yang habis untuk verifikasi yang harusnya tidak perlu kamu lakukan?'",
                "back_out": "'Tidak perlu angka pasti — kira-kira sering atau jarang?'",
                "genome_link": "decision_making: 73",
            },
            {
                "question": "Kapan terakhir kali kamu masuk rapat direksi dan benar-benar tenang dengan angkanya?",
                "purpose": "Akses memory emosional — identifikasi gap antara standar dia dan realita saat ini",
                "depth_level": 3,
                "open_follow_up": "'Apa yang berbeda waktu itu — sistemnya, prosesnya, atau waktunya?'",
                "back_out": "'Mungkin pertanyaan yang lebih mudah — kapan kamu paling tidak tenang sebelum presentasi?'",
                "genome_link": "real_fear: terlihat tidak kompeten, pride_point: track record akurasi",
            },
            {
                "question": "Kalau ada error yang lolos dan terdeteksi saat presentasi — apa dampaknya ke kamu secara personal?",
                "purpose": "Menyentuh shame_architecture secara indirect — membuka unspoken fear",
                "depth_level": 4,
                "open_follow_up": "'Dan seberapa sering kamu memikirkan skenario itu sebelum setiap laporan?'",
                "back_out": "'Tidak perlu menjawab kalau terlalu spesifik — saya hanya ingin memahami taruhannya.'",
                "genome_link": "tom_self_awareness: 58",
            },
            {
                "question": "Apa yang sudah pernah kamu coba untuk memperbaiki situasi ini sebelumnya?",
                "purpose": "Mapping previous attempts — hindari menjual solusi yang sudah dia coba",
                "depth_level": 2,
                "open_follow_up": "'Dan kenapa menurutmu itu tidak cukup berhasil?'",
                "back_out": "'Atau mungkin belum ada yang dicoba karena belum ketemu yang pas?'",
                "genome_link": "agreeableness: 55",
            },
        ],
        "stage_4_reflect": {
            "stage_name": "Refleksi",
            "duration_minutes": "3–5 mnt",
            "purpose": "Mirror. Validasi. Ciptakan pengalaman didengar sepenuhnya.",
            "content": (
                "MIRROR STATEMENT: 'Jadi kalau saya merangkum — kamu punya sistem yang secara teknis "
                "berfungsi, tapi memaksamu investasikan terlalu banyak waktu untuk memastikan datanya bisa "
                "dipercaya. Dan yang bikin frustrasi bukan errornya — tapi ketidakpastiannya. "
                "Apakah saya menangkapnya dengan benar?'\n\n"
                "BIARKAN DIA KOREKSI. Setiap koreksi adalah data berharga tentang di mana rasa sakitnya paling dalam."
            ),
        },
        "stage_5_reframe": {
            "stage_name": "Mengubah Sudut Pandang",
            "duration_minutes": "5 mnt",
            "purpose": "Geser cara dia memahami masalah — bukan untuk memanipulasi, tapi untuk membantu dia melihat lebih jelas.",
            "content": (
                "REFRAME: Kebanyakan orang berpikir masalahnya adalah 'sistem yang lambat'. "
                "Padahal masalah sebenarnya adalah 'energi yang habis untuk memverifikasi, bukan untuk menganalisis'.\n\n"
                "CONTOH: 'Sistem yang lambat bisa diakali. Tapi sistem yang membuat kamu ragu pada datanya sendiri "
                "— itu yang menguras kamu. Pertanyaan yang lebih penting bukan seberapa cepat sistemnya, "
                "tapi seberapa banyak kepercayaan yang kamu bisa taruh di angka yang keluar dari sana.'"
            ),
        },
        "stage_6_framework": {
            "stage_name": "Kerangka Kerja",
            "duration_minutes": "5–10 mnt",
            "purpose": "Tunjukkan jalan ke depan tanpa meminta komitmen.",
            "content": (
                "Step 1: DIAGNOSIS — Petakan di mana data hilang atau tidak konsisten.\n"
                "WHY IT MATTERS: Kamu tidak bisa memperbaiki yang tidak kamu ukur.\n"
                "WHAT IT FEELS LIKE: Seperti akhirnya punya peta setelah lama berjalan di gelap.\n\n"
                "Step 2: SATU SUMBER KEBENARAN — Konsolidasi data ke satu sistem yang bisa diaudit.\n"
                "WHY IT MATTERS: Eliminasi pekerjaan double-check yang menguras waktu.\n"
                "WHAT IT FEELS LIKE: Seperti bisa bernafas lagi sebelum deadline.\n\n"
                "Step 3: OTOMASI LAPORAN RUTIN — Biarkan sistem membuat laporan standar.\n"
                "WHY IT MATTERS: Waktumu kembali untuk analisis, bukan administrasi.\n"
                "WHAT IT FEELS LIKE: Seperti akhirnya mengerjakan pekerjaan yang sebenarnya kamu dibayar untuk itu.\n\n"
                "Step 4: DASHBOARD EKSEKUTIF REAL-TIME — Direksi bisa lihat angka kapan saja.\n"
                "WHY IT MATTERS: Kredibilitasmu naik karena kamu proaktif, bukan reaktif.\n"
                "WHAT IT FEELS LIKE: Masuk rapat dengan tenang, bukan khawatir ada yang ketinggalan."
            ),
        },
        "stage_7_cta": {
            "stage_name": "Panggilan Bertindak",
            "duration_minutes": "3–5 mnt",
            "purpose": "Satu langkah jelas, jujur, dan spesifik. Bukan pitch. Sebuah pintu.",
            "content": (
                "CTA (Readiness 3): 'Ada satu hal yang ingin saya tunjukkan — bukan demo produk, tapi hasilnya. "
                "Perusahaan dengan profil serupa mengurangi waktu close bulan-an dari 5 hari ke 2 hari. "
                "Angkanya ada, kalau kamu mau lihat.'\n\n"
                "FRAMING: Dia tidak harus memutuskan apa-apa sekarang. Kamu hanya meminta izin untuk memberi "
                "data yang dia butuhkan untuk membuat keputusan yang baik."
            ),
        },
    },
    "section_3_signal_reading": {
        "open_signals": [
            "Dia mulai menggunakan 'kita' bukan 'saya' saat bicara tentang solusinya — identity_fusion (52) artinya dia sudah mentally include kamu dalam prosesnya.",
            "Dia spontan menyebut angka spesifik (jam lembur, jumlah error) tanpa diminta — conscientiousness tinggi (79) butuh presisi, dan dia percaya cukup untuk berbagi.",
            "Dia tiba-tiba bertanya tentang timeline implementasi — sinyal dia sudah mentally moving forward.",
            "Dia mengajukan pertanyaan teknis spesifik tentang integrasi sistem — dia sedang mengerjakan hambatan praktis.",
            "Suaranya melambat dan dia berhenti sebelum menjawab — executive flexibility tinggi (68) artinya dia sedang mengolah sesuatu yang benar-benar relevan.",
        ],
        "close_signals": [
            "Jawaban menjadi lebih pendek dan lebih formal — executive flexibility tinggi (68) artinya dia masih terlihat sopan tapi sudah tidak engaged.",
            "Dia redirect ke fakta teknis ketika kamu tanya tentang perasaan — cara dia menjaga jarak emosional.",
            "Dia menyebut 'budget cycle' atau 'perlu approval atasan' terlalu awal — ini defleksi, bukan keberatan nyata.",
            "Dia check handphone atau jam — decision_making analitis (73) artinya dia sudah kalkulasi dan hasilnya belum memuaskan.",
            "Kalimatnya mulai dengan 'Memang bagus, tapi...' lebih dari dua kali berturut-turut.",
        ],
        "back_out_scripts": {
            "b1": "Oke, kita skip dulu. Boleh saya tanya sesuatu yang berbeda — lebih ke sisi proses, bukan angkanya?",
            "b2": "Wajar — banyak yang prefer tidak membahas detail itu di awal. Mungkin lebih useful kalau saya share apa yang biasanya terjadi di situasi serupa, dan kamu bisa bilang mana yang relevan.",
            "b3": "Maaf, sepertinya saya terlalu jauh. Balik ke tadi — kamu bilang proses close bulan-an yang paling makan waktu. Bisa ceritakan lebih detail?",
            "b4": "Saya dengar kamu. Tidak akan kita paksa ke sana. Dari waktu yang sudah kamu berikan hari ini, saya ingin pastikan kamu pulang dengan setidaknya satu hal yang berguna — boleh?",
        },
    },
    "section_4_plain_language_guide": [
        {
            "technical": "Decision-making score 73 — upper analytical range; expects evidence-based case with quantifiable outcomes before commitment.",
            "plain": "Budi tidak bisa di-close pakai energy dan visi aja. Dia butuh angka konkret dari industri yang sama. Kalau kamu skip ini, dia bakal bilang 'menarik, nanti follow up' dan tidak ada yang terjadi.",
            "analogy": "Seperti auditor yang diminta menandatangani laporan tanpa melihat lampirannya — bukan karena tidak percaya, tapi karena itu memang bukan cara dia bekerja.",
            "one_line": "Tunjukkan angkanya dulu, baru dia bisa bilang ya.",
        },
        {
            "technical": "Executive flexibility score 68 — professional mask is active; inner state may diverge significantly from presented demeanor.",
            "plain": "Budi bisa terlihat antusias padahal sebetulnya masih ragu. Senyum dan anggukan bukan tanda dia sudah yakin — perhatikan momen off-script: pertanyaan yang dia lempar sambil lalu, atau komentar sebelum dia sempat menyaringnya.",
            "analogy": "Seperti poker player yang bagus — wajahnya flat, tapi kalau kamu tahu harus lihat ke mana, ada tell-nya.",
            "one_line": "Tenang di luar belum tentu yakin di dalam — perhatikan momen candid-nya.",
        },
        {
            "technical": "Identity stake tied to professional credibility; shame_architecture centers on public error in front of leadership.",
            "plain": "Ketakutan terbesar Budi bukan soal sistem yang lambat — tapi soal terlihat tidak kompeten di depan direksi. Bingkailah solusinya sebagai pelindung kredibilitasnya, bukan perbaikan untuk kekurangannya.",
            "analogy": "Seperti dokter yang butuh alat diagnostik yang lebih baik — bukan karena dia tidak kompeten, tapi karena alat yang baik membuat kompetensinya terlihat.",
            "one_line": "Jual perlindungan reputasi, bukan perbaikan sistem.",
        },
    ],
    "section_5_product_fit": {
        "fit_status": "TRUE_FIT",
        "fit_rationale": "Produk secara langsung mengatasi root cause yang teridentifikasi: ketidakpastian data yang memaksa verifikasi manual berulang. Dashboard real-time dan audit trail menjawab kebutuhan decision_making analitis Budi.",
        "pain_it_addresses": "Waktu yang terbuang untuk verifikasi manual dan ketidaktenangan sebelum presentasi direksi akibat data yang tidak bisa sepenuhnya dipercaya.",
        "how_to_introduce_it": "Ada satu hal yang ingin saya tunjukkan — bukan produknya, tapi hasilnya. Perusahaan dengan profil serupa mengurangi waktu close bulan-an dari 5 hari ke 2 hari. Angkanya ada, kalau kamu mau lihat.",
        "honest_limitation": "Implementasi awal membutuhkan 6–8 minggu untuk migrasi data historis dan pelatihan tim. Ada learning curve yang perlu diantisipasi selama periode itu.",
        "what_happens_next": "Kirim satu case study manufaktur yang paling relevan dengan satu paragraf eksekutif summary — bukan brochure, tapi angka yang bisa dia verifikasi sendiri.",
        "what_else_they_need": None,
        "honest_redirect": None,
    },
    "section_6_post_conversation": {
        "within_24_hours": "Kirim case study yang dijanjikan via email — satu halaman, dengan angka spesifik. Tambahkan satu kalimat yang mengakui keterbatasan implementasi secara proaktif.",
        "what_to_note": "Catat apakah dia menyebut angka spesifik selama percakapan (tanda readiness lebih tinggi dari perkiraan). Catat juga apakah dia defleksi ke 'approval atasan' — kalau ya, cari tahu siapa pengambil keputusan sebenarnya.",
        "what_to_update": "Konfirmasi skor readiness dari 3 ke 4 jika dia bertanya tentang timeline. Update catatan tentang previous_attempts jika ada yang baru terungkap.",
        "next_conversation": "Follow-up dalam 5 hari kerja — bukan untuk close, tapi untuk tanya satu pertanyaan: 'Ada yang ingin kamu klarifikasi dari case study-nya?' Satu pertanyaan itu membuka pintu ke conversation berikutnya.",
    },
}

MOCK_SIMULATED_LIFE = """
PANTHEON LIFE BLUEPRINT — Budi Santoso
Generated: 2026-03-14  Cohort: Urban Professional Jakarta

GENOME SCORES (v3 — 18 traits)
Big Five:
  openness: 52  conscientiousness: 79  extraversion: 41
  agreeableness: 55  neuroticism: 62
Behavioral:
  decision_making: 73  emotional_expression: 38
  conflict_behavior: 34  influence_susceptibility: 44
  communication_style: 61  brand_relationship: 55
Cognitive Architecture (v3):
  identity_fusion: 52  chronesthesia_capacity: 45
  tom_self_awareness: 58  tom_social_modeling: 63
  executive_flexibility: 68

LAYER 1 — SURVIVAL: Financial pressure moderate. Primary anxiety: job security during digitalization push.
LAYER 2 — IDENTITY: Self-concept = the competent one. Pride: 6yr audit clean record. Shame: public error in front of leadership.
LAYER 3 — SOCIAL: Formal in professional settings. Conflict-avoidant — absorbs friction rather than surfaces it.
LAYER 4 — LEGACY (chronesthesia 45 — 1-2yr horizon): Wants to be seen as the person who modernized the finance function.
LAYER 5 — TRANSCENDENCE: Work as craft. Derives meaning from doing the job correctly, not just done.
""".strip()


os.makedirs("D:/Claude Home/venus-app/reports", exist_ok=True)
out = build_whisper_docx(
    prospect_name="Budi Santoso",
    strategy=MOCK_STRATEGY,
    simulated_life=MOCK_SIMULATED_LIFE,
    linkedin_url="https://linkedin.com/in/budisantoso",
    instagram_url="https://instagram.com/budisantoso",
)
path = "D:/Claude Home/venus-app/reports/BudiSantoso_Sample_20260314.docx"
with open(path, "wb") as f:
    f.write(out)
print(f"OK — {len(out):,} bytes written to {path}")
