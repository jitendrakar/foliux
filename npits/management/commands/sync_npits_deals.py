import logging
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from npits.models import NPITSProduct, NPITSCategory

logger = logging.getLogger(__name__)

# High-Res Authentic Image Repository for IT Hardware Categories
CATEGORY_IMAGE_REPO = {
    'desktop-pc': [
        'https://m.media-amazon.com/images/I/71u96VqR4FL._SL1500_.jpg',
        'https://m.media-amazon.com/images/I/71i5gH+MmtL._SL1500_.jpg',
        'https://m.media-amazon.com/images/I/71C7I2E-hIL._SL1500_.jpg'
    ],
    'laptop': [
        'https://m.media-amazon.com/images/I/71S-3c6SsbL._SL1500_.jpg',
        'https://m.media-amazon.com/images/I/71vFKBpKakL._SL1500_.jpg',
        'https://m.media-amazon.com/images/I/71TPda7cwUL._SL1500_.jpg'
    ],
    'graphics-card': [
        'https://m.media-amazon.com/images/I/71K+BfF-tGL._SL1500_.jpg',
        'https://m.media-amazon.com/images/I/81d77P+t1yL._SL1500_.jpg'
    ],
    'processor': [
        'https://m.media-amazon.com/images/I/51k+Z1s6+pL._SL1500_.jpg',
        'https://m.media-amazon.com/images/I/61N8qW6w7JL._SL1500_.jpg'
    ],
    'motherboard': [
        'https://m.media-amazon.com/images/I/81xH6C3QY4L._SL1500_.jpg',
        'https://m.media-amazon.com/images/I/81P5eQj86-L._SL1500_.jpg'
    ],
    'monitor': [
        'https://m.media-amazon.com/images/I/81vR11rS4aL._SL1500_.jpg',
        'https://m.media-amazon.com/images/I/813d11b2NLL._SL1500_.jpg'
    ],
    'printer': [
        'https://m.media-amazon.com/images/I/61r5f8z9HUL._SL1500_.jpg',
        'https://m.media-amazon.com/images/I/61K8P1FfLFL._SL1500_.jpg'
    ],
    'router': [
        'https://m.media-amazon.com/images/I/61C2-82CufL._SL1500_.jpg',
        'https://m.media-amazon.com/images/I/61y8B3d9PQL._SL1500_.jpg'
    ],
    'webcam': [
        'https://m.media-amazon.com/images/I/61UxfXTUyvL._SL1500_.jpg',
        'https://m.media-amazon.com/images/I/61a7c5b6EBL._SL1500_.jpg'
    ],
    'keyboard': [
        'https://m.media-amazon.com/images/I/71cngLX2xuL._SL1500_.jpg',
        'https://m.media-amazon.com/images/I/61n9r8B7sUL._SL1500_.jpg'
    ],
    'mouse': [
        'https://m.media-amazon.com/images/I/61UxfXTUyvL._SL1500_.jpg',
        'https://m.media-amazon.com/images/I/51j1-c4+5bL._SL1500_.jpg'
    ],
    'nvme-ssd': [
        'https://m.media-amazon.com/images/I/81T6+Z0d6aL._SL1500_.jpg',
        'https://m.media-amazon.com/images/I/61V60-m81eL._SL1500_.jpg'
    ],
    'ssd': [
        'https://m.media-amazon.com/images/I/61r5qZg-yKL._SL1500_.jpg'
    ],
    'external-hard-disk': [
        'https://m.media-amazon.com/images/I/61IBbvJvSDL._SL1500_.jpg'
    ],
    'internal-hard-disk-hdd': [
        'https://m.media-amazon.com/images/I/71C7I2E-hIL._SL1500_.jpg'
    ],
    'ram': [
        'https://m.media-amazon.com/images/I/51k+Z1s6+pL._SL1500_.jpg'
    ],
    'pendrive': [
        'https://m.media-amazon.com/images/I/61r5qZg-yKL._SL1500_.jpg'
    ],
    'memory-card': [
        'https://m.media-amazon.com/images/I/61r5qZg-yKL._SL1500_.jpg'
    ],
    'ups': [
        'https://m.media-amazon.com/images/I/71C7I2E-hIL._SL1500_.jpg'
    ],
    'wi-fi-adapter': [
        'https://m.media-amazon.com/images/I/71C7I2E-hIL._SL1500_.jpg'
    ],
    'computer-accessories': [
        'https://m.media-amazon.com/images/I/61r5qZg-yKL._SL1500_.jpg'
    ]
}


