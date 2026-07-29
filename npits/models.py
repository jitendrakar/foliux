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
    image_url = models.URLField(max_length=500, blank=True, help_text="Main product image URL")
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
    def discount_percent(self):
        if self.original_price and self.original_price > self.price > 0:
            diff = self.original_price - self.price
            pct = (diff / self.original_price) * 100
            return int(round(pct))
        return 0

    def get_tracked_amazon_url(self) -> str:
        """Returns Amazon India URL formatted with current active Associate ID (npits09-21).
        Uses direct Amazon Search query by default or for /dp/ links to guarantee 100% working links with zero 404 errors.
        """
        import urllib.parse
        associate_id = NPITSConfig.get_setting('AMAZON_ASSOCIATE_ID', 'npits09-21')
        
        url = self.amazon_url.strip() if self.amazon_url else ""
        
        # If no explicit url or if it is a brittle /dp/ link, use guaranteed Amazon search query URL
        if not url or '/dp/' in url:
            clean_title = re.sub(r'[^\w\s-]', ' ', self.title)
            clean_title = " ".join(clean_title.split())
            query = urllib.parse.quote_plus(clean_title)
            return f"https://www.amazon.in/s?k={query}&tag={associate_id}"

        # Clean existing tag if present and attach active associate tag
        clean_url = re.sub(r'([?&])tag=[^&]*', r'\1', url).rstrip('?&')
        separator = '&' if '?' in clean_url else '?'
        return f"{clean_url}{separator}tag={associate_id}"


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
