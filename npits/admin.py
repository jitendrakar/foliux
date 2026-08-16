from django.contrib import admin
from django.utils.html import format_html
from .models import (
    NPITSConfig, NPITSCategory, NPITSProduct, 
    NPITSAffiliateLink, NPITSArticle, NPITSSeoLanding
)

class NPITSAffiliateLinkInline(admin.TabularInline):
    model = NPITSAffiliateLink
    extra = 1

@admin.register(NPITSConfig)
class NPITSConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'description')
    search_fields = ('key', 'value', 'description')

@admin.register(NPITSCategory)
class NPITSCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_featured', 'order')
    list_filter = ('is_featured', 'parent')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(NPITSProduct)
class NPITSProductAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'title', 'brand', 'category', 'price', 'is_featured', 'test_meesho_link', 'test_affiliate_link', 'is_active')
    list_filter = ('is_featured', 'category', 'brand', 'capacity', 'is_active')
    search_fields = ('title', 'brand', 'asin', 'short_description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [NPITSAffiliateLinkInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'brand', 'category', 'capacity', 'is_featured', 'is_active')
        }),
        ('Pricing & Ratings', {
            'fields': ('price', 'original_price', 'rating', 'review_count')
        }),
        ('Product Image (Upload or External URL)', {
            'fields': ('image', 'image_url'),
            'description': 'Upload a local image file directly from your computer, or paste an external image URL.'
        }),
        ('Store Links (Meesho, Amazon, Flipkart)', {
            'fields': ('meesho_url', 'amazon_url', 'flipkart_url', 'asin'),
            'description': 'Specify direct Meesho Product URL (NPITS Official Store - Preferred), Amazon URL/ASIN, or Flipkart URL.'
        }),
        ('Details & Specifications', {
            'classes': ('collapse',),
            'fields': ('short_description', 'features', 'specifications', 'pros', 'cons', 'meta_title', 'meta_description')
        }),
    )

    def image_preview(self, obj):
        url = obj.get_image_url
        return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: contain; border-radius: 4px; border: 1px solid #ccc; background: #fff;" onerror="this.src=\'data:image/svg+xml;utf8,<svg xmlns=\\\'http://www.w3.org/2000/svg\\\' width=\\\'50\\\' height=\\\'50\\\'><rect width=\\\'100%\\\' height=\\\'100%\\\' fill=\\\'%23eee\\\'/><text x=\\\'50%\\\' y=\\\'50%\\\' dominant-baseline=\\\'middle\\\' text-anchor=\\\'middle\\\' fill=\\\'%23aaa\\\'>No Img</text></svg>\';" />', url)
    image_preview.short_description = "Image"

    def test_meesho_link(self, obj):
        url = obj.get_tracked_meesho_url()
        if not url:
            return format_html('<span style="color: #999; font-size: 11px;">No Meesho Link</span>')
        return format_html(
            '<a href="{}" target="_blank" style="background-color: #9f208c; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 4px 10px; text-decoration: none; display: inline-block; font-size: 11px;">🛍️ Meesho (NPITS)</a>',
            url
        )
    test_meesho_link.short_description = "Meesho Link"

    def test_affiliate_link(self, obj):
        url = obj.get_tracked_amazon_url()
        return format_html(
            '<a href="{}" target="_blank" style="background-color: #ff9900; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 4px 10px; text-decoration: none; display: inline-block; font-size: 11px;">🛒 Amazon Link</a>',
            url
        )
    test_affiliate_link.short_description = "Amazon Link"

@admin.register(NPITSAffiliateLink)
class NPITSAffiliateLinkAdmin(admin.ModelAdmin):
    list_display = ('product', 'provider', 'price', 'in_stock', 'is_primary')
    list_filter = ('provider', 'in_stock', 'is_primary')
    search_fields = ('product__title', 'raw_url', 'affiliate_tag')

@admin.register(NPITSArticle)
class NPITSArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_published', 'published_at')
    list_filter = ('is_published', 'category')
    search_fields = ('title', 'summary', 'content')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(NPITSSeoLanding)
class NPITSSeoLandingAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'target_category', 'max_price', 'capacity_filter')
    search_fields = ('title', 'slug', 'h1_title', 'meta_title')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('featured_products',)
