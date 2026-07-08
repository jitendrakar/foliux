import os
import json
import base64
import hashlib
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

from .models import (
    IncomeTaxProfile, IncomeTaxTds, IncomeTaxSalary, IncomeTaxInterest,
    IncomeTaxDividend, IncomeTaxEquity, IncomeTaxMutualFund, IncomeTaxSft,
    IncomeTaxTaxPaid, IncomeTaxRefund, IncomeTaxDemand, IncomeTaxOther,
    UserTaxProfile
)
from .ais_importer import decrypt_ais_json, parse_and_import_ais

class AISTestHelper:
    @staticmethod
    def encrypt_payload(plaintext_str, password):
        salt = os.urandom(16)
        iv = os.urandom(16)
        
        # Derive 32-byte key
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 1000, dklen=32)
        
        # Pad plaintext
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext_str.encode('utf-8')) + padder.finalize()
        
        # Encrypt
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # Format payload: IV (32 hex) + Salt (32 hex) + Base64 Ciphertext
        payload = iv.hex() + salt.hex() + base64.b64encode(ciphertext).decode('utf-8')
        return payload


class AISTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testtaxpayer', password='password123')
        self.pan = 'atkpk3598g'
        self.dob = '04081982'
        self.password = self.pan + self.dob
        
        self.mock_ais_data = {
            "partA": {
                "pan": "ATKPK3598G",
                "aadhaar": "XXXX-XXXX-1234",
                "taxpayerName": "TEST TAXPAYER NAME",
                "dob": "04/08/1982",
                "emailId": "test@foliux.com",
                "mobileNo": "9876543210",
                "address": {
                    "line1": "Flat 101, building A",
                    "city": "Mumbai",
                    "pin": "400001"
                }
            },
            "partB": {
                "tdsTcsInfo": [
                    {
                        "tan": "MUMR12345A",
                        "deductorName": "MOCK EMPLOYER LTD",
                        "section": "192",
                        "amountPaid": "1200000.00",
                        "taxDeducted": "150000.00",
                        "quarter": "Q4"
                    },
                    {
                        "tan": "DELR98765B",
                        "deductorName": "MOCK DEDUCTOR LTD",
                        "section": "194A",
                        "amountPaid": "10000.00",
                        "taxDeducted": "1000.00",
                        "quarter": "Q2"
                    }
                ],
                "sftInfo": [
                    {
                        "sftType": "SFT-005",
                        "description": "Interest on savings bank account",
                        "amount": "12500.00",
                        "transDate": "2026-03-31",
                        "bankName": "HDFC BANK LTD"
                    },
                    {
                        "sftType": "SFT-006",
                        "description": "Interest on fixed deposits",
                        "amount": "45000.00",
                        "transDate": "2026-03-31",
                        "bankName": "ICICI BANK LTD"
                    },
                    {
                        "sftType": "SFT-015",
                        "description": "Dividend from equity shares",
                        "amount": "5000.00",
                        "transDate": "2025-10-15",
                        "companyName": "RELIANCE INDUSTRIES LTD",
                        "isin": "INE002A01018"
                    },
                    {
                        "sftType": "SFT-011",
                        "description": "Mutual fund purchase",
                        "amount": "50000.00",
                        "transDate": "2025-06-20",
                        "amcName": "SBI MUTUAL FUND",
                        "schemeName": "SBI Bluechip Fund",
                        "units": "500.00"
                    },
                    {
                        "sftType": "SFT-017",
                        "description": "Sale of equity shares",
                        "amount": "75000.00",
                        "transDate": "2025-12-05",
                        "brokerName": "ZERODHA BROKING LTD",
                        "isin": "INE123A01024",
                        "quantity": "100.00"
                    }
                ],
                "taxPaymentInfo": [
                    {
                        "taxType": "Advance Tax",
                        "bsrCode": "0210099",
                        "challanNumber": "04561",
                        "amount": "20000.00",
                        "date": "2025-09-15"
                    }
                ],
                "demandRefundInfo": {
                    "refund": [
                        {
                            "refundAmount": "1500.00",
                            "refundDate": "2025-07-22",
                            "assessmentYear": "2025-26",
                            "status": "Refund Paid"
                        }
                    ],
                    "demand": [
                        {
                            "assessmentYear": "2024-25",
                            "outstandingDemand": "500.00",
                            "status": "Outstanding"
                        }
                    ]
                },
                "otherInfo": [
                    {
                        "category": "Interest on Tax Refund",
                        "description": "Interest under section 244A",
                        "amount": "80.00"
                    }
                ]
            }
        }
        
        self.json_str = json.dumps(self.mock_ais_data)
        self.encrypted_payload = AISTestHelper.encrypt_payload(self.json_str, self.password)

    def test_decryption_success(self):
        decrypted = decrypt_ais_json(self.encrypted_payload.encode('utf-8'), self.password)
        self.assertEqual(decrypted, self.json_str)

    def test_decryption_plaintext(self):
        decrypted = decrypt_ais_json(self.json_str.encode('utf-8'), self.password)
        self.assertEqual(decrypted, self.json_str)

    def test_decryption_failure_wrong_password(self):
        with self.assertRaises(ValueError) as ctx:
            decrypt_ais_json(self.encrypted_payload.encode('utf-8'), "wrongpassword123")
        self.assertIn("Invalid password", str(ctx.exception))

    def test_decryption_failure_corrupted_payload(self):
        corrupted = (self.encrypted_payload[:64] + "AAAAA").encode('utf-8')
        with self.assertRaises(ValueError):
            decrypt_ais_json(corrupted, self.password)

    def test_parsing_and_import(self):
        fy = "FY 2025-26"
        counts, err = parse_and_import_ais(self.user, self.json_str, fy, duplicate_action=None)
        
        self.assertNil = err is None
        self.assertTrue(err is None)
        self.assertEqual(counts['salary'], 1)
        self.assertEqual(counts['tds'], 2)
        self.assertEqual(counts['interest'], 2)
        self.assertEqual(counts['dividend'], 1)
        self.assertEqual(counts['mutual_fund'], 1)
        self.assertEqual(counts['equity'], 1)
        self.assertEqual(counts['sft'], 5)
        self.assertEqual(counts['tax_payment'], 1)
        self.assertEqual(counts['refund'], 1)
        self.assertEqual(counts['demand'], 1)
        self.assertEqual(counts['other'], 1)

        # Verify DB Records
        profile = IncomeTaxProfile.objects.get(user=self.user, financial_year=fy)
        self.assertEqual(profile.pan, "ATKPK3598G")
        self.assertEqual(profile.name, "TEST TAXPAYER NAME")
        self.assertEqual(profile.aadhaar, "XXXX-XXXX-1234")
        self.assertIn("Flat 101", profile.address)

        # Check UserTaxProfile Auto-updates
        tax_profile = UserTaxProfile.objects.get(user=self.user, financial_year="FY 2025-26")
        self.assertEqual(tax_profile.salary, Decimal('1200000.00')) # MUMR12345A salary
        # Interest: 12500 + 45000 = 57500. Dividend: 5000. Total = 62500.00
        self.assertEqual(tax_profile.other_taxable_income, Decimal('62500.00'))

    def test_duplicate_handling_detected(self):
        fy = "FY 2025-26"
        # First import
        parse_and_import_ais(self.user, self.json_str, fy)
        
        # Second import without duplicate_action -> should return duplicate status
        result, err = parse_and_import_ais(self.user, self.json_str, fy, duplicate_action=None)
        self.assertEqual(result['status'], 'duplicate_detected')
        self.assertEqual(result['financial_year'], fy)

    def test_duplicate_handling_replace(self):
        fy = "FY 2025-26"
        parse_and_import_ais(self.user, self.json_str, fy)
        
        # Run replace import
        counts, err = parse_and_import_ais(self.user, self.json_str, fy, duplicate_action='replace')
        self.assertTrue(err is None)
        self.assertEqual(counts['tds'], 2)
        # Should not double the records since it deleted existing
        self.assertEqual(IncomeTaxTds.objects.filter(user=self.user, financial_year=fy).count(), 2)

    def test_duplicate_handling_merge(self):
        fy = "FY 2025-26"
        parse_and_import_ais(self.user, self.json_str, fy)
        
        # Run merge import with same JSON -> should deduplicate and result in 0 new records
        counts, err = parse_and_import_ais(self.user, self.json_str, fy, duplicate_action='merge')
        self.assertTrue(err is None)
        self.assertEqual(counts['tds'], 0) # deduplicated
        self.assertEqual(IncomeTaxTds.objects.filter(user=self.user, financial_year=fy).count(), 2)

    def test_ais_dashboard_view_login_required(self):
        self.client.logout()
        response = self.client.get('/calc/ais/dashboard/')
        self.assertEqual(response.status_code, 302)

    def test_ais_dashboard_view_logged_in(self):
        self.client.login(username='testtaxpayer', password='password123')
        parse_and_import_ais(self.user, self.json_str, "FY 2025-26")
        
        response = self.client.get('/calc/ais/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("FY 2025-26", response.context['available_fys'])

    def test_ais_data_api_success(self):
        self.client.login(username='testtaxpayer', password='password123')
        fy = "FY 2025-26"
        parse_and_import_ais(self.user, self.json_str, fy)
        
        response = self.client.get(f'/calc/ais/data/?fy={fy}')
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data['status'], 'success')
        self.assertEqual(res_data['financial_year'], fy)
        
        data = res_data['data']
        self.assertIn('profile', data)
        self.assertIn('tds', data)
        self.assertIn('salary', data)
        self.assertEqual(len(data['tds']), 2)
        self.assertEqual(len(data['salary']), 1)

    def test_parsing_and_import_ignores_inactive(self):
        # We construct a mock JSON that contains 'Inactive' rows
        mock_data_with_inactive = {
            "partA": {
                "pan": "ATKPK3598G",
                "aadhaar": "XXXX-XXXX-1234",
                "taxpayerName": "TEST TAXPAYER NAME",
                "dob": "04/08/1982",
                "emailId": "test@foliux.com",
                "mobileNo": "9876543210",
                "address": {
                    "line1": "Flat 101, building A"
                }
            },
            "partB": {
                "sections": [
                    {
                        "sectionKey": "tdsTcs",
                        "elements": [
                            {
                                "title": "Income distributed by business trust",
                                "l2": {
                                    "columnLabel": ["Information CategoryCode"],
                                    "columnData": [["TDS-194LBA"]]
                                },
                                "l1": {
                                    "columnLabel": [
                                        {"field": "quarter", "name": "Quarter"},
                                        {"field": "amtPaid", "name": "Amount Paid"},
                                        {"field": "amountDeducted", "name": "TDS Deducted"},
                                        {"field": "status", "name": "Status"}
                                    ],
                                    "columnData": [
                                        ["Q1(Apr-Jun)", "112.00", "0", "Inactive"],
                                        ["Q1(Apr-Jun)", "112.00", "0", "Active"],
                                        ["Q2(Jul-Sep)", "100.00", "5.00", "Active"],
                                        ["Q2(Jul-Sep)", "100.00", "5.00", "Inactive"]
                                    ]
                                }
                            }
                        ]
                    },
                    {
                        "sectionKey": "sft",
                        "elements": [
                            {
                                "title": "Dividend",
                                "l2": {
                                    "columnLabel": ["Information Code"],
                                    "columnData": [["SFT-015"]]
                                },
                                "l1": {
                                    "columnLabel": [
                                        {"field": "amtPaid", "name": "Amount"},
                                        {"field": "status", "name": "Status"}
                                    ],
                                    "columnData": [
                                        ["500.00", "Inactive"],
                                        ["300.00", "Active"]
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        }
        
        fy = "FY 2025-26"
        json_str = json.dumps(mock_data_with_inactive)
        counts, err = parse_and_import_ais(self.user, json_str, fy, duplicate_action=None)
        
        self.assertTrue(err is None)
        # Should only import Active records:
        # For tds: 2 active rows out of 4 total rows
        # For dividend: 1 active row out of 2 total rows
        self.assertEqual(counts['tds'], 2)
        self.assertEqual(counts['dividend'], 1)
        
        # Verify from database
        tds_records = IncomeTaxTds.objects.filter(user=self.user, financial_year=fy)
        self.assertEqual(tds_records.count(), 2)
        
        div_records = IncomeTaxDividend.objects.filter(user=self.user, financial_year=fy)
        self.assertEqual(div_records.count(), 1)
        self.assertEqual(div_records.first().amount, Decimal('300.00'))

        # Test legacy format with Inactive records
        legacy_data_with_inactive = {
            "partA": {
                "pan": "ATKPK3598G",
                "aadhaar": "XXXX-XXXX-1234",
                "taxpayerName": "TEST TAXPAYER NAME",
                "dob": "04/08/1982"
            },
            "tds": [
                {
                    "tan": "MUMR12345A",
                    "deductorName": "MOCK EMPLOYER LTD",
                    "section": "192",
                    "amountPaid": "50000.00",
                    "taxDeducted": "5000.00",
                    "quarter": "Q1",
                    "status": "Inactive"
                },
                {
                    "tan": "MUMR12345A",
                    "deductorName": "MOCK EMPLOYER LTD",
                    "section": "192",
                    "amountPaid": "60000.00",
                    "taxDeducted": "6000.00",
                    "quarter": "Q1",
                    "status": "Active"
                }
            ],
            "sft": [
                {
                    "sftType": "SFT-015",
                    "description": "Dividend",
                    "amount": "1000.00",
                    "companyName": "RELIANCE INDUSTRIES LTD",
                    "status": "Inactive"
                },
                {
                    "sftType": "SFT-015",
                    "description": "Dividend",
                    "amount": "2000.00",
                    "companyName": "RELIANCE INDUSTRIES LTD",
                    "status": "Active"
                }
            ]
        }
        
        # We need to clear the existing records
        IncomeTaxProfile.objects.filter(user=self.user, financial_year=fy).delete()
        IncomeTaxTds.objects.filter(user=self.user, financial_year=fy).delete()
        IncomeTaxDividend.objects.filter(user=self.user, financial_year=fy).delete()
        
        legacy_json_str = json.dumps(legacy_data_with_inactive)
        counts_legacy, err_legacy = parse_and_import_ais(self.user, legacy_json_str, fy, duplicate_action=None)
        
        self.assertTrue(err_legacy is None)
        self.assertEqual(counts_legacy['tds'], 1)
        self.assertEqual(counts_legacy['dividend'], 1)

