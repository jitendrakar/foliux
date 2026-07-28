import logging
from typing import Dict, List, Any, Optional
from .base import BaseRegistrar
from .mufg import MUFGRegistrar
from .kfintech import KFintechRegistrar

logger = logging.getLogger(__name__)

class RegistrarRegistry:
    """
    Central Registry for managing registrar integrations.
    Allows easy expansion for future registrars (MUFG, KFintech, Link Intime, Bigshare, etc.).
    """

    def __init__(self):
        self._registrars: Dict[str, BaseRegistrar] = {}

    def register(self, registrar: BaseRegistrar) -> None:
        """Register a new registrar instance."""
        slug = registrar.slug.lower()
        self._registrars[slug] = registrar
        logger.info(f"Registered IPO registrar: '{registrar.name}' ({slug})")

    def get_registrar(self, slug: str) -> Optional[BaseRegistrar]:
        """Retrieve registrar instance by slug."""
        return self._registrars.get((slug or "mufg").lower())

    def get_all_registrars(self) -> List[Dict[str, str]]:
        """Get list of registered registrars."""
        return [
            {"slug": reg.slug, "name": reg.name}
            for reg in self._registrars.values()
        ]

    def get_all_active_ipos(self) -> List[Dict[str, Any]]:
        """
        Fetch active IPOs across all registered registrars.
        Returns combined list of company dicts.
        """
        combined_list = []
        for slug, registrar in self._registrars.items():
            try:
                ipos = registrar.get_active_ipos()
                combined_list.extend(ipos)
            except Exception as e:
                logger.error(f"Error fetching IPO list from registrar '{slug}': {e}")
        return combined_list


# Singleton Registry Instance
registrar_registry = RegistrarRegistry()

# Register active registrars
registrar_registry.register(MUFGRegistrar())
registrar_registry.register(KFintechRegistrar())

def get_registrar(slug: str = "mufg") -> Optional[BaseRegistrar]:
    return registrar_registry.get_registrar(slug)
