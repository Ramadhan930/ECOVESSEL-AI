from google import genai
from google.genai import types
import os
import json
from backend.config import settings

class GeminiAdvisorService:
    @staticmethod
    def generate_logistics_solution(region: str, risk_score: int, risk_level: str, co2_data: dict) -> list:
        """
        Menghasilkan rekomendasi taktis logistik secara real-time menggunakan
        SDK Resmi TERBARU (google.genai) dengan model Gemini 1.5 Flash.
        """
        # Ambil API Key resmi dari sistem config Pydantic
        gemini_key = settings.GEMINI_API_KEY
        
        # DEFENSIVE FALLBACK: Jika di .env kosong, langsung lari ke static fallback
        if not gemini_key or gemini_key == "YOUR_API_KEY":
            return GeminiAdvisorService._static_fallback(region, risk_level, co2_data)

        try:
            # 🌟 SINTAKSIS BARU: Inisialisasi Client tunggal yang lebih clean
            client = genai.Client(api_key=gemini_key)
            
            # Susun prompt terstruktur dengan instruksi output JSON Array
            prompt = f"""
            Bertindaklah sebagai Konsultan Senior Manajemen Logistik Maritim & Pakar Supply Chain Global.
            Berikan 3 poin rekomendasi solusi taktis, singkat (maksimal 2 kalimat per poin), tegas, dan operasional berdasarkan data analitik berikut:
            - Wilayah Transit/Tujuan: {region}
            - Skor Risiko Keterlambatan: {risk_score}/100 ({risk_level})
            - Estimasi Emisi Karbon: {co2_data['carbon_emission_tons']} Ton CO2 ({co2_data['emission_intensity_level']})
            
            Wajib memberikan rekomendasi alternatif rute atau taktik penundaan jadwal (slow steaming) jika risiko keterlambatan HIGH.
            
            Format output WAJIB hanya berupa JSON array string kontainer teks langsung tanpa penomoran, contoh format:
            ["Saran tindakan pertama di wilayah ini.", "Saran tindakan kedua untuk mitigasi.", "Saran tindakan ketiga untuk efisiensi emisi."]
            
            Jangan berikan teks tambahan, spasi berlebih, atau markdown selain format JSON array di atas!
            """
            
            # 🌟 SINTAKSIS BARU: Pemanggilan generate_content langsung dari client.models
            response = client.models.generate_content(
                model='gemini-pro',
                contents=prompt
            )
            
            ai_text = response.text.strip()
            
            # Pembersihan Blok Markdown Terstruktur (Defensive Programming)
            if "```" in ai_text:
                ai_text = ai_text.split("```")[1]
                if ai_text.startswith("json"):
                    ai_text = ai_text[4:].strip()
            ai_text = ai_text.strip()

            # Lakukan parsing string JSON menjadi array Python asli
            solutions = json.loads(ai_text)
            if isinstance(solutions, list) and len(solutions) > 0:
                return solutions[:3]
                
        except Exception as e:
            print(f"=== ERROR GEMINI NEW GENAI SDK ===: {str(e)}")
            return GeminiAdvisorService._static_fallback(region, risk_level, co2_data)
            
        return GeminiAdvisorService._static_fallback(region, risk_level, co2_data)
    
    @staticmethod
    def _static_fallback(region: str, risk_level: str, co2_data: dict) -> list:
        """Rekomendasi statis jika semua jalur AI eksternal gagal atau terkena pembatasan."""
        co2_tons = co2_data.get('carbon_emission_tons', 0)
        emission_level = co2_data.get('emission_intensity_level', 'UNKNOWN')
        
        if risk_level.upper() == "HIGH":
            return [
                f"[Kritis] Risiko keterlambatan di wilayah {region} sangat tinggi! Direkomendasikan segera alihkan rute alternatif via hub logistik sekunder terdekat untuk menghindari bottleneck.",
                f"[Taktik Slow Steaming] Mengingat status emisi terpantau '{emission_level}' ({co2_tons} Ton CO2), segera kurangi kecepatan armada (Slow Steaming) jika jadwal masih memungkinkan guna memangkas konsumsi bahan bakar.",
                "[Komentar Operasional] Aktifkan protokol kontinjensi kargo level-1. Hubungi agen lokal di wilayah tujuan untuk persiapan bongkar muat prioritas darurat demi mengamankan rantai pasok."
            ]
        elif risk_level.upper() == "MEDIUM":
            return [
                f"[Peringatan] Terdeteksi potensi hambatan operasional medium di wilayah {region}. Manifes keberangkatan kargo wajib dievaluasi ulang dalam waktu 1x24 jam.",
                f"[Efisiensi ESG] Jejak karbon tercatat {co2_tons} Ton CO2. Optimalkan utilisasi kapasitas muatan kontainer hingga >90% pada pengiriman berikutnya agar intensitas emisi tetap terjaga.",
                "[Komentar Operasional] Lakukan pemantauan cuaca dan kondisi pelabuhan transit secara berkala. Persiapkan tim pemeliharaan internal jika moda pengiriman mengalami kendala teknis ringan."
            ]
        else:
            return [
                f"[Aman] Alur rantai pasok di wilayah {region} dalam kondisi hijau dan berjalan lancar. Jadwal keberangkatan reguler dapat dipertahankan tanpa perubahan.",
                f"[Eco-Audit Lolos] Pengiriman ini memenuhi regulasi kepatuhan hijau dengan status '{emission_level}'. Pertahankan kombinasi rute dan moda transportasi aktif ini untuk audit kuartal.",
                "[Komentar Operasional] Dokumentasikan log performa pengiriman ini ke dalam sistem sebagai tolok ukur (benchmark) efisiensi operasional kargo di masa mendatang."
            ]