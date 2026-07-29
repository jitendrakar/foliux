import os
from django.test import TestCase
from screener.models import Company, ManagementDocument, ManagementForecast, ForecastComparison, ManagementReliabilityScore
from screener.guidance_downloader import download_or_sync_document, compute_sha256, get_company_fy_dir
from screener.forecast_extractor import extract_and_store_forecasts
from screener.comparison_engine import evaluate_forecast_vs_actuals, update_company_reliability_score

class ManagementGuidanceTestCase(TestCase):
    databases = {'default', 'screener'}

    def setUp(self):
        self.company = Company.objects.create(
            name="Tata Consultancy Services Ltd",
            nse_symbol="TCS",
            industry="IT Services & Consulting",
            sector="Technology"
        )

    def test_local_directory_structure(self):
        fy_dir = get_company_fy_dir(self.company.nse_symbol, "FY2024")
        self.assertTrue(os.path.exists(fy_dir))
        self.assertTrue(fy_dir.endswith(os.path.join("TCS", "FY2024")))

    def test_download_and_checksum(self):
        doc = download_or_sync_document(self.company, "FY2024", "annual_report")
        self.assertIsNotNone(doc)
        self.assertTrue(os.path.exists(doc.local_file_path))
        self.assertTrue(len(doc.checksum) > 0)
        
        # Second call should reuse local cached file
        checksum_before = doc.checksum
        doc2 = download_or_sync_document(self.company, "FY2024", "annual_report")
        self.assertEqual(doc2.checksum, checksum_before)

    def test_forecast_extraction_and_comparison(self):
        doc = download_or_sync_document(self.company, "FY2024", "annual_report")
        forecasts = extract_and_store_forecasts(self.company, "FY2024", [doc])
        self.assertGreater(len(forecasts), 0)

        first_forecast = forecasts[0]
        comp = evaluate_forecast_vs_actuals(first_forecast)
        self.assertIsNotNone(comp)
        self.assertIn(comp.status, ['achieved', 'partially_achieved', 'not_achieved', 'delayed', 'pending'])

        score_obj = update_company_reliability_score(self.company)
        self.assertIsNotNone(score_obj)
        self.assertGreaterEqual(score_obj.overall_score, 0)
        self.assertLessEqual(score_obj.overall_score, 100)
