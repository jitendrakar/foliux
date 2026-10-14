import json
from django.test import TestCase, Client
from core.audio_adviser import parse_advisory_query, generate_investment_advice

class AudioAdviserEngineTests(TestCase):
    def test_parse_amount_sip(self):
        parsed = parse_advisory_query("Where should I invest 10000 monthly for 5 years?")
        self.assertEqual(parsed['amount'], 10000)
        self.assertTrue(parsed['is_sip'])
        self.assertFalse(parsed['is_lump_sum'])

    def test_parse_lump_sum(self):
        parsed = parse_advisory_query("How should I invest 1 lakh lumpsum?")
        self.assertEqual(parsed['amount'], 100000)
        self.assertTrue(parsed['is_lump_sum'])

    def test_parse_retirement(self):
        parsed = parse_advisory_query("I want to plan for retirement with NPS and low risk")
        self.assertEqual(parsed['risk'], 'conservative')
        self.assertEqual(parsed['topic'], 'retirement')
        self.assertIn('nps', parsed['assets_mentioned'])

    def test_generate_advice_structure(self):
        advice = generate_investment_advice("Where should I invest 20000 per month?")
        self.assertEqual(advice['status'], 'success')
        self.assertTrue(len(advice['spoken_text']) > 50)
        self.assertTrue(len(advice['allocations']) >= 3)
        self.assertTrue(len(advice['execution_steps']) >= 3)
        self.assertTrue(len(advice['suggested_links']) >= 3)
        
        # Verify allocation percentages sum to 100%
        total_pct = sum(a['percentage'] for a in advice['allocations'])
        self.assertEqual(total_pct, 100)

    def test_generate_advice_beginner(self):
        advice = generate_investment_advice("I am a beginner where and how to invest")
        self.assertEqual(advice['status'], 'success')
        self.assertIn("Beginner", advice['title'])
        self.assertIn("50", str(advice['allocations'][0]['percentage']))

    def test_generate_advice_short_term_safe(self):
        advice = generate_investment_advice("Safe investment for 6 months no loss")
        self.assertEqual(advice['status'], 'success')
        self.assertIn("Capital Preservation", advice['title'])


class AudioAdviserAPITests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')

    def test_api_post_valid(self):
        response = self.client.post(
            '/api/audio-adviser/',
            data=json.dumps({'query': 'Where should I invest 10000 monthly?'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('spoken_text', data)
        self.assertIn('allocations', data)
        self.assertIn('execution_steps', data)

    def test_api_post_empty_query(self):
        response = self.client.post(
            '/api/audio-adviser/',
            data=json.dumps({'query': ''}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_api_get_query(self):
        response = self.client.get('/api/audio-adviser/?q=How+to+invest+safely')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
