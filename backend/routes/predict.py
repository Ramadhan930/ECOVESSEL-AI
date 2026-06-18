import asyncio
import io
import json
import logging
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_db
from backend.database.models import ShipmentLogModel, ShipmentModel
from backend.schemas.shipment import ShipmentEditRequest
from backend.services.emission import EmissionCalculatorService
from backend.services.gemini import GeminiAdvisorService
from backend.services.ml_predict import MLPredictionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/shipments", tags=["Shipment Core & Hybrid Analytics"])


async def _process_row(row, index: int):
    """
    Fungsi bantu async untuk memproses satu baris CSV dengan Log Indikator Khusus.
    """
    region = str(row['region'])
    mode = str(row['shipping_mode'])
    days = int(row['scheduled_shipment_days'])
    category = str(row['product_category'])

    # 1. Prediksi risiko ML di thread agar tidak blocking
    try:
        risk_prob, risk_score, risk_level = await asyncio.to_thread(
            MLPredictionService.predict_risk,
            region, mode, days, category
        )
        # 🚀 JIKA MODUL ML FRANZ BERHASIL MEMPROSES TANPA EROR
        print("\n" + "="*60)
        print(f"🔥 [LOG BARIS {index}]: MODEL ML RANDOM FOREST FRANZ SUKSES DIGUNAKAN!")
        print(f"👉 Output Asli -> Prob: {risk_prob}, Score: {risk_score}, Level: {risk_level}")
        print("="*60 + "\n")

    except Exception as e:
        # ⚠️ JIKA EROR STRING-TO-FLOAT TERJADI (MASUK JARING PENGAMAN)
        print("\n" + "!"*60)
        print(f"⚠️ [LOG BARIS {index}]: PIPELINE ML GAGAL -> MASUK MODE SIMULASI (FALLBACK)")
        print(f"Detail Masalah: {e}")
        print("💡 Solusi: Backend butuh file encoder/preprocessor.pkl dari Franz.")
        print("!"*60 + "\n")
        
        logger.warning("ML predict failed for row %d, using fallback. Error: %s", index, e)
        risk_prob, risk_score, risk_level = 0.35, 35, "MEDIUM"

    # 2. Kalkulasi Emisi (operasi CPU-bound ringan, tetap sync)
    co2_result = EmissionCalculatorService.from_region_mode(region, mode)

    # 3. AI Solutions (blocking call di thread)
    try:
        ai_solutions = await asyncio.to_thread(
            GeminiAdvisorService.generate_logistics_solution,
            region, risk_score, risk_level, co2_result
        )
    except Exception as e:
        logger.error("Gemini advisor failed for row %d, fallback to static. Error: %s", index, e)
        ai_solutions = GeminiAdvisorService._static_fallback(region, risk_level, co2_result)

    # Bangun objek model
    shipment = ShipmentModel(
        region=region,
        shipping_mode=mode,
        scheduled_shipment_days=days,
        product_category=category,
        version=1,
        risk_probability=risk_prob,
        risk_score=risk_score,
        risk_level=risk_level,
        estimated_distance_km=co2_result["estimated_distance_km"],
        carbon_emission_tons=co2_result["carbon_emission_tons"],
        emission_intensity_level=co2_result["emission_intensity_level"],
        compliance_status=co2_result["compliance_status"],
        ai_solutions=ai_solutions,
    )
    return shipment, {
        "region": region,
        "shipping_mode": mode,
        "analytics": {
            "risk_analysis": {"risk_score": risk_score, "risk_level": risk_level},
            "sustainability_audit": co2_result,
            "ai_mitigation_advisor": {"solutions": ai_solutions},
        }
    }


@router.post("/upload-csv")
async def upload_logistics_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Format file harus CSV")

    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        required = ['region', 'shipping_mode', 'scheduled_shipment_days', 'product_category']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise HTTPException(status_code=400, detail=f"Kolom wajib tidak ada: {missing}")

        response_data = []
        for idx, row in df.iterrows():
            shipment, analytics = await _process_row(row, idx)
            db.add(shipment)
            await db.flush()  # dapatkan ID
            response_entry = {"id": shipment.id, **analytics}
            response_data.append(response_entry)

        await db.commit()
        return {
            "status": "success",
            "message": f"Berhasil menyimpan {len(response_data)} data logistik ke PostgreSQL.",
            "data": response_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Gagal memproses CSV")
        raise HTTPException(status_code=500, detail=f"Gagal memproses CSV: {str(e)}")


@router.put("/{shipment_id}/edit")
async def edit_shipment_data(
    shipment_id: int,
    payload: ShipmentEditRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ShipmentModel).where(ShipmentModel.id == shipment_id))
    old_shipment = result.scalar_one_or_none()
    if not old_shipment:
        raise HTTPException(status_code=404, detail="ID Pengiriman tidak ditemukan")

    # Snapshot data lama
    old_analytics = {
        "risk_analysis": {
            "risk_probability": old_shipment.risk_probability,
            "risk_score": old_shipment.risk_score,
            "risk_level": old_shipment.risk_level,
        },
        "sustainability_audit": {
            "estimated_distance_km": old_shipment.estimated_distance_km,
            "carbon_emission_tons": old_shipment.carbon_emission_tons,
            "emission_intensity_level": old_shipment.emission_intensity_level,
            "compliance_status": old_shipment.compliance_status,
        },
        "ai_mitigation_advisor": {"solutions": old_shipment.ai_solutions},
    }
    db_log = ShipmentLogModel(
        shipment_id=shipment_id,
        version_archived=old_shipment.version,
        previous_data={
            "region": old_shipment.region,
            "shipping_mode": old_shipment.shipping_mode,
            "scheduled_shipment_days": old_shipment.scheduled_shipment_days,
            "product_category": old_shipment.product_category,
        },
        previous_analytics=old_analytics,
    )
    db.add(db_log)

    # Kalkulasi ulang menggunakan service
    region = payload.region
    mode = payload.shipping_mode
    days = payload.scheduled_shipment_days
    category = payload.product_category

    # ML prediction di thread
    try:
        risk_prob, risk_score, risk_level = await asyncio.to_thread(
            MLPredictionService.predict_risk, region, mode, days, category
        )
    except Exception:
        logger.warning("ML edit prediction failed, fallback")
        risk_prob, risk_score, risk_level = 0.35, 35, "MEDIUM"

    co2_result = EmissionCalculatorService.from_region_mode(region, mode)

    # AI advisor di thread
    try:
        ai_solutions = await asyncio.to_thread(
            GeminiAdvisorService.generate_logistics_solution,
            region, risk_score, risk_level, co2_result
        )
    except Exception:
        ai_solutions = GeminiAdvisorService._static_fallback(region, risk_level, co2_result)

    # Update objek
    old_shipment.region = region
    old_shipment.shipping_mode = mode
    old_shipment.scheduled_shipment_days = days
    old_shipment.product_category = category
    old_shipment.version += 1
    old_shipment.risk_probability = risk_prob
    old_shipment.risk_score = risk_score
    old_shipment.risk_level = risk_level
    old_shipment.estimated_distance_km = co2_result["estimated_distance_km"]
    old_shipment.carbon_emission_tons = co2_result["carbon_emission_tons"]
    old_shipment.emission_intensity_level = co2_result["emission_intensity_level"]
    old_shipment.compliance_status = co2_result["compliance_status"]
    old_shipment.ai_solutions = ai_solutions

    await db.commit()

    return {
        "status": "success",
        "message": f"Data ID {shipment_id} berhasil diupdate ke Versi {old_shipment.version} di PostgreSQL.",
        "data": {
            "id": shipment_id,
            "region": region,
            "shipping_mode": mode,
            "analytics": {
                "risk_analysis": {
                    "risk_score": risk_score,
                    "risk_level": risk_level
                },
                "sustainability_audit": co2_result,
                "ai_mitigation_advisor": {"solutions": ai_solutions}
            }
        }
    }

@router.get("/{shipment_id}/logs")
async def get_shipment_historical_logs(
    shipment_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ShipmentLogModel)
        .where(ShipmentLogModel.shipment_id == shipment_id)
        .order_by(ShipmentLogModel.archived_at.desc())
    )
    logs = result.scalars().all()
    return {
        "status": "success",
        "shipment_id": shipment_id,
        "total_mutations": len(logs),
        "historical_logs": [
            {
                "log_id": log.log_id,
                "version_archived": log.version_archived,
                "archived_at": log.archived_at.isoformat() + "Z",
                "previous_data": log.previous_data,
                "previous_analytics": log.previous_analytics,
            }
            for log in logs
        ],
    }

@router.get("/list", status_code=200)
async def get_all_logistics_data(db: AsyncSession = Depends(get_db)):
    """
    3. MVP TAMBAHAN: Menarik semua data logistik dari PostgreSQL 
       untuk disuplai dan ditampilkan dalam bentuk tabel di Frontend.
    """
    try:
        # 1. Tulis query SQL: SELECT * FROM shipments ORDER BY updated_at DESC
        query = select(ShipmentModel).order_by(ShipmentModel.updated_at.desc())
        result = await db.execute(query)
        
        # 2. Ambil semua baris datanya
        all_shipments = result.scalars().all()
        
        # 3. Rapikan formatnya menjadi JSON Array untuk Frontend
        response_list = []
        for shipment in all_shipments:
            response_list.append({
                "id": shipment.id,
                "region": shipment.region,
                "shipping_mode": shipment.shipping_mode,
                "scheduled_shipment_days": shipment.scheduled_shipment_days,
                "product_category": shipment.product_category,
                "version": shipment.version,
                "analytics": {
                    "risk_analysis": {
                        "risk_score": shipment.risk_score, 
                        "risk_level": shipment.risk_level,
                        "risk_probability": shipment.risk_probability
                    },
                    "sustainability_audit": {
                        "estimated_distance_km": shipment.estimated_distance_km,
                        "carbon_emission_tons": shipment.carbon_emission_tons,
                        "emission_intensity_level": shipment.emission_intensity_level,
                        "compliance_status": shipment.compliance_status
                    },
                    "ai_mitigation_advisor": {
                        "solutions": shipment.ai_solutions
                    }
                }
            })
            
        return {
            "status": "success",
            "total_records": len(response_list),
            "data": response_list
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Gagal mengambil data dari database: {str(e)}"
        )