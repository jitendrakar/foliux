import re
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

class NPITSConfig(models.Model):
    """Configuration settings for NPITS (e.g. AMAZON_ASSOCIATE_ID)."""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "NPITS Config Setting"
        verbose_name_plural = "NPITS Config Settings"

    def __str__(self):
        return f"{self.key} = {self.value}"

    @classmethod
    def get_setting(cls, key: str, default: str = "") -> str:
        try:
            cfg = cls.objects.filter(key=key).first()
            if cfg and cfg.value:
                return cfg.value.strip()
        except Exception:
            pass
        return default


class NPITSCategory(models.Model):
    """Product Categories for IT Hardware & Accessories."""
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    icon_class = models.CharField(max_length=50, default='fas fa-microchip', blank=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='subcategories')
    is_featured = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "IT Product Category"
        verbose_name_plural = "IT Product Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class NPITSProduct(models.Model):
    """Hardware & IT Product Model."""
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    brand = models.CharField(max_length=100, db_index=True)
    category = models.ForeignKey(NPITSCategory, on_delete=models.CASCADE, related_name='products')
    asin = models.CharField(max_length=20, blank=True, help_text="Amazon ASIN (e.g. B087NYAF9N)")
    image = models.ImageField(upload_to='npits/products/', blank=True, null=True, help_text="Upload local product image file (overrides external URL)")
    image_url = models.URLField(max_length=500, blank=True, help_text="Main product external image URL")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5)
    review_count = models.IntegerField(default=120)
    short_description = models.TextField(blank=True)
    features = models.JSONField(default=list, blank=True, help_text="List of feature bullet points")
    specifications = models.JSONField(default=dict, blank=True, help_text="Technical specifications key-values")
    pros = models.JSONField(default=list, blank=True, help_text="List of Pros")
    cons = models.JSONField(default=list, blank=True, help_text="List of Cons")
    capacity = models.CharField(max_length=50, blank=True, help_text="e.g., 256GB, 512GB, 1TB, 2TB")
    amazon_url = models.URLField(max_length=500, blank=True, help_text="Direct Amazon Product URL")
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-rating', '-price']
        verbose_name = "IT Product"
        verbose_name_plural = "IT Products"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def get_image_url(self) -> str:
        """Returns uploaded image URL if available, else external image_url, else default SVG placeholder."""
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        if self.image_url and self.image_url.strip():
            return self.image_url.strip()
        return "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 24 24' fill='none' stroke='%230d6efd' stroke-width='1.5'><rect x='2' y='3' width='20' height='14' rx='2'/><line x1='8' y1='21' x2='16' y2='21'/><line x1='12' y1='17' x2='12' y2='21'/></svg>"


    @property
    def discount_percent(self):
        if self.original_price and self.original_price > self.price > 0:
            diff = self.original_price - self.price
            pct = (diff / self.original_price) * 100
            return int(round(pct))
        return 0

    def get_tracked_amazon_url(self) -> str:
        """Returns Amazon India direct product URL formatted with active Associate ID.
        If a direct amazon_url or ASIN exists, links directly to the product with tag.
        Falls back to search query URL only if no direct link or ASIN is present.
        """
        import urllib.parse
        associate_id = NPITSConfig.get_setting('AMAZON_ASSOCIATE_ID', 'npits09-21')
        
        url = self.amazon_url.strip() if self.amazon_url else ""
        
        # 1. If explicit amazon_url is provided, append/replace associate tag
        if url:
            clean_url = re.sub(r'([?&])tag=[^&]*', r'\1', url).rstrip('?&')
            separator = '&' if '?' in clean_url else '?'
            return f"{clean_url}{separator}tag={associate_id}"
            
        # 2. If ASIN is provided, construct direct product page URL
        if self.asin and self.asin.strip():
            asin_clean = self.asin.strip()
            return f"https://www.amazon.in/dp/{asin_clean}?tag={associate_id}"

        # 3. Fallback: Amazon search query by product title
        clean_title = re.sub(r'[^\w\s-]', ' ', self.title)
        clean_title = " ".join(clean_title.split())
        query = urllib.parse.quote_plus(clean_title)
        return f"https://www.amazon.in/s?k={query}&tag={associate_id}"



class NPITSAffiliateLink(models.Model):
    """Affiliate Links for Products across Stores (Amazon, Flipkart, Croma, etc.)."""
    PROVIDER_CHOICES = [
        ('amazon', 'Amazon India'),
        ('flipkart', 'Flipkart'),
        ('croma', 'Croma'),
        ('reliance', 'Reliance Digital'),
        ('vijaysales', 'Vijay Sales'),
    ]

    product = models.ForeignKey(NPITSProduct, on_delete=models.CASCADE, related_name='affiliate_links')
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, default='amazon')
    raw_url = models.URLField(max_length=500)
    affiliate_tag = models.CharField(max_length=100, blank=True, help_text="Custom associate tag override")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    in_stock = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Affiliate Link"
        verbose_name_plural = "Affiliate Links"

    def __str__(self):
        return f"{self.product.title} - {self.get_provider_display()}"

    def get_final_url(self) -> str:
        if self.provider == 'amazon':
            return self.product.get_tracked_amazon_url()
        elif self.provider == 'flipkart':
            from .affiliates import get_affiliate_provider
            provider_obj = get_affiliate_provider('flipkart')
            tag = self.affiliate_tag if self.affiliate_tag else NPITSConfig.get_setting("FLIPKART_AFFILIATE_ID", "jitendrak")
            return provider_obj.build_affiliate_url(self.raw_url, tag)
        return self.raw_url


class NPITSArticle(models.Model):
    """Buying Guides and IT Articles."""
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    summary = models.TextField(blank=True)
    content = models.TextField()
    category = models.ForeignKey(NPITSCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name='articles')
    image_url = models.URLField(max_length=500, blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-published_at']
        verbose_name = "Buying Guide / Article"
        verbose_name_plural = "Buying Guides / Articles"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class NPITSSeoLanding(models.Model):
    """Curated SEO Landing Pages (e.g., best-1tb-hdd, best-512gb-ssd, best-laptop-under-50000)."""
    slug = models.SlugField(max_length=200, unique=True, help_text="URL slug e.g. best-1tb-hdd")
    title = models.CharField(max_length=255)
    h1_title = models.CharField(max_length=255)
    intro_text = models.TextField(blank=True)
    meta_title = models.CharField(max_length=255)
    meta_description = models.TextField(blank=True)
    target_category = models.ForeignKey(NPITSCategory, null=True, blank=True, on_delete=models.SET_NULL)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    capacity_filter = models.CharField(max_length=50, blank=True, help_text="e.g. 1TB, 512GB")
    featured_products = models.ManyToManyField(NPITSProduct, blank=True, related_name='seo_landings')

    class Meta:
        verbose_name = "SEO Landing Page"
        verbose_name_plural = "SEO Landing Pages"

    def __str__(self):
        return f"{self.title} (/{self.slug})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