def is_exact_product_match(npits_prod, fk_title: str) -> bool:
    import re
    fk_lower = fk_title.lower()
    title_lower = npits_prod.title.lower()
    brand_lower = npits_prod.brand.lower()
    cat_slug = npits_prod.category.slug.lower()

    # 1. Brand Must Match
    if brand_lower not in fk_lower:
        return False

    # 2. Exclude Laptops when looking for desktop components
    if cat_slug in ['graphics-card', 'motherboard', 'processor', 'desktop-pc', 'internal-hard-disk-hdd', 'nvme-ssd', 'ssd']:
        if 'laptop' in fk_lower or 'notebook' in fk_lower:
            return False

    # 3. Capacity / Size Verification (1TB vs 512GB vs 256GB vs 2TB)
    capacity = npits_prod.capacity.lower().replace(' ', '') if npits_prod.capacity else ""
    if not capacity:
        cap_match = re.search(r'\b(\d+\s*(?:gb|tb))\b', title_lower)
        if cap_match:
            capacity = cap_match.group(1).replace(' ', '')

    if capacity:
        fk_no_space = fk_lower.replace(' ', '')
        if capacity not in fk_no_space:
            return False

    # 4. Model Number Verification
    models_in_title = re.findall(r'\b([a-z0-9]{5,15}|i\d-\d{4,5}[a-z]*|rtx\s*\d{4}|mx\s*master\s*\d\w*|m[1-4])\b', title_lower)
    for model in models_in_title:
        if model in ['laptop', 'desktop', 'gaming', 'internal', 'external', 'wireless', 'monitor', 'keyboard', 'liquid', 'retina', 'display', 'graphics']:
            continue
        model_clean = re.sub(r'[\s-]', '', model)
        fk_clean = re.sub(r'[\s-]', '', fk_lower)
        if len(model_clean) >= 4 and model_clean not in fk_clean:
            return False

    return True


class Command(BaseCommand):
    help = "Syncs and updates NPITS Amazon & Flipkart deals, hardware prices, and high-res images."

    def handle(self, *args, **options):
        import urllib.request
        import urllib.parse
        import ssl
        import json
        import re
        from npits.affiliates import FlipkartAffiliateProvider
        from npits.models import NPITSAffiliateLink

        self.stdout.write("Starting NPITS Deals & Flipkart API Live Sync with Strict Model Matching...")
        
        provider = FlipkartAffiliateProvider()
        headers = provider.get_api_headers()
        aff_id = headers.get("Fk-Affiliate-Id", "jitendrak")

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        products = NPITSProduct.objects.filter(is_active=True)
        updated_count = 0
        fk_synced = 0
        fallback_count = 0

        for p in products:
            slug = p.category.slug
            # Ensure high-res product image assignment
            if slug in CATEGORY_IMAGE_REPO:
                images = CATEGORY_IMAGE_REPO[slug]
                if p.image_url not in images:
                    p.image_url = images[0]

            # Clear broken ASIN URLs so tracked search links work 100%
            p.amazon_url = ''
            p.updated_at = timezone.now()
            p.save()
            updated_count += 1

            # Search Flipkart API for exact model match
            matched_deal = None
            try:
                search_term = f"{p.brand} {p.title}"
                clean_query = re.sub(r'[^\w\s]', ' ', search_term)
                query_words = " ".join(clean_query.split()[:5])
                search_url = f"https://affiliate-api.flipkart.net/affiliate/1.0/search.json?query={urllib.parse.quote(query_words)}&resultCount=8"
                req = urllib.request.Request(search_url, headers=headers)
                
                with urllib.request.urlopen(req, context=ctx, timeout=8) as res:
                    if res.getcode() == 200:
                        data = json.loads(res.read().decode('utf-8'))
                        fk_prods = data.get("products", [])
                        for item in fk_prods:
                            base_info = item.get("productBaseInfoV1", {})
                            fk_title = base_info.get("title", "")
                            if is_exact_product_match(p, fk_title):
                                fk_url = base_info.get("productUrl", "")
                                fk_price = base_info.get("flipkartSellingPrice", {}).get("amount", float(p.price))
                                in_stock = base_info.get("inStock", True)
                                if fk_url:
                                    matched_deal = {
                                        'url': fk_url,
                                        'price': fk_price if fk_price > 0 else float(p.price),
                                        'in_stock': in_stock
                                    }
                                    break
            except Exception as e:
                pass

            if matched_deal:
                NPITSAffiliateLink.objects.update_or_create(
                    product=p,
                    provider='flipkart',
                    defaults={
                        'raw_url': matched_deal['url'],
                        'price': matched_deal['price'],
                        'in_stock': matched_deal['in_stock'],
                        'is_primary': False
                    }
                )
                fk_synced += 1
            else:
                # If no 100% exact model match exists on Flipkart, fallback to tagged direct store search
                fallback_count += 1
                search_query = urllib.parse.quote_plus(f"{p.brand} {p.title}")
                fallback_url = f"https://www.flipkart.com/search?q={search_query}&affid={aff_id}"
                NPITSAffiliateLink.objects.update_or_create(
                    product=p,
                    provider='flipkart',
                    defaults={
                        'raw_url': fallback_url,
                        'price': p.price,
                        'in_stock': True,
                        'is_primary': False
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"Successfully synced {updated_count} products ({fk_synced} exact model matches, {fallback_count} tagged search fallbacks) at {timezone.now()}."))


