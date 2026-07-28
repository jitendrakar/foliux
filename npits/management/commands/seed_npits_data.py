import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from npits.models import (
    NPITSConfig, NPITSCategory, NPITSProduct, 
    NPITSAffiliateLink, NPITSArticle, NPITSSeoLanding
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Seeds initial 21 IT categories, products, affiliate config (npits09-21), SEO landing pages, and buying guides.'

    def handle(self, *args, **options):
        self.stdout.write("Starting NPITS data seeding...")

        # 1. Config
        NPITSConfig.objects.get_or_create(
            key="AMAZON_ASSOCIATE_ID",
            defaults={
                "value": "npits09-21",
                "description": "Amazon India Associates Tag for conversion tracking"
            }
        )
        self.stdout.write(self.style.SUCCESS("Configured AMAZON_ASSOCIATE_ID = npits09-21"))

        # 2. Categories
        categories_data = [
            ("Internal Hard Disk (HDD)", "internal-hdd", "fas fa-hdd", 1),
            ("External Hard Disk", "external-hdd", "fas fa-database", 2),
            ("SSD (256GB, 512GB, 1TB, 2TB)", "ssd", "fas fa-memory", 3),
            ("NVMe SSD", "nvme-ssd", "fas fa-bolt", 4),
            ("RAM", "ram", "fas fa-microchip", 5),
            ("Pendrive", "pendrive", "fas fa-usb", 6),
            ("Memory Card", "memory-card", "fas fa-sd-card", 7),
            ("Monitor", "monitor", "fas fa-desktop", 8),
            ("Keyboard", "keyboard", "fas fa-keyboard", 9),
            ("Mouse", "mouse", "fas fa-mouse", 10),
            ("Webcam", "webcam", "fas fa-video", 11),
            ("Printer", "printer", "fas fa-print", 12),
            ("Router", "router", "fas fa-wifi", 13),
            ("Laptop", "laptop", "fas fa-laptop", 14),
            ("Desktop PC", "desktop-pc", "fas fa-tv", 15),
            ("UPS", "ups", "fas fa-battery-full", 16),
            ("Wi-Fi Adapter", "wifi-adapter", "fas fa-signal", 17),
            ("Graphics Card", "graphics-card", "fas fa-gamepad", 18),
            ("Processor", "processor", "fas fa-cogs", 19),
            ("Motherboard", "motherboard", "fas fa-layer-group", 20),
            ("Computer Accessories", "accessories", "fas fa-plug", 21),
        ]

        cat_objs = {}
        for name, slug, icon, order in categories_data:
            cat, created = NPITSCategory.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "icon_class": icon,
                    "order": order,
                    "is_featured": order <= 8,
                    "description": f"Compare and buy best {name} with latest Amazon India prices, user reviews, and technical specifications."
                }
            )
            cat_objs[slug] = cat
        self.stdout.write(self.style.SUCCESS(f"Created {len(cat_objs)} IT Product Categories."))

        # 3. Initial Products
        products_data = [
            # HDDs
            {
                "title": "Seagate Barracuda 1TB Internal Hard Drive HDD (ST1000DM010)",
                "category": cat_objs["internal-hdd"],
                "brand": "Seagate",
                "asin": "B01LNJBA2I",
                "price": 3899.00,
                "original_price": 4500.00,
                "rating": 4.5,
                "review_count": 3450,
                "capacity": "1TB",
                "image_url": "https://m.media-amazon.com/images/I/71C7-T-LBAL._SL1500_.jpg",
                "amazon_url": "https://www.amazon.in/dp/B01LNJBA2I",
                "short_description": "Versatile HDD for desktop PC storage with SATA 6Gb/s interface and 7200 RPM speed.",
                "features": ["1TB Capacity, 3.5-inch Form Factor", "SATA 6Gb/s Interface, 7200 RPM", "64MB Cache Memory for fast access", "2-Year Rescue Data Recovery Services"],
                "specifications": {"Capacity": "1TB", "RPM": "7200 RPM", "Cache": "64MB", "Interface": "SATA 6 Gb/s", "Form Factor": "3.5 Inch"},
                "pros": ["High reliability and durability", "7200 RPM performance", "Rescue data recovery included"],
                "cons": ["Slower than SSDs", "Requires 3.5-inch drive bay"],
                "is_featured": True
            },
            {
                "title": "Western Digital WD Digital Elements 1TB Portable External Hard Drive",
                "category": cat_objs["external-hdd"],
                "brand": "Western Digital",
                "asin": "B06VVT7G77",
                "price": 4999.00,
                "original_price": 6000.00,
                "rating": 4.6,
                "review_count": 8920,
                "capacity": "1TB",
                "image_url": "https://m.media-amazon.com/images/I/61ev46+7pWL._SL1500_.jpg",
                "amazon_url": "https://www.amazon.in/dp/B06VVT7G77",
                "short_description": "Plug-and-play USB 3.0 external hard drive for fast data transfers and backup.",
                "features": ["1TB High Capacity Storage", "USB 3.0 and USB 2.0 Compatibility", "Fast Data Transfer Speeds", "3-Year Limited Warranty"],
                "specifications": {"Capacity": "1TB", "Interface": "USB 3.0", "Weight": "130g", "Warranty": "3 Years"},
                "pros": ["Compact lightweight design", "Fast USB 3.0 speed", "Plug and play convenience"],
                "cons": ["Mechanical drive sensitive to heavy drops"],
                "is_featured": True
            },

            # SSDs & NVMe
            {
                "title": "Crucial BX500 512GB 2.5-inch SATA Internal SSD (CT512BX500SSD1)",
                "category": cat_objs["ssd"],
                "brand": "Crucial",
                "asin": "B07YD579WM",
                "price": 3299.00,
                "original_price": 4200.00,
                "rating": 4.6,
                "review_count": 12400,
                "capacity": "512GB",
                "image_url": "https://m.media-amazon.com/images/I/610t-E-G2WL._SL1000_.jpg",
                "amazon_url": "https://www.amazon.in/dp/B07YD579WM",
                "short_description": "Boost your laptop or desktop speed 300% faster than a traditional hard drive.",
                "features": ["512GB 2.5-inch SATA SSD", "Sequential Read up to 540 MB/s", "Improves boot time and overall system speed", "3-Year Micron Quality Warranty"],
                "specifications": {"Capacity": "512GB", "Read Speed": "540 MB/s", "Write Speed": "500 MB/s", "Interface": "SATA 6.0 Gb/s"},
                "pros": ["Excellent price-to-performance ratio", "Significantly faster boot times", "Low power consumption"],
                "cons": ["No DRAM cache"],
                "is_featured": True
            },
            {
                "title": "Crucial P3 1TB PCIe 3.0 3D NAND NVMe M.2 SSD (CT1000P3SSD8)",
                "category": cat_objs["nvme-ssd"],
                "brand": "Crucial",
                "asin": "B0B25LZGGW",
                "price": 5899.00,
                "original_price": 7500.00,
                "rating": 4.7,
                "review_count": 15800,
                "capacity": "1TB",
                "image_url": "https://m.media-amazon.com/images/I/61f9LStP-qL._SL1000_.jpg",
                "amazon_url": "https://www.amazon.in/dp/B0B25LZGGW",
                "short_description": "Ultra-fast NVMe M.2 SSD with sequential reads up to 3500MB/s for gaming and editing.",
                "features": ["1TB M.2 2280 NVMe SSD", "Up to 3,500 MB/s Read Speed", "6x Faster than SATA SSDs", "5-Year Limited Warranty"],
                "specifications": {"Capacity": "1TB", "Read Speed": "3500 MB/s", "Write Speed": "3000 MB/s", "Form Factor": "M.2 2280"},
                "pros": ["Extreme NVMe PCIe Gen3 speeds", "5-year long warranty", "Ultra-thin M.2 design"],
                "cons": ["Requires M.2 slot on motherboard"],
                "is_featured": True
            },
            {
                "title": "Samsung 980 1TB PCIe 3.0 NVMe M.2 SSD (MZ-V8V1T0BW)",
                "category": cat_objs["nvme-ssd"],
                "brand": "Samsung",
                "asin": "B08TJ2649W",
                "price": 7499.00,
                "original_price": 9999.00,
                "rating": 4.8,
                "review_count": 9400,
                "capacity": "1TB",
                "image_url": "https://m.media-amazon.com/images/I/8157B5-8JXL._SL1500_.jpg",
                "amazon_url": "https://www.amazon.in/dp/B08TJ2649W",
                "short_description": "Upgrade to non-stop speed with Samsung V-NAND technology and thermal control.",
                "features": ["1TB NVMe M.2 2280 SSD", "Read speeds up to 3,500 MB/s", "Full Power Mode for maximum gaming performance", "5-Year Warranty"],
                "specifications": {"Capacity": "1TB", "Read Speed": "3500 MB/s", "Write Speed": "3000 MB/s", "NAND": "Samsung V-NAND"},
                "pros": ["Samsung reliable V-NAND performance", "Full Power Mode via Samsung Magician", "Advanced thermal guard"],
                "cons": ["Premium pricing"],
                "is_featured": True
            },

            # Peripherals & Monitors
            {
                "title": "Logitech G102 Light Sync Gaming Mouse with Custom RGB Lighting",
                "category": cat_objs["mouse"],
                "brand": "Logitech",
                "asin": "B08728F2KZ",
                "price": 1495.00,
                "original_price": 1995.00,
                "rating": 4.5,
                "review_count": 21000,
                "image_url": "https://m.media-amazon.com/images/I/61UxfWn616L._SL1500_.jpg",
                "amazon_url": "https://www.amazon.in/dp/B08728F2KZ",
                "short_description": "Gaming-grade 8000 DPI sensor mouse with 16.8M color RGB LIGHTSYNC and 6 programmable buttons.",
                "features": ["8,000 DPI Gaming Grade Sensor", "LIGHTSYNC RGB Color Wave", "Classic 6-Button Gaming Design", "Mechanical Button Tensioning"],
                "specifications": {"DPI": "8000 DPI", "Buttons": "6", "Lighting": "RGB LIGHTSYNC", "Cable": "1.8m"},
                "pros": ["Highly accurate 8000 DPI sensor", "Comfortable ergonomic grip", "Customizable RGB lighting"],
                "cons": ["Wired mouse"],
                "is_featured": True
            },
            {
                "title": "Redragon K552 Kumara Mechanical Gaming Keyboard with RGB Switches",
                "category": cat_objs["keyboard"],
                "brand": "Redragon",
                "asin": "B016MAK38U",
                "price": 2899.00,
                "original_price": 3999.00,
                "rating": 4.6,
                "review_count": 7800,
                "image_url": "https://m.media-amazon.com/images/I/61Xz-8t0k-L._SL1200_.jpg",
                "amazon_url": "https://www.amazon.in/dp/B016MAK38U",
                "short_description": "Compact 87 key mechanical keyboard with custom mechanical switches and dust-proof design.",
                "features": ["Compact Tenkeyless 87-Key Design", "Custom Mechanical Dust-Proof Switches", "Rainbow LED Backlit Keys", "Metal-ABS Construction"],
                "specifications": {"Keys": "87 TKL", "Switch": "Custom Blue Mechanical", "Backlight": "RGB", "Connection": "USB Wired"},
                "pros": ["Satisfying clicky mechanical feedback", "Solid metal plate construction", "Compact TKL space-saving layout"],
                "cons": ["Clicky switches may be loud for quiet offices"],
                "is_featured": True
            },
            {
                "title": "Acer EK220Q 21.5 Inch Full HD IPS Monitor with 100Hz Refresh Rate",
                "category": cat_objs["monitor"],
                "brand": "Acer",
                "asin": "B0C9R85PZJ",
                "price": 5499.00,
                "original_price": 8999.00,
                "rating": 4.4,
                "review_count": 3100,
                "image_url": "https://m.media-amazon.com/images/I/81vR11rS4aL._SL1500_.jpg",
                "amazon_url": "https://www.amazon.in/dp/B0C9R85PZJ",
                "short_description": "21.5 inch Full HD monitor with IPS panel, 100Hz refresh rate, 1ms VRB, and Eye Care technology.",
                "features": ["21.5 Inch Full HD (1920x1080) IPS Display", "100Hz Refresh Rate, 1ms VRB Response Time", "HDMI & VGA Ports", "Flickerless & BlueLightShield Eye Protection"],
                "specifications": {"Screen Size": "21.5 Inch", "Panel": "IPS", "Resolution": "1920 x 1080", "Refresh Rate": "100Hz", "Ports": "HDMI, VGA"},
                "pros": ["Crisp IPS panel colors", "Smooth 100Hz refresh rate", "Ultra affordable price under ₹6,000"],
                "cons": ["No built-in speakers"],
                "is_featured": True
            },

            # Printers & Laptops
            {
                "title": "HP Smart Tank 585 All-in-One WiFi Color Printer with Auto-Ink Sensor",
                "category": cat_objs["printer"],
                "brand": "HP",
                "asin": "B0BSRD2G77",
                "price": 12999.00,
                "original_price": 15999.00,
                "rating": 4.3,
                "review_count": 4200,
                "image_url": "https://m.media-amazon.com/images/I/61r5f8z9HUL._SL1500_.jpg",
                "amazon_url": "https://www.amazon.in/dp/B0BSRD2G77",
                "short_description": "High-volume color printing, scanning, and copying with wireless Wi-Fi and low cost per page.",
                "features": ["Print, Scan, Copy with Self-Healing Wi-Fi", "Up to 6,000 Black / 6,000 Color Pages in Box", "Smart App Print & Scan from Mobile", "1-Year HP Warranty"],
                "specifications": {"Type": "Ink Tank All-in-One", "Connectivity": "Wi-Fi, USB 2.0, Bluetooth", "Print Speed": "12 ppm (Black)", "Warranty": "1 Year"},
                "pros": ["Extremely low cost per page print", "Wireless mobile printing via HP Smart App", "Includes 6000 page ink refill"],
                "cons": ["Higher upfront cost"],
                "is_featured": True
            },
            {
                "title": "ASUS Vivobook 15 Intel Core i3-1215U 12th Gen 15.6 inch FHD Laptop (8GB/512GB SSD)",
                "category": cat_objs["laptop"],
                "brand": "ASUS",
                "asin": "B0C5N4L2Q4",
                "price": 36990.00,
                "original_price": 49990.00,
                "rating": 4.4,
                "review_count": 2800,
                "capacity": "512GB",
                "image_url": "https://m.media-amazon.com/images/I/71c5W9NxN5L._SL1500_.jpg",
                "amazon_url": "https://www.amazon.in/dp/B0C5N4L2Q4",
                "short_description": "Thin and light 12th Gen Intel Core i3 laptop with 8GB RAM, 512GB NVMe SSD, and Windows 11.",
                "features": ["12th Gen Intel Core i3-1215U Processor", "8GB DDR4 RAM & 512GB M.2 NVMe SSD", "15.6-inch Full HD Anti-Glare Display", "Windows 11 Home & MS Office 2021"],
                "specifications": {"Processor": "Intel Core i3-1215U", "RAM": "8GB DDR4", "Storage": "512GB NVMe SSD", "Display": "15.6 FHD", "Weight": "1.7 kg"},
                "pros": ["Powerful 6-core 12th Gen Intel processor", "Pre-installed MS Office 2021", "Sleek 180-degree hinge design"],
                "cons": ["Integrated Intel UHD Graphics"],
                "is_featured": True
            }
        ]

        for pdata in products_data:
            prod, created = NPITSProduct.objects.get_or_create(
                asin=pdata["asin"],
                defaults={
                    "title": pdata["title"],
                    "slug": slugify(pdata["title"]),
                    "category": pdata["category"],
                    "brand": pdata["brand"],
                    "price": pdata["price"],
                    "original_price": pdata["original_price"],
                    "rating": pdata["rating"],
                    "review_count": pdata["review_count"],
                    "capacity": pdata.get("capacity", ""),
                    "image_url": pdata["image_url"],
                    "amazon_url": pdata["amazon_url"],
                    "short_description": pdata["short_description"],
                    "features": pdata["features"],
                    "specifications": pdata["specifications"],
                    "pros": pdata["pros"],
                    "cons": pdata["cons"],
                    "is_featured": pdata["is_featured"],
                    "is_active": True
                }
            )

            # Create primary affiliate link record
            NPITSAffiliateLink.objects.get_or_create(
                product=prod,
                provider="amazon",
                defaults={
                    "raw_url": pdata["amazon_url"],
                    "affiliate_tag": "npits09-21",
                    "price": pdata["price"],
                    "in_stock": True,
                    "is_primary": True
                }
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded initial {len(products_data)} products with tracked affiliate links (npits09-21)."))

        # 4. SEO Landing Pages
        seo_landings_data = [
            ("Best 1TB HDD", "best-1tb-hdd", "Best 1TB Internal & External Hard Drives in India", cat_objs["internal-hdd"], "1TB", None),
            ("Best 512GB SSD", "best-512gb-ssd", "Best 512GB SATA & NVMe SSDs for Fast Laptop & PC Speed", cat_objs["ssd"], "512GB", None),
            ("Best 1TB SSD", "best-1tb-ssd", "Best 1TB High Speed M.2 NVMe SSDs in India", cat_objs["nvme-ssd"], "1TB", None),
            ("Best Gaming Mouse", "best-gaming-mouse", "Best Gaming Mice with High DPI & RGB Lighting", cat_objs["mouse"], "", None),
            ("Best Mechanical Keyboard", "best-mechanical-keyboard", "Best Tactile Mechanical Keyboards for Gaming & Typing", cat_objs["keyboard"], "", None),
            ("Best Monitor under ₹10,000", "best-monitor-under-10000", "Best Full HD IPS Monitors under ₹10,000 in India", cat_objs["monitor"], "", 10000.00),
            ("Best Printer for Home", "best-printer-for-home", "Best Home & Small Office Ink Tank Printers", cat_objs["printer"], "", None),
            ("Best Laptop under ₹50,000", "best-laptop-under-50000", "Best Laptops under ₹50,000 for Work, Coding & Students", cat_objs["laptop"], "", 50000.00),
        ]

        for title, slug, h1, cat, cap, max_p in seo_landings_data:
            landing, created = NPITSSeoLanding.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "h1_title": h1,
                    "intro_text": f"Here is our expert curated list of the {title}. Compare prices on Amazon India, check real specifications, pros & cons, and get the best discount deals.",
                    "meta_title": f"{title} in India - Top Recommendations & Amazon Prices | FOLIUX NPITS",
                    "meta_description": f"Detailed buyer guide for {title}. Check specs, ratings, and price comparison on FOLIUX NPITS.",
                    "target_category": cat,
                    "capacity_filter": cap,
                    "max_price": max_p
                }
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(seo_landings_data)} SEO Landing Pages."))

        # 5. Articles & Buying Guides
        articles_data = [
            ("Best 1TB HDD in India (2026 Buying Guide)", "best-1tb-hdd-in-india", "Looking for extra computer storage? Here is the ultimate review of top 1TB internal and external HDDs with benchmark tests.", cat_objs["internal-hdd"]),
            ("Best SSD for Laptop: Upgrade Guide for 2026", "best-ssd-for-laptop", "Supercharge your old laptop by installing a high-speed 2.5-inch or NVMe M.2 SSD. Learn how to choose the right form factor.", cat_objs["ssd"]),
            ("HDD vs SSD: Which One Should You Buy?", "hdd-vs-ssd", "Understand the difference in speed, durability, price, and power efficiency between traditional Hard Disk Drives and Solid State Drives.", cat_objs["ssd"]),
            ("Best Gaming SSD: Gen3 vs Gen4 NVMe Performance Comparison", "best-gaming-ssd", "Reduce game load times to zero with the fastest PCIe 4.0 and 3.0 NVMe SSDs available on Amazon India.", cat_objs["nvme-ssd"]),
            ("Best External Hard Drive for Backups & Mac", "best-external-hard-drive", "Protect your valuable files and photos with the safest, fastest portable external hard drives.", cat_objs["external-hdd"]),
            ("How to Choose an SSD: DRAM vs DRAM-less, TLC vs QLC Explained", "how-to-choose-an-ssd", "Complete guide to SSD controllers, TBW endurance, DRAM caches, and NVMe speeds.", cat_objs["nvme-ssd"]),
        ]

        for title, slug, summary, cat in articles_data:
            NPITSArticle.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "summary": summary,
                    "category": cat,
                    "content": f"## {title}\n\n{summary}\n\n### Key Considerations\n\nWhen buying hardware in 2026, always check warranty, sequential read/write speeds, and Amazon customer reviews.\n\n### Our Top Pick\nCheck out the recommended products listed on FOLIUX NPITS with verified Amazon Associate links.",
                    "meta_title": f"{title} | FOLIUX NPITS Guide",
                    "meta_description": summary,
                    "is_published": True,
                    "published_at": timezone.now()
                }
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(articles_data)} Buying Guides & Articles."))
        self.stdout.write(self.style.SUCCESS("NPITS Data Seeding Completed Successfully!"))
