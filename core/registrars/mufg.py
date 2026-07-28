import logging
import requests
import xml.etree.ElementTree as ET
import base64
from typing import List, Dict, Any, Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from .base import BaseRegistrar

logger = logging.getLogger(__name__)

class MUFGRegistrar(BaseRegistrar):
    """
    Integration for MUFG IPO Allotment Portal (in.mpms.mufg.com / Link Intime).
    """

    BASE_URL = "https://in.mpms.mufg.com/Initial_Offer/"
    GET_DETAILS_URL = BASE_URL + "IPO.aspx/GetDetails"
    GENERATE_TOKEN_URL = BASE_URL + "IPO.aspx/generateToken"
    SEARCH_URL = BASE_URL + "IPO.aspx/SearchOnPan"
    PAGE_URL = BASE_URL + "public-issues.html"

    AES_KEY = b"8080808080808080"
    AES_IV = b"8080808080808080"

    @property
    def slug(self) -> str:
        return "mufg"

    @property
    def name(self) -> str:
        return "MUFG Intime"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Origin": "https://in.mpms.mufg.com",
            "Referer": self.PAGE_URL
        }

    def _encrypt_token(self, raw_token: str) -> str:
        """Encrypts token string using AES-128-CBC matching MUFG's CryptoJS encVal logic."""
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(raw_token.encode('utf-8')) + padder.finalize()
        cipher = Cipher(algorithms.AES(self.AES_KEY), modes.CBC(self.AES_IV))
        encryptor = cipher.encryptor()
        encrypted_bytes = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(encrypted_bytes).decode('utf-8')

    def get_active_ipos(self) -> List[Dict[str, Any]]:
        """
        Fetches active IPO list dynamically from MUFG IPO portal.
        """
        headers = self._get_headers()
        try:
            resp = requests.post(self.GET_DETAILS_URL, json={}, headers=headers, timeout=12)
            if resp.status_code != 200:
                logger.error(f"MUFG GetDetails failed with status {resp.status_code}")
                return []

            data = resp.json()
            xml_str = data.get("d", "")
            if not xml_str:
                return []

            root = ET.fromstring(xml_str)
            companies = []
            for table in root.findall("Table"):
                cid = table.find("company_id")
                cname = table.find("companyname")
                if cid is not None and cname is not None and cid.text and cname.text:
                    companies.append({
                        "id": cid.text.strip(),
                        "name": cname.text.strip(),
                        "registrar": self.slug,
                        "registrar_name": self.name
                    })
            return companies
        except Exception as e:
            logger.error(f"Error fetching MUFG IPO list: {e}", exc_info=True)
            return []

    def check_allotment_status(
        self, 
        company_id: str, 
        search_type: str, 
        search_value: str, 
        ifsc: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Checks allotment status on MUFG portal.
        """
        search_type_upper = (search_type or "").upper().strip()
        
        # CHKVAL Mapping
        if search_type_upper in ["PAN", "1"]:
            chkval = "1"
        elif search_type_upper in ["APP", "APPLICATION", "2"]:
            chkval = "2"
        elif search_type_upper in ["DP", "DPID", "CLIENT", "OTHER", "3"]:
            chkval = "3"
        elif search_type_upper in ["ACC", "ACCOUNT", "ACCOUNTNO", "4"]:
            chkval = "4"
        else:
            chkval = "1"

        clean_value = str(search_value or "").strip().upper()
        clean_ifsc = str(ifsc or "").strip().upper()

        if not clean_value:
            return {
                "status": "error",
                "message": "Search input value cannot be blank.",
                "results": []
            }

        session = requests.Session()
        headers = self._get_headers()

        try:
            # 1. Warm session cookies
            session.get(self.PAGE_URL, headers=headers, timeout=10)

            # 2. Generate security token
            token_resp = session.post(self.GENERATE_TOKEN_URL, json={}, headers=headers, timeout=10)
            if token_resp.status_code != 200:
                return {
                    "status": "error",
                    "message": "Failed to generate security token from MUFG server.",
                    "results": []
                }

            raw_token = token_resp.json().get("d", "")
            if not raw_token:
                return {
                    "status": "error",
                    "message": "Invalid token response from MUFG server.",
                    "results": []
                }

            enc_token = self._encrypt_token(raw_token)

            # 3. Post Search query
            payload = {
                "clientid": str(company_id),
                "PAN": clean_value,
                "IFSC": clean_ifsc,
                "CHKVAL": chkval,
                "token": enc_token
            }

            search_resp = session.post(self.SEARCH_URL, json=payload, headers=headers, timeout=15)
            if search_resp.status_code != 200:
                return {
                    "status": "error",
                    "message": f"MUFG server returned status code {search_resp.status_code}.",
                    "results": []
                }

            xml_str = search_resp.json().get("d", "")
            if not xml_str:
                return {
                    "status": "error",
                    "message": "Empty response received from MUFG portal.",
                    "results": []
                }

            root = ET.fromstring(xml_str)

            # Check for error table (<Table1><Msg>...</Msg></Table1>)
            for err_table in root.findall("Table1"):
                msg_elem = err_table.find("Msg")
                if msg_elem is not None and msg_elem.text:
                    return {
                        "status": "error",
                        "message": msg_elem.text.strip(),
                        "results": []
                    }

            # Parse results (<Table>)
            tables = root.findall("Table")
            if not tables:
                return {
                    "status": "success",
                    "message": "No allotment record found for the given details.",
                    "results": []
                }

            results = []
            for t in tables:
                def get_txt(tag_name):
                    elem = t.find(tag_name)
                    return elem.text.strip() if elem is not None and elem.text else ""

                company_name = get_txt("companyname")
                applicant_name = get_txt("NAME1")
                category = get_txt("PEMNDG")
                shares_applied_str = get_txt("SHARES")
                shares_allotted_str = get_txt("ALLOT")
                cutoff_price_str = get_txt("offer_price") or get_txt("CUTOFF")
                amt_adj_str = get_txt("AMTADJ")
                rfnd_amt_str = get_txt("RFNDAMT")
                dp_client_id = get_txt("DPCLITID")
                refund_no = get_txt("RFNDNO")

                try:
                    shares_applied = int(float(shares_applied_str)) if shares_applied_str else 0
                except ValueError:
                    shares_applied = 0

                try:
                    shares_allotted = int(float(shares_allotted_str)) if shares_allotted_str else 0
                except ValueError:
                    shares_allotted = 0

                status_label = "ALLOTTED" if shares_allotted > 0 else "NOT ALLOTTED"

                results.append({
                    "company_name": company_name,
                    "applicant_name": applicant_name,
                    "category": category,
                    "shares_applied": shares_applied,
                    "shares_allotted": shares_allotted,
                    "cutoff_price": cutoff_price_str,
                    "amount_adjusted": amt_adj_str,
                    "refund_amount": rfnd_amt_str,
                    "dp_client_id": dp_client_id,
                    "refund_no": refund_no,
                    "allotment_status": status_label
                })

            return {
                "status": "success",
                "message": f"Found {len(results)} allotment record(s).",
                "results": results
            }

        except requests.RequestException as req_err:
            logger.error(f"Network error communicating with MUFG: {req_err}")
            return {
                "status": "error",
                "message": "Unable to connect to MUFG server. Please try again later.",
                "results": []
            }
        except Exception as e:
            logger.error(f"Error parsing MUFG allotment response: {e}", exc_info=True)
            return {
                "status": "error",
                "message": "An unexpected error occurred while processing your request.",
                "results": []
            }
