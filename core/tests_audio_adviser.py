import json
import re
from django.test import TestCase, Client
from core.audio_adviser import (
    parse_advisory_query,
    generate_investment_advice,
    CLOSING_NOTICE_EN,
    CLOSING_NOTICE_HI,
    CLOSING_NOTICE_HI_PHONETIC
)

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
        self.assertEqual(advice['language'], 'en')
        self.assertIn('login_cta', advice)
        # Check closing login notification in spoken audio
        self.assertTrue(advice['spoken_text'].strip().endswith(CLOSING_NOTICE_EN))
        
        # Verify allocation percentages sum to 100%
        total_pct = sum(a['percentage'] for a in advice['allocations'])
        self.assertEqual(total_pct, 100)

    def test_generate_advice_beginner(self):
        advice = generate_investment_advice("I am a beginner where and how to invest")
        self.assertEqual(advice['status'], 'success')
        self.assertIn("Beginner", advice['title'])
        self.assertIn("50", str(advice['allocations'][0]['percentage']))
        self.assertTrue(advice['spoken_text'].strip().endswith(CLOSING_NOTICE_EN))

    def test_generate_advice_short_term_safe(self):
        advice = generate_investment_advice("Safe investment for 6 months no loss")
        self.assertEqual(advice['status'], 'success')
        self.assertIn("Capital Preservation", advice['title'])
        self.assertTrue(advice['spoken_text'].strip().endswith(CLOSING_NOTICE_EN))

    def test_hindi_devanagari_query_detection_and_advice(self):
        advice = generate_investment_advice("मुझे 10000 रुपये हर महीने निवेश करने हैं")
        self.assertEqual(advice['status'], 'success')
        self.assertEqual(advice['language'], 'hi')
        self.assertEqual(advice['parsed_query']['amount'], 10000)
        self.assertTrue(advice['parsed_query']['is_sip'])
        # Spoken audio must be in Hindi and end with the login and profile notice
        self.assertTrue(advice['spoken_text'].strip().endswith(CLOSING_NOTICE_HI))
        self.assertIn("FOLIUX", advice['spoken_text'])
        self.assertIn("लॉगिन", advice['spoken_text'])
        self.assertIn("प्रोफ़ाइल", advice['spoken_text'])
        self.assertEqual(advice['login_cta']['button_text'], 'लॉगिन करें और प्रोफ़ाइल सेट करें')
        # Check phonetic Romanized Hindi fallback for devices lacking Hindi TTS pack
        self.assertIn('spoken_text_phonetic', advice)
        self.assertTrue(advice['spoken_text_phonetic'].strip().endswith(CLOSING_NOTICE_HI_PHONETIC))
        # Ensure spoken_text_phonetic contains no Devanagari characters
        self.assertIsNone(re.search(r'[\u0900-\u097F]', advice['spoken_text_phonetic']))

    def test_hindi_hinglish_query_detection_and_advice(self):
        advice = generate_investment_advice("mujhe 50000 invest karna hai safe tarike se")
        self.assertEqual(advice['status'], 'success')
        self.assertEqual(advice['language'], 'hi')
        self.assertEqual(advice['parsed_query']['amount'], 50000)
        self.assertEqual(advice['parsed_query']['risk'], 'conservative')
        self.assertTrue(advice['spoken_text'].strip().endswith(CLOSING_NOTICE_HI))
        self.assertTrue(advice['spoken_text_phonetic'].strip().endswith(CLOSING_NOTICE_HI_PHONETIC))
        self.assertIsNone(re.search(r'[\u0900-\u097F]', advice['spoken_text_phonetic']))

    def test_explicit_hindi_language_flag(self):
        advice = generate_investment_advice("invest 15000 monthly", requested_lang="hi")
        self.assertEqual(advice['language'], 'hi')
        self.assertTrue(advice['spoken_text'].strip().endswith(CLOSING_NOTICE_HI))
        self.assertTrue(advice['spoken_text_phonetic'].strip().endswith(CLOSING_NOTICE_HI_PHONETIC))
        self.assertIsNone(re.search(r'[\u0900-\u097F]', advice['spoken_text_phonetic']))


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
        self.assertIn('login_cta', data)
        self.assertEqual(data['language'], 'en')
        self.assertTrue(data['spoken_text'].strip().endswith(CLOSING_NOTICE_EN))

    def test_api_post_hindi_query(self):
        response = self.client.post(
            '/api/audio-adviser/',
            data=json.dumps({'query': 'रिटायरमेंट के लिए पैसे कहाँ लगाएं?'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['language'], 'hi')
        self.assertTrue(data['spoken_text'].strip().endswith(CLOSING_NOTICE_HI))
        self.assertIn('spoken_text_phonetic', data)
        self.assertTrue(data['spoken_text_phonetic'].strip().endswith(CLOSING_NOTICE_HI_PHONETIC))
        self.assertIn('लॉगिन करें', data['login_cta']['button_text'])

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
        self.assertEqual(data['language'], 'en')

    def test_api_get_hindi_query(self):
        response = self.client.get('/api/audio-adviser/?q=kaha+invest+kare+safely')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['language'], 'hi')
        self.assertTrue(data['spoken_text'].strip().endswith(CLOSING_NOTICE_HI))
        self.assertIn('spoken_text_phonetic', data)
        self.assertTrue(data['spoken_text_phonetic'].strip().endswith(CLOSING_NOTICE_HI_PHONETIC))
