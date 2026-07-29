from django.test import TestCase, Client
from django.urls import reverse
from screener.models import Company, ManagementReliabilityScore
from screener.nl_query_parser import parse_natural_language_query
from screener.nl_query_engine import execute_nl_query

class NLQuerySearchTestCase(TestCase):
    databases = {'default', 'screener'}

    def setUp(self):
        self.client = Client()
        self.tcs = Company.objects.create(
            name="Tata Consultancy Services Ltd",
            nse_symbol="TCS",
            industry="IT Services & Consulting",
            sector="Technology",
            current_price=3800.0,
            market_cap=1400000.0,
            pe_ratio=28.5,
            roe=45.0,
            roce=52.0,
            debt=0.0,
            sales_growth=12.5,
            profit_growth=14.0,
            dividend_yield=2.2,
            promoter_holding=72.3,
            foliux_score=88
        )
        ManagementReliabilityScore.objects.create(
            company=self.tcs,
            total_forecasts=10,
            achieved_count=8,
            partially_achieved_count=1,
            not_achieved_count=0,
            delayed_count=1,
            reliability_score_percent=86.0,
            ai_credibility_rating='High',
            overall_score=86
        )

    def test_parse_single_conditions(self):
        parsed = parse_natural_language_query("PE Ratio below 50")
        self.assertIn('pe_ratio__lte', parsed['filters'])
        self.assertEqual(parsed['filters']['pe_ratio__lte'], 50.0)

        parsed_roe = parse_natural_language_query("ROE greater than 20%")
        self.assertIn('roe__gte', parsed_roe['filters'])
        self.assertEqual(parsed_roe['filters']['roe__gte'], 20.0)

        parsed_mgmt = parse_natural_language_query("Management Reliability Score above 80%")
        self.assertIn('reliability_score__gte', parsed_mgmt['filters'])
        self.assertEqual(parsed_mgmt['filters']['reliability_score__gte'], 80)

    def test_execute_combined_query(self):
        query = "PE Ratio below 50, ROE above 20%, and Management Reliability Score above 80%"
        result = execute_nl_query(query)
        self.assertGreater(result['total_count'], 0)
        matched_symbols = [r['nse_symbol'] for r in result['results']]
        self.assertIn("TCS", matched_symbols)

    def test_search_views_and_apis(self):
        response = self.client.get(reverse('screener:nl_search') + '?q=PE+Ratio+below+50')
        self.assertEqual(response.status_code, 200)

        api_response = self.client.get(reverse('screener:nl_search_api') + '?q=ROE+above+20%25')
        self.assertEqual(api_response.status_code, 200)
        self.assertIn('results', api_response.json())

        suggest_response = self.client.get(reverse('screener:nl_suggest_api') + '?q=pe')
        self.assertEqual(suggest_response.status_code, 200)
        self.assertIn('suggestions', suggest_response.json())
