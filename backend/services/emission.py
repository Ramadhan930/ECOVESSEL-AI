class EmissionCalculatorService:
    # Faktor default jika tidak ada mode (digunakan oleh calculate_co2)
    EMISSION_FACTORS = {
        "STANDARD CLASS": 0.00015,
        "FIRST CLASS": 0.00085,
        "SAME DAY": 0.00095,
        "SECOND CLASS": 0.00030,
    }

    # Mapping region ke estimasi jarak (km)
    DISTANCE_MAP = {
        "SOUTHEAST ASIA": 1200,
        "EAST ASIA": 4200,
        "WESTERN EUROPE": 11500,
        "EASTERN EUROPE": 10200,
        "NORTH AMERICA": 14000,
        "SOUTH AMERICA": 16500,
        "OCEANIA": 5300,
        "CENTRAL AMERICA": 13200,
    }

    @classmethod
    def from_region_mode(cls, region: str, shipping_mode: str) -> dict:
        """
        Menghitung jejak karbon berdasarkan region dan shipping_mode.
        Return dict dengan: estimated_distance_km, carbon_emission_tons,
        emission_intensity_level, compliance_status.
        """
        reg_key = region.upper()
        mode_key = shipping_mode.upper()

        # Jarak: fallback 2500 km jika region tidak dikenal
        distance = cls.DISTANCE_MAP.get(reg_key, 2500)

        # Faktor emisi: cari berdasarkan substring mode (lebih fleksibel)
        factor = cls.EMISSION_FACTORS.get("STANDARD CLASS", 0.00015)  # default
        for mode_substring, fac in cls.EMISSION_FACTORS.items():
            if mode_substring in mode_key:
                factor = fac
                break

        # Rumus emisi: jarak * faktor * 1.2 (faktor koreksi ESG)
        carbon = round(distance * factor * 1.2, 2)

        # Tentukan level & compliance
        if carbon >= 5.0:
            emission_level = "HIGH (Heavy Footprint)"
            compliance = "NON-COMPLIANT"
        elif carbon >= 1.5:
            emission_level = "MEDIUM (Moderate Footprint)"
            compliance = "COMPLIANT"
        else:
            emission_level = "LOW (Eco-Friendly)"
            compliance = "COMPLIANT"

        return {
            "estimated_distance_km": distance,
            "carbon_emission_tons": carbon,
            "emission_intensity_level": emission_level,
            "compliance_status": compliance,
        }

    @classmethod
    def calculate_co2(cls, shipping_mode: str, quantity: int, days_for_shipment: int) -> dict:
        """Alternatif jika menghitung berdasarkan hari pengiriman, bukan region."""
        factor = cls.EMISSION_FACTORS.get(shipping_mode.upper(), 0.05)
        estimated_distance_km = days_for_shipment * 400 if days_for_shipment > 0 else 500
        total_co2_tons = round((estimated_distance_km * quantity * factor) / 1000, 2)

        if total_co2_tons > 15.0:
            intensity = "HIGH (ESG Critical Warning)"
            compliance = "NON-COMPLIANT"
        elif total_co2_tons > 5.0:
            intensity = "MEDIUM (ESG Warning)"
            compliance = "CONDITIONAL"
        else:
            intensity = "LOW (Eco-Friendly)"
            compliance = "COMPLIANT"

        return {
            "estimated_distance_km": estimated_distance_km,
            "carbon_emission_tons": total_co2_tons,
            "emission_intensity_level": intensity,
            "compliance_status": compliance,
        }