from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/explain", tags=["AI Explainability (SHAP)"])

# 1. Definisikan Request Body (Payload dari Frontend)
class ExplainRequest(BaseModel):
    region: str
    shipping_mode: str
    scheduled_shipment_days: int
    product_category: str

@router.post("/shipment")
def get_shap_explainability(payload: ExplainRequest):
    """
    Kebutuhan Awal: Mengembalikan nilai kontribusi fitur (SHAP values)
    untuk menjelaskan alasan di balik skor risiko suatu pengiriman.
    """
    try:
        # Simulasi analisis SHAP berdasarkan input bisnis utama
        # Nilai positif berarti menaikkan risiko delay, nilai negatif menurunkan risiko
        shap_values = [
            {"feature": "Scheduled Shipment Days", "shap_value": 0.28, "effect": "Meningkatkan Risiko Delay"},
            {"feature": "Shipping Mode (" + payload.shipping_mode + ")", "shap_value": 0.15, "effect": "Meningkatkan Risiko Delay"},
            {"feature": "Order Region (" + payload.region + ")", "shap_value": -0.12, "effect": "Menurunkan Risiko Delay"},
            {"feature": "Product Category (" + payload.product_category + ")", "shap_value": 0.04, "effect": "Meningkatkan Risiko Delay"},
            {"feature": "Is Weekend Order", "shap_value": -0.05, "effect": "Menurunkan Risiko Delay"}
        ]
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "meta": {
                "base_value": 0.35,  # Skor risiko rata-rata global model
                "prediction_risk_score": 0.65  # Total skor setelah kalkulasi SHAP
            },
            "data": {
                "target_region": payload.region,
                "shap_contributions": shap_values,
                "summary_text": f"Faktor utama yang mendorong peningkatan risiko di wilayah {payload.region} adalah ketatnya estimasi hari pengiriman dijadwalkan ({payload.scheduled_shipment_days} hari) dan pemilihan moda {payload.shipping_mode}."
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses analisis SHAP: {str(e)}")