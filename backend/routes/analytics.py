from fastapi import APIRouter
from datetime import datetime, timezone  # 🌟 Tambahkan timezone

router = APIRouter(prefix="/analytics", tags=["Analytics & Dashboard"])

@router.get("/home")
def get_home_dashboard_metadata():
    """
    Kebutuhan Awal: Mengembalikan data ringkasan makro global 
    untuk halaman beranda dashboard utama (Cards & Summary).
    """
    return {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),  # 🌟 Standar modern
        "data": {
            "summary_cards": {
                "total_shipments_monitored": 1420,
                "active_high_risk_alerts": 12,
                "total_carbon_saved_tons": 45.8,
                "average_delivery_efficiency": "92.4%"
            },
            "charts": {
                "monthly_risk_trend": [
                    {"month": "Jan", "low_risk": 120, "medium_risk": 30, "high_risk": 5},
                    {"month": "Feb", "low_risk": 140, "medium_risk": 25, "high_risk": 8},
                    {"month": "Mar", "low_risk": 110, "medium_risk": 45, "high_risk": 12},
                    {"month": "Apr", "low_risk": 155, "medium_risk": 20, "high_risk": 3}
                ],
                "shipping_mode_distribution": [
                    {"mode": "Standard Class", "percentage": 55},
                    {"mode": "Second Class", "percentage": 25},
                    {"mode": "First Class", "percentage": 15},
                    {"mode": "Same Day", "percentage": 5}
                ]
            }
        }
    }