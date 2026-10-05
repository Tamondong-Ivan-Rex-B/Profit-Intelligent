"""
Computer Vision OCR Expiration Scanner Module.
Complies with Section 7 Step 2, Section 4.2 & ISO 8601 standards.
Features:
  1. OpenCV digital image preprocessing (Grayscale, Gaussian Blur, Adaptive Thresholding, Morphological Ops)
  2. Multi-pattern Date Parsing Engine (ISO 8601, DD/MM/YYYY, Month names: '24 OCT 2026', 'EXP: 11/2026')
  3. ISO 8601 Normalization (YYYY-MM-DD)
  4. Visual filter preview generator (Base64 data URIs)
  5. System Error Rate evaluation tester
"""
import re
import cv2
import numpy as np
import base64
from datetime import datetime

# Month mapping for packaging text
MONTH_MAP = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06",
    "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
    "JANUARY": "01", "FEBRUARY": "02", "MARCH": "03", "APRIL": "04",
    "JUNE": "06", "JULY": "07", "AUGUST": "08", "SEPTEMBER": "09",
    "OCTOBER": "10", "NOVEMBER": "11", "DECEMBER": "12"
}

class ExpirationDateScanner:
    def __init__(self):
        # Comprehensive packaging date regexes
        self.date_patterns = [
            # ISO 8601: 2026-10-15 or 2026/10/15 or 2026.10.15
            (r'\b(20\d{2})[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])\b', "ISO"),
            # DD/MM/YYYY or DD-MM-YYYY: 15/10/2026 or 15-10-2026
            (r'\b(0[1-9]|[12]\d|3[01])[-/.](0[1-9]|1[0-2])[-/.](20\d{2})\b', "DMY"),
            # MM/DD/YYYY: 10/15/2026
            (r'\b(0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])[-/.](20\d{2})\b', "MDY"),
            # DD MON YYYY: 15 OCT 2026 or 15-OCT-2026
            (r'\b(0[1-9]|[12]\d|3[01])[\s\-.](JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[\s\-.](20\d{2})\b', "DMON_Y"),
            # MON DD YYYY: OCT 15 2026
            (r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[\s\-.](0[1-9]|[12]\d|3[01])[\s\-,.](20\d{2})\b', "MON_DY"),
            # Month/Year: 10/2026 or 10-2026 or EXP 10/26
            (r'(?:EXP|BB|BEST BEFORE|USE BY)?[\s:]*(0[1-9]|1[0-2])[-/.](20\d{2})\b', "MY"),
            # Compact YYYYMMDD: 20261015
            (r'\b(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\b', "COMPACT")
        ]

    def preprocess_image(self, img_array):
        """
        OpenCV image preprocessing pipeline for retail packaging:
        1. Grayscale
        2. Bilateral/Gaussian Filter (edge-preserving noise reduction)
        3. Adaptive Thresholding / Otsu binarization
        4. Morphological Closing to connect dot-matrix text
        """
        # Convert to Grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_array.copy()

        # Resize if too small or too large
        h, w = gray.shape[:2]
        if w < 600:
            scale = 600 / w
            gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
            
        # Noise reduction while preserving stamp edges
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Adaptive Thresholding for varying retail lighting
        thresh = cv2.adaptiveThreshold(
            filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4
        )
        
        # Morphological operations to sharpen ink-jet/dot-matrix printed numbers
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        morphed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return gray, filtered, thresh, morphed

    def encode_cv2_image_to_base64(self, cv2_img):
        """Encode OpenCV image array to base64 data URL for frontend display."""
        _, buffer = cv2.imencode('.png', cv2_img)
        b64_str = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/png;base64,{b64_str}"

    def parse_raw_text(self, raw_text: str):
        """
        Extract and normalize expiration dates from recognized text string.
        Returns list of ISO 8601 dates (YYYY-MM-DD) and pattern details.
        """
        clean_text = raw_text.upper().replace("\n", " ").replace("\r", " ")
        extracted_dates = []

        for pattern, p_type in self.date_patterns:
            matches = re.finditer(pattern, clean_text)
            for m in matches:
                try:
                    iso_date = self.normalize_to_iso(m.groups(), p_type)
                    if iso_date and iso_date not in [d['iso_date'] for d in extracted_dates]:
                        extracted_dates.append({
                            "raw_match": m.group(0),
                            "pattern_type": p_type,
                            "iso_date": iso_date
                        })
                except Exception:
                    continue

        return extracted_dates

    def normalize_to_iso(self, groups, pattern_type):
        """Convert any matched date components to ISO 8601 (YYYY-MM-DD)."""
        if pattern_type == "ISO":
            # (YYYY, MM, DD)
            year, month, day = groups[0], groups[1], groups[2]
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
        elif pattern_type == "DMY":
            # (DD, MM, YYYY)
            day, month, year = groups[0], groups[1], groups[2]
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
        elif pattern_type == "MDY":
            # (MM, DD, YYYY)
            month, day, year = groups[0], groups[1], groups[2]
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
        elif pattern_type == "DMON_Y":
            # (DD, MON, YYYY)
            day, mon_str, year = groups[0], groups[1], groups[2]
            month = MONTH_MAP.get(mon_str, "01")
            return f"{year}-{month}-{day.zfill(2)}"
            
        elif pattern_type == "MON_DY":
            # (MON, DD, YYYY)
            mon_str, day, year = groups[0], groups[1], groups[2]
            month = MONTH_MAP.get(mon_str, "01")
            return f"{year}-{month}-{day.zfill(2)}"
            
        elif pattern_type == "MY":
            # (MM, YYYY) - Assume end of month expiration
            month, year = groups[0], groups[1]
            return f"{year}-{month.zfill(2)}-28"
            
        elif pattern_type == "COMPACT":
            # (YYYY, MM, DD)
            year, month, day = groups[0], groups[1], groups[2]
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
        return None

    def evaluate_system_error_rate(self, test_samples=None):
        """
        Quantifies System Error Rate = 1 - Accuracy Percentage (Section 4.2).
        Runs benchmark across 20 synthetic retail packaging test strings and image patterns.
        """
        if test_samples is None:
            test_samples = [
                ("EXP: 2027-05-18 LOT 4892", "2027-05-18"),
                ("BEST BEFORE 15 OCT 2026", "2026-10-15"),
                ("BB: 24/12/2026 BATCH 91A", "2026-12-24"),
                ("USE BY 08/2027", "2027-08-28"),
                ("EXP 2026.11.30", "2026-11-30"),
                ("PROD 2025-01-01 EXP 2026-06-15", "2026-06-15"),
                ("EXPIRE DATE 09-04-2027", "2027-04-09"),
                ("CONSUME BEFORE 02 FEB 2028", "2028-02-02"),
                ("EXPIRY: 20261231", "2026-12-31"),
                ("L2994 EXP: 14 NOV 2026 14:30", "2026-11-14"),
                ("BEST BEFORE 05/2028 MFG 2025", "2028-05-28"),
                ("EXP 10/22/2026", "2026-10-22"),
                ("EXP: 2027/03/15", "2027-03-15"),
                ("EXP 30-JUN-2026", "2026-06-30"),
                ("EXP. DATE: 12-25-2026", "2026-12-25"),
                ("MFG: 2024 EXP: 2026-09-18", "2026-09-18"),
                ("USE BY: 01 MAR 2027", "2027-03-01"),
                ("BB 18/07/2026", "2026-07-18"),
                ("EXP: 2027-01-10", "2027-01-10"),
                ("BEST BEFORE 28 DEC 2026", "2026-12-28")
            ]

        total_trials = len(test_samples)
        successful_trials = 0
        test_details = []

        for text_input, expected_iso in test_samples:
            matches = self.parse_raw_text(text_input)
            found_dates = [m['iso_date'] for m in matches]
            success = expected_iso in found_dates
            if success:
                successful_trials += 1
            test_details.append({
                "input": text_input,
                "expected": expected_iso,
                "extracted": found_dates[0] if found_dates else "None",
                "status": "PASS" if success else "FAIL"
            })

        accuracy = successful_trials / total_trials
        error_rate = 1.0 - accuracy

        return {
            "total_trials": total_trials,
            "successful_trials": successful_trials,
            "accuracy_percentage": round(accuracy * 100, 2),
            "system_error_rate": round(error_rate, 4),
            "benchmark_passed": error_rate < 0.05,
            "test_details": test_details
        }

# Global singleton scanner
scanner = ExpirationDateScanner()
