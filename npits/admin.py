from django.contrib import admin
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
    list_display = ('title', 'brand', 'category', 'capacity', 'price', 'original_price', 'rating', 'is_featured', 'is_active')
    list_filter = ('category', 'brand', 'capacity', 'is_featured', 'is_active')
    search_fields = ('title', 'brand', 'asin', 'short_description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [NPITSAffiliateLinkInline]

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
