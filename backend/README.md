# Ecologistic Intelligence - Backend API

Repositori ini berisi kode sumber layanan backend untuk proyek **Ecologistic Intelligence**. Diperkuat dengan **FastAPI (Python)**, arsitektur *asynchronous* (`asyncpg` + SQLAlchemy), serta jaring pengaman otomatis (*fallback mechanism*) untuk integrasi model Machine Learning (Random Forest) dan Gemini AI Advisor.

Backend ini dirancang dengan prinsip *defensive programming* untuk memastikan stabilitas dashboard saat menangani analisis risiko logistik operasional dan emisi karbon (ESG).

---

## Tech Stack & Prerequisites

- **Framework:** FastAPI (Python 3.12+)
- **Database:** PostgreSQL (Hosted on Supabase Cloud)
- **ORM & Driver:** SQLAlchemy (AsyncSession) + `asyncpg`
- **Validation:** Pydantic v2 / Pydantic Settings
- **AI/ML Dependencies:** Scikit-learn, Joblib, Google GenAI SDK (`gemini-pro`)

---

## Cara Menjalankan Project di Lokal

Jika tim Frontend atau anggota kelompok lain ingin menjalankan service backend ini di lokal laptop mereka, ikuti langkah berikut:

### 1. Clone & Masuk ke Direktori Backend
```bash
git clone [https://github.com/username/Ecologistic_Intelligence.git](https://github.com/username/Ecologistic_Intelligence.git)
cd Ecologistic_Intelligence
```

### 2. Setup Virtual Environment & Install Dependencies
```Bash
Membuat venv
python -m venv .venv
```

# Aktivasi venv (Windows Git Bash)
```bash
source .venv/Scripts/activate
```

# Install semua library wajib
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Environment Variables (.env)

Buat file bernama .env di dalam root folder proyek, lalu isi parameter berikut (sesuaikan dengan credentials Supabase dan API Key Gemini):
Cuplikan kode

```bash
# Database Configuration (Supabase AWS Singapore Connection Pooler)
DB_HOST=aws-0-ap-southeast-1.pooler.supabase.com
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.yvagzzqbtalvozqcncog
DB_PASSWORD=your_supabase_password


# Jalur Mutlak Database untuk Engine Async SQLAlchemy
DATABASE_URL=postgresql+asyncpg://postgres.yvagzzqbtalvozqcncog:your_supabase_password@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?ssl=require&prepared_statements=false

# Gemini AI SDK Configuration
GEMINI_API_KEY=AIzaSyYourGeminiAPIKeyUtuhDiSini

```
### 4. Nyalakan Server Uvicorn
``` Bash
uvicorn backend.main:app --reload
```

Aplikasi akan otomatis berjalan di rute publik lokal: http://127.0.0.1:8000

Dokumentasi interaktif (Swagger UI) dapat diakses di: http://127.0.0.1:8000/docs

---

# Kontrak Dokumen API (Kebutuhan Frontend)

Frontend cukup merujuk pada daftar rute API di bawah ini untuk menghubungkan antarmuka UI komponen dashboard ke pangkalan data cloud.

### 1. Upload Kumpulan Data Operasional (CSV Upload)

Digunakan sebagai entry-point utama saat user mengunggah file manifest pengiriman. Sistem otomatis melakukan ekstraksi, klasifikasi risiko (ML), kalkulasi CO2, dan komparasi Gemini AI secara asynchronous / bulk.

    Endpoint: POST /api/shipments/upload-csv

    Format Payload: multipart/form-data (Key: file, Value: .csv file)

    Format Response Sukses (JSON):
```JSON

    {
      "status": "success",
      "message": "Bulk data processed successfully",
      "total_rows_processed": 142
    }
```

### 2. Modifikasi Data Manifest (Edit Shipment)

Digunakan untuk merevisi data logistik operasional lewat form dashboard. Setiap kali terjadi update, backend otomatis menghitung ulang matriks risiko dan emisi karbon global, serta menaikkan nomor versi riwayat.

    Endpoint: PUT /api/shipments/{shipment_id}/edit

    Format Payload (JSON):
```JSON

    {
      "origin_region": "Southeast Asia",
      "destination_region": "North America",
      "shipping_mode": "Air Freight",
      "weight_kg": 1500.5,
      "distance_km": 12000.0
    }
```

    Format Response Sukses (JSON):
```JSON

    {
      "status": "success",
      "message": "Shipment updated and metrics recalculated",
      "data": {
        "shipment_id": "uuid-string",
        "version": 2,
        "calculated_co2": 450.25,
        "risk_status": "High Risk"
      }
    }
```

### 3. Riwayat Audit Mutasi Data (Audit Logs Tracking)

Digunakan untuk menampilkan tabel historis perubahan record data pada dashboard dari database log temporal.

    Endpoint: GET /api/shipments/{shipment_id}/logs

    Format Response Sukses (JSON Array):
```JSON

    [
      {
        "log_id": 1,
        "shipment_id": "uuid-string",
        "action": "UPDATE",
        "changed_fields": "shipping_mode, calculated_co2",
        "version_snapshot": 2,
        "timestamp": "2026-06-04T15:30:00Z"
      }
    ]
```

### 4. Pemasok Data Utama Tabel (Get Shipment List)

Menyuplai data mentah baris pengiriman berurutan secara descending (terbaru ke lama) untuk langsung dipetakan ke dalam komponen <Table /> utama Next.js.

    Endpoint: GET /api/shipments/list

    Format Response Sukses (JSON Array):
```JSON

    [
      {
        "shipment_id": "uuid-string",
        "origin": "Southeast Asia",
        "destination": "North America",
        "risk_status": "Low Risk",
        "co2_emission": 120.4,
        "updated_at": "2026-06-04T15:30:00Z"
      }
    ]
```

### 5. Pemasok Grafik Analytics (Get Macro Metrics Dashboard)

Menyediakan agregasi data global (seperti ringkasan rasio risiko, persentase kepatuhan ESG per wilayah, rata-rata karbon) untuk langsung dipetakan ke komponen Charts & Cards Next.js.

    Endpoint: GET /api/analytics/home

    Format Response Sukses (JSON Object):
```JSON

    {
      "total_shipments": 1540,
      "average_co2_emission": 235.8,
      "risk_distribution": {
        "high_risk": 15,
        "medium_risk": 35,
        "low_risk": 50
      },
      "esg_compliance_rate": "87.5%"
    }
``` 

