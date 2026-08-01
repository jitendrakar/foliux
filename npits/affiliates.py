import abc
import re
from typing import Dict, Any

class BaseAffiliateProvider(abc.ABC):
    """
    Abstract Base Class for Affiliate Network Providers.
    Allows easy expansion for Flipkart, Croma, Reliance Digital, Vijay Sales, etc.
    """

    @property
    @abc.abstractmethod
    def provider_code(self) -> str:
        """Unique identifier code for the provider (e.g. 'amazon', 'flipkart')."""
        pass

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Display name of the store (e.g. 'Amazon India', 'Flipkart')."""
        pass

    @abc.abstractmethod
    def build_affiliate_url(self, raw_url: str, tracking_tag: str = "") -> str:
        """Transforms a raw product URL into a tracked affiliate link."""
        pass


class AmazonAffiliateProvider(BaseAffiliateProvider):
    """Amazon Associates Affiliate Provider Implementation."""

    @property
    def provider_code(self) -> str:
        return "amazon"

    @property
    def provider_name(self) -> str:
        return "Amazon India"

    def build_affiliate_url(self, raw_url: str, tracking_tag: str = "") -> str:
        if not tracking_tag:
            from .models import NPITSConfig
            tracking_tag = NPITSConfig.get_setting("AMAZON_ASSOCIATE_ID", "npits09-21")
        
        url = raw_url.strip() if raw_url else ""
        if not url:
            return ""

        # Clean any existing tag parameter
        clean_url = re.sub(r'([?&])tag=[^&]*', r'\1', url).rstrip('?&')
        sep = '&' if '?' in clean_url else '?'
        return f"{clean_url}{sep}tag={tracking_tag}"


class FlipkartAffiliateProvider(BaseAffiliateProvider):
    """Flipkart Affiliate Provider Implementation."""

    @property
    def provider_code(self) -> str:
        return "flipkart"

    @property
    def provider_name(self) -> str:
        return "Flipkart"

    def get_api_credentials(self) -> Dict[str, str]:
        from .models import NPITSConfig
        aff_id = NPITSConfig.get_setting("FLIPKART_AFFILIATE_ID", "jitendrak")
        api_token = NPITSConfig.get_setting("FLIPKART_API_TOKEN", "a79d042d8cb5434bb917c24b40d614a9")
        return {
            "affiliate_id": aff_id,
            "api_token": api_token
        }

    def get_api_headers(self) -> Dict[str, str]:
        creds = self.get_api_credentials()
        return {
            "Fk-Affiliate-Id": creds["affiliate_id"],
            "Fk-Affiliate-Token": creds["api_token"],
            "Accept": "application/json"
        }

    def build_affiliate_url(self, raw_url: str, tracking_tag: str = "") -> str:
        if not tracking_tag:
            from .models import NPITSConfig
            tracking_tag = NPITSConfig.get_setting("FLIPKART_AFFILIATE_ID", "jitendrak")
        
        url = raw_url.strip() if raw_url else ""
        if not url:
            return ""

        clean_url = re.sub(r'([?&])affid=[^&]*', r'\1', url).rstrip('?&')
        sep = '&' if '?' in clean_url else '?'
        return f"{clean_url}{sep}affid={tracking_tag}"


class GenericAffiliateProvider(BaseAffiliateProvider):
    """Generic Store Affiliate Provider."""

    @property
    def provider_code(self) -> str:
        return "generic"

    @property
    def provider_name(self) -> str:
        return "Online Store"

    def build_affiliate_url(self, raw_url: str, tracking_tag: str = "") -> str:
        return raw_url.strip() if raw_url else ""


# Provider Registry
AFFILIATE_PROVIDERS: Dict[str, BaseAffiliateProvider] = {
    "amazon": AmazonAffiliateProvider(),
    "flipkart": FlipkartAffiliateProvider(),
    "generic": GenericAffiliateProvider()
}

def get_affiliate_provider(code: str) -> BaseAffiliateProvider:
    return AFFILIATE_PROVIDERS.get(code.lower(), GenericAffiliateProvider())

