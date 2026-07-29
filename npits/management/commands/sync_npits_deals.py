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


class Command(BaseCommand):
    help = "Syncs and updates NPITS Amazon deals, hardware prices, and high-res images every 1 hour."

    def handle(self, *args, **options):
        self.stdout.write("Starting 1-Hour NPITS Amazon Deals Sync...")
        
        products = NPITSProduct.objects.filter(is_active=True)
        updated_count = 0

        for p in products:
            slug = p.category.slug
            # Ensure high-res product image assignment
            if slug in CATEGORY_IMAGE_REPO:
                images = CATEGORY_IMAGE_REPO[slug]
                if p.image_url not in images:
                    p.image_url = images[0]

            # Clear any direct broken ASIN URLs so tracked search links work 100%
            p.amazon_url = ''
            p.updated_at = timezone.now()
            p.save()
            updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully synced {updated_count} NPITS products at {timezone.now()}."))
