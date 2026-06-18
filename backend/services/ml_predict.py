import os
import logging
import joblib
import pandas as pd
from backend.config import settings

logger = logging.getLogger(__name__)

class MLPredictionService:
    _pipeline = None   # gunakan pipeline lengkap jika tersedia

    @classmethod
    def load_pipeline(cls):
        if cls._pipeline is None:
            # Coba pipeline lengkap dulu
            pipeline_path = os.path.join(settings.BASE_DIR, settings.MODEL_PATH)
            if os.path.exists(pipeline_path):
                try:
                    cls._pipeline = joblib.load(pipeline_path)
                    logger.info("ML pipeline loaded from %s", pipeline_path)
                except Exception as e:
                    logger.error("Failed to load pipeline: %s", e)
            else:
                logger.warning("Pipeline file not found at %s", pipeline_path)

    @classmethod
    def predict_risk(cls, region: str, shipping_mode: str,
                     scheduled_days: int, product_category: str) -> tuple:
        cls.load_pipeline()
        # Jika pipeline tersedia (berisi preprocessor + model)
        if cls._pipeline is not None:
            try:
                input_data = pd.DataFrame([{
                    "region": region,
                    "shipping_mode": shipping_mode,
                    "scheduled_shipment_days": scheduled_days,
                    "product_category": product_category,
                }])
                proba = cls._pipeline.predict_proba(input_data)
                risk_prob = float(proba[0][1])
                risk_score = int(risk_prob * 100)
            except Exception as e:
                logger.warning("Pipeline prediction failed, fallback. Error: %s", e)
                risk_prob, risk_score = None, None
            else:
                risk_level = "HIGH" if risk_score >= 70 else ("MEDIUM" if risk_score >= 45 else "LOW")
                return risk_prob, risk_score, risk_level

        # --- Fallback logic ---
        base_risk = 35
        reg_up = region.upper()
        if "NORTH AMERICA" in reg_up or "EUROPE" in reg_up:
            base_risk += 25
        mode_up = shipping_mode.upper()
        if "FIRST CLASS" in mode_up or "SAME DAY" in mode_up:
            base_risk += 20
        if scheduled_days <= 1:
            base_risk += 15

        risk_score = min(base_risk, 95)
        risk_level = "HIGH" if risk_score >= 70 else ("MEDIUM" if risk_score >= 45 else "LOW")
        return round(risk_score / 100, 2), risk_score, risk_level