import logging
import requests
import re
import json
from typing import List, Dict, Any, Optional
from .base import BaseRegistrar

logger = logging.getLogger(__name__)

class KFintechRegistrar(BaseRegistrar):
    """
    Integration for KFintech IPO Allotment Portal (ipostatus.kfintech.com).
    """

    BASE_URL = "https://ipostatus.kfintech.com/"
    API_QUERY_URL = "https://0uz601ms56.execute-api.ap-south-1.amazonaws.com/prod/api/query?type="

    @property
    def slug(self) -> str:
        return "kfintech"

    @property
    def name(self) -> str:
        return "KFintech"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://ipostatus.kfintech.com",
            "Referer": "https://ipostatus.kfintech.com/"
        }

    def get_active_ipos(self) -> List[Dict[str, Any]]:
        """
        Fetches active IPO list dynamically from KFintech portal JS bundle.
        """
        headers = self._get_headers()
        try:
            res = requests.get(self.BASE_URL, headers=headers, timeout=10)
            if res.status_code != 200:
                logger.error(f"KFintech main page failed with status {res.status_code}")
                return []

            js_files = re.findall(r'src="(\./static/js/[^"]+)"', res.text)
            if not js_files:
                return []

            js_url = self.BASE_URL + js_files[0].lstrip("./")
            r = requests.get(js_url, headers=headers, timeout=10)
            if r.status_code != 200:
                return []

            match = re.search(r'rf=JSON\.parse\(\'([^\']+)\'\)', r.text)
            if not match:
                match = re.search(r'JSON\.parse\(\'(\[\{"clientId"[^\']+\\]?)\'\)', r.text)

            if not match:
                return []

            json_str = match.group(1)
            raw_ipos = json.loads(json_str)

            companies = []
            for item in raw_ipos:
                cid = item.get("clientId", "")
                cname = item.get("name", "")
                if cid and cname:
                    companies.append({
                        "id": str(cid).strip(),
                        "name": str(cname).strip(),
                        "registrar": self.slug,
                        "registrar_name": self.name
                    })
            return companies
        except Exception as e:
            logger.error(f"Error fetching KFintech IPO list: {e}", exc_info=True)
            return []

    def check_allotment_status(
        self, 
        company_id: str, 
        search_type: str, 
        search_value: str, 
        ifsc: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Checks allotment status on KFintech portal via AWS API Gateway endpoint.
        """
        search_type_upper = (search_type or "").upper().strip()

        if search_type_upper in ["PAN", "1"]:
            query_type = "pan"
        elif search_type_upper in ["APP", "APPLICATION", "2"]:
            query_type = "app_no"
        elif search_type_upper in ["DP", "DPID", "CLIENT", "OTHER", "3"]:
            query_type = "dpid"
        else:
            query_type = "pan"

        clean_value = str(search_value or "").strip().upper()
        if not clean_value:
            return {
                "status": "error",
                "message": "Search input value cannot be blank.",
                "results": []
            }

        headers = self._get_headers()
        headers["reqparam"] = clean_value
        headers["client_id"] = str(company_id).strip()

        url = self.API_QUERY_URL + query_type

        try:
            resp = requests.get(url, headers=headers, timeout=12)

            if resp.status_code == 404:
                return {
                    "status": "success",
                    "message": "No allotment record found for the given details.",
                    "results": []
                }

            if resp.status_code != 200:
                err_data = {}
                try:
                    err_data = resp.json()
                except Exception:
                    pass
                msg = err_data.get("error") or err_data.get("message") or f"Server error ({resp.status_code})"
                if "not found" in str(msg).lower():
                    return {
                        "status": "success",
                        "message": "No allotment record found for the given details.",
                        "results": []
                    }
                return {
                    "status": "error",
                    "message": f"KFintech portal message: {msg}",
                    "results": []
                }

            res_json = resp.json()
            if isinstance(res_json, dict) and "data" in res_json:
                records = res_json["data"]
            elif isinstance(res_json, list):
                records = res_json
            else:
                records = [res_json]

            if not records:
                return {
                    "status": "success",
                    "message": "No allotment record found for the given details.",
                    "results": []
                }

            results = []
            for item in records:
                if not isinstance(item, dict):
                    continue
                
                if item.get("error"):
                    msg = item.get("error")
                    if "not found" in str(msg).lower():
                        return {
                            "status": "success",
                            "message": "No allotment record found for the given details.",
                            "results": []
                        }

                applicant_name = item.get("Name") or item.get("NAME") or item.get("applicant_name") or "Sole Applicant"
                app_no = item.get("Appln_No") or item.get("app_no") or item.get("application_no") or ""
                dp_clid = item.get("DP_CLID") or item.get("DPCLITID") or item.get("dpid") or ""
                pan_no = item.get("Pan_No") or item.get("PAN") or ""
                category = item.get("category") or item.get("cat") or "Retail"
                
                shares_applied_str = item.get("App_Shares") or item.get("SHARES") or item.get("applied") or 0
                shares_allotted_str = item.get("All_Shares") or item.get("ALLOT") or item.get("allotted") or 0
                
                try:
                    shares_applied = int(float(shares_applied_str))
                except (ValueError, TypeError):
                    shares_applied = 0

                try:
                    shares_allotted = int(float(shares_allotted_str))
                except (ValueError, TypeError):
                    shares_allotted = 0

                status_label = "ALLOTTED" if shares_allotted > 0 else "NOT ALLOTTED"

                masked_pan = f"XXXXXX{pan_no[-4:]}" if len(pan_no) >= 10 else pan_no

                results.append({
                    "company_name": item.get("ipoTitle") or item.get("company_name") or "",
                    "applicant_name": applicant_name,
                    "appln_no": app_no,
                    "pan_no": masked_pan,
                    "category": category,
                    "shares_applied": shares_applied,
                    "shares_allotted": shares_allotted,
                    "cutoff_price": str(item.get("price") or item.get("cutoff") or "N/A"),
                    "amount_adjusted": str(item.get("amt_adj") or item.get("amount_adjusted") or "0"),
                    "refund_amount": str(item.get("refund") or item.get("RFNDAMT") or "0"),
                    "dp_client_id": dp_clid if dp_clid else "N/A",
                    "refund_no": str(item.get("ref_no") or item.get("RFNDNO") or "N/A"),
                    "allotment_status": status_label
                })

            return {
                "status": "success",
                "message": f"Found {len(results)} allotment record(s).",
                "results": results
            }

        except requests.RequestException as req_err:
            logger.error(f"Network error communicating with KFintech: {req_err}")
            return {
                "status": "error",
                "message": "Unable to connect to KFintech server. Please try again later.",
                "results": []
            }
        except Exception as e:
            logger.error(f"Error checking KFintech allotment status: {e}", exc_info=True)
            return {
                "status": "error",
                "message": "An unexpected error occurred while processing your KFintech request.",
                "results": []
            }
