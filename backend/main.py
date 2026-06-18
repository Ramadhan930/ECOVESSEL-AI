import os
import uvicorn
import uuid
from datetime import datetime
from fastapi import FastAPI, Request, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from backend.database.connection import db  # Driver Firebase Firestore Cloud Kita
import csv
import io

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=====================================================================")
    print("=== SYSTEM: [FIREBASE CODENAME] Backend Live & Terhubung ke NoSQL ===")
    print("=====================================================================")
    yield
    print("=== SYSTEM: Koneksi Firebase Cloud Firestore Diputus ===")

app = FastAPI(
    title="EcoLogistics Intelligence API — Firebase Final Edition",
    description="Backend Engine NoSQL Firestore dengan Fitur Multi-Destination & Audit Trail Snapshot",
    version="2.5.0",
    lifespan=lifespan
)

@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    if request.method == "POST" and "multipart/form-data" in request.headers.get("content-type", ""):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 2 * 1024 * 1024:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "status": "error",
                    "message": "Payload Too Large",
                    "detail": "Eror: Ukuran berkas terlalu besar! Maksimal hanya boleh 2MB."
                }
            )
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══ 1. UPLOAD CSV DENGAN DISTANCE THRESHOLD & MULTI-DESTINATION FIREBASE ════
@app.post("/api/shipments/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Menerima manifest maritim, memproses rute pelayaran heuristik, dan menyimpan ke Firestore NoSQL"""
    try:
        contents = await file.read()
        # Menggunakan io.StringIO dan csv.DictReader sebagai pengganti Pandas
        csv_file = io.StringIO(contents.decode('utf-8'))
        reader = csv.DictReader(csv_file)
        
        total_rows = 0
        
        for row in reader:
            total_rows += 1
            shipment_id = str(uuid.uuid4())
            
            csv_region = str(row.get('region', 'Southeast Asia')).strip()
            csv_mode = str(row.get('shipping_mode', 'Container Vessel')).strip()
            csv_days = int(row.get('scheduled_shipment_days', 10))
            csv_category = str(row.get('product_category', 'General Cargo')).strip()
            csv_vessel = str(row.get('vessel_name', 'MV Unknown Echo')).strip()
            
            # 🔥 SINKRON: Baca kolom destination langsung dari CSV baru kamu
            csv_destination = str(row.get('destination', 'North America')).strip()
            
            simulated_distance_km = csv_days * 580.0
            distance_threshold_km = 500.0
            
            # Formulasi Bobot Pendukung ESG Berdasarkan Hari Manifes Pelayaran
            simulated_weight_kg = float(csv_days * 180.5)
            
            if simulated_distance_km > distance_threshold_km:
                routing_type = "Hybrid Multi-Modal (Sea + Road Connection)"
                nearest_origin_port = f"Port of {csv_region.split(' ')[0]} Hub"
                nearest_dest_port = f"Port of {csv_destination.split(' ')[0]} Terminal"
                
                land_emissions = float(simulated_distance_km * 0.12 * 0.04)
                sea_emissions = float(simulated_distance_km * 0.88 * 0.022)
                calculated_co2 = round(land_emissions + sea_emissions, 2)
            else:
                routing_type = "Direct Single-Modal (Local Sea Channel)"
                nearest_origin_port = "Direct Coastal Terminal"
                nearest_dest_port = "Direct Regional Drop"
                calculated_co2 = round(float(simulated_distance_km * 0.022), 2)
                
            if csv_mode.lower() == "lng tanker":
                calculated_co2 = round(float(calculated_co2 * 1.2), 2)

            if csv_days <= 5 or csv_category.lower() in ["chemicals", "gases"]:
                simulated_risk = "High Risk"
            elif 5 < csv_days <= 10:
                simulated_risk = "Medium Risk"
            else:
                simulated_risk = "Low Risk"

            payload = {
                "shipment_id": shipment_id,
                "origin": csv_region,
                "destination": csv_destination,  
                "shipping_mode": csv_mode,
                "vessel_name": csv_vessel,
                "routing_architecture": routing_type,
                "nearest_origin_port": nearest_origin_port,
                "nearest_destination_port": nearest_dest_port,
                "scheduled_shipment_days": csv_days,
                "estimated_distance_km": simulated_distance_km,
                "weight_kg": simulated_weight_kg, 
                "product_category": csv_category,
                "co2_emission": calculated_co2,
                "risk_status": simulated_risk,
                "version": 1,
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
            
            db.collection("shipments").document(shipment_id).set(payload)
            
        return {
            "status": "success",
            "message": "Bulk data processed successfully",
            "total_rows_processed": total_rows
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Gagal memproses manifest maritim: {str(e)}"})

# ═══ 2. MODIFIKASI DATA MANIFEST (EDIT SHIPMENT FIREBASE LOGIC) ═══════════════
@app.post("/api/shipments/{shipment_id}/edit")  
@app.put("/api/shipments/{shipment_id}/edit")
async def edit_shipment(shipment_id: str, payload: dict):
    try:
        doc_ref = db.collection("shipments").document(shipment_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Shipment ID tidak ditemukan"})
            
        current_data = doc.to_dict()
        new_version = current_data.get("version", 1) + 1
        
        # 🔥 FIX SAKRAL: Ambil data origin/destination dari payload frontend, sinkronkan key-nya
        updated_origin = payload.get("origin_region", current_data.get("origin"))
        updated_destination = payload.get("destination_region", current_data.get("destination"))
        updated_mode = payload.get("shipping_mode", current_data.get("shipping_mode"))
        
        # 🔥 FIX LOGIKA EMISI: Gunakan nilai database lama (current_data) jika frontend tidak mengirim data berat/jarak
        updated_weight = float(payload.get("weight_kg", current_data.get("weight_kg", 1500.0)))
        updated_distance = float(payload.get("distance_km", current_data.get("estimated_distance_km", 4000.0)))
        
        # Rekalkulator emisi taktis dari data dinamis asli
        new_co2 = round((updated_distance * 0.025) + (updated_weight * 0.006), 2)
        new_risk = payload.get("risk_status", current_data.get("risk_status", "Medium Risk"))
        
        updated_payload = {
            "origin": updated_origin,
            "destination": updated_destination,
            "shipping_mode": updated_mode,
            "version": new_version,
            "co2_emission": new_co2,
            "risk_status": new_risk,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        doc_ref.update(updated_payload)
        
        # Simpan riwayat Snapshot Temporal ke koleksi audit_logs Firebase
        log_id = str(uuid.uuid4())
        audit_log = {
            "log_id": log_id,
            "shipment_id": shipment_id,
            "action": "UPDATE",
            "changed_fields": "shipping_mode, calculated_co2, destination",
            "version_snapshot": new_version,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        db.collection("audit_logs").document(log_id).set(audit_log)
        
        return {
            "status": "success",
            "message": "Shipment updated and metrics recalculated inside Firestore",
            "data": {
                "shipment_id": shipment_id,
                "version": new_version,
                "calculated_co2": new_co2,
                "risk_status": new_risk
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Gagal mengedit data: {str(e)}"})

# ═══ 3. RIWAYAT AUDIT MUTASI DATA (AUDIT LOGS TRACKING) ═══════════════
@app.get("/api/shipments/{shipment_id}/logs")
async def get_shipment_logs(shipment_id: str):
    try:
        docs = db.collection("audit_logs").where("shipment_id", "==", shipment_id).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        return {"error": str(e)}

# ═══ 4. PEMASOK DATA UTAMA TABEL (GET SHIPMENT LIST) ═════════════════
@app.get("/api/shipments/list")
async def get_shipment_list():
    try:
        docs = db.collection("shipments").order_by("updated_at", direction="DESCENDING").stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        docs = db.collection("shipments").stream()
        return [doc.to_dict() for doc in docs]

# ═══ 5. PEMASOK GRAFIK ANALYTICS ═════════════════════════════════════
@app.get("/api/analytics/home")
async def get_analytics_home():
    try:
        shipments = db.collection("shipments").stream()
        shipment_list = [s.to_dict() for s in shipments]
        total_count = len(shipment_list)
        if total_count == 0:
            return {"total_shipments": 0, "average_co2_emission": 0, "risk_distribution": {"high_risk": 0, "medium_risk": 0, "low_risk": 0}, "esg_compliance_rate": "100%"}
            
        total_co2 = sum([s.get("co2_emission", 0) for s in shipment_list])
        high_r = len([s for s in shipment_list if s.get("risk_status") == "High Risk"])
        med_r = len([s for s in shipment_list if s.get("risk_status") == "Medium Risk"])
        low_r = len([s for s in shipment_list if s.get("risk_status") == "Low Risk"])
        compliance_ratio = round(((low_r + med_r) / total_count) * 100, 1)
        
        return {
            "total_shipments": total_count,
            "average_co2_emission": round(total_co2 / total_count, 2),
            "risk_distribution": {"high_risk": high_r, "medium_risk": med_r, "low_risk": low_r},
            "esg_compliance_rate": f"{compliance_ratio}%"
        }
    except Exception as e:
        return {"error": str(e)}