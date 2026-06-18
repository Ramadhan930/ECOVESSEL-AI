from datetime import datetime

class ShipmentModel:
    """Model untuk menampung data hasil analisis CSV logistik secara aman tanpa SQL Engine"""
    def __init__(self, **kwargs):
        self.id = kwargs.get("id")
        self.region = kwargs.get("region", "Global Node")
        self.shipping_mode = kwargs.get("shipping_mode", "Standard")
        self.scheduled_shipment_days = kwargs.get("scheduled_shipment_days", 0)
        self.product_category = kwargs.get("product_category", "General")
        self.version = kwargs.get("version", 1)
        self.updated_at = kwargs.get("updated_at", datetime.utcnow())

        # Kolom Hasil Analisis AI
        self.risk_probability = kwargs.get("risk_probability", 0.0)
        self.risk_score = kwargs.get("risk_score", 0)
        self.risk_level = kwargs.get("risk_level", "low")
        self.estimated_distance_km = kwargs.get("estimated_distance_km", 0)
        self.carbon_emission_tons = kwargs.get("carbon_emission_tons", 0.0)
        self.emission_intensity_level = kwargs.get("emission_intensity_level", "low")
        self.compliance_status = kwargs.get("compliance_status", "Compliant")
        self.ai_solutions = kwargs.get("ai_solutions", [])

    def to_dict(self):
        """Helper untuk mengubah objek menjadi dictionary agar siap dilempar ke Firebase Firestore"""
        return {
            "region": self.region,
            "shipping_mode": self.shipping_mode,
            "risk_probability": self.risk_probability,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "ai_solutions": self.ai_solutions,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }


class ShipmentLogModel:
    """Model dummy log riwayat versi untuk mencegah import-error di router lama"""
    def __init__(self, **kwargs):
        self.log_id = kwargs.get("log_id")
        self.shipment_id = kwargs.get("shipment_id")
        self.version_archived = kwargs.get("version_archived", 1)
        self.archived_at = kwargs.get("archived_at", datetime.utcnow())
        self.previous_data = kwargs.get("previous_data", {})
        self.previous_analytics = kwargs.get("previous_analytics", {})