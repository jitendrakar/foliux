import abc
from typing import List, Dict, Any, Optional

class BaseRegistrar(abc.ABC):
    """
    Abstract Base Class for IPO Registrars (MUFG, Link Intime, KFintech, Bigshare, etc.).
    All registrar integration classes must inherit from this base class.
    """

    @property
    @abc.abstractmethod
    def slug(self) -> str:
        """Unique slug identifier for the registrar (e.g., 'mufg', 'kfintech', 'linkintime')."""
        pass

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Display name of the registrar (e.g., 'MUFG Intime', 'KFin Technologies')."""
        pass

    @abc.abstractmethod
    def get_active_ipos(self) -> List[Dict[str, Any]]:
        """
        Fetch active IPOs dynamically from the registrar's portal.
        Returns:
            List of dicts: [{'id': str, 'name': str, 'registrar': str}]
        """
        pass

    @abc.abstractmethod
    def check_allotment_status(
        self, 
        company_id: str, 
        search_type: str, 
        search_value: str, 
        ifsc: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check allotment status for a given company and identifier.
        
        Args:
            company_id: Registrar's internal ID for the company/issue.
            search_type: 'PAN', 'APP' (Application Number), 'DP' (DP/Client ID), or 'ACC' (Account Number).
            search_value: The identifier value entered by user.
            ifsc: IFSC Code if search_type == 'ACC'.

        Returns:
            Dict containing status ('success'|'error'), message, and parsed allotment results list.
        """
        pass
