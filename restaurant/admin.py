from django.contrib import admin
from .models import (
    RestaurantInfo, OpeningHour, SocialLink, Category, MenuItem,
    GalleryItem, Testimonial, Reservation, BlogPost, ContactMessage,
    NewsletterSubscription
)

# 1. Restaurant Information Admin
@admin.register(RestaurantInfo)
class RestaurantInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'tagline')
    
    # Restrict to only 1 entry in the admin to prevent duplicate restaurant profiles
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

# 2. Opening Hour Admin
@admin.register(OpeningHour)
class OpeningHourAdmin(admin.ModelAdmin):
    list_display = ('day', 'opens_at', 'closes_at', 'is_closed')
    list_editable = ('opens_at', 'closes_at', 'is_closed')
    list_filter = ('is_closed',)

# 3. Social Media Link Admin
@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ('platform', 'url', 'icon_class')
    list_editable = ('url', 'icon_class')

# 4. Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'display_order')
    list_editable = ('display_order',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

# 5. Menu Item Admin
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_veg', 'is_best_seller', 'is_available', 'is_chef_special')
    list_editable = ('price', 'is_veg', 'is_best_seller', 'is_available', 'is_chef_special')
    list_filter = ('category', 'is_veg', 'is_best_seller', 'is_available', 'is_chef_special')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')

# 6. Gallery Item Admin
@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'caption')
    list_filter = ('category',)
    search_fields = ('title', 'caption')

# 7. Testimonial Admin
@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'designation', 'rating', 'is_featured')
    list_editable = ('rating', 'is_featured')
    list_filter = ('rating', 'is_featured')
    search_fields = ('name', 'review_text')

# 8. Reservation Admin
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'date', 'time', 'guests', 'status')
    list_editable = ('status',)
    list_filter = ('status', 'date', 'guests')
    search_fields = ('name', 'phone', 'email', 'special_request')
    date_hierarchy = 'date'
    
    actions = ['confirm_reservations', 'cancel_reservations']
    
    def confirm_reservations(self, request, queryset):
        queryset.update(status='Confirmed')
        self.message_user(request, "Selected reservations have been marked as Confirmed.")
    confirm_reservations.short_description = "Mark selected reservations as Confirmed"
    
    def cancel_reservations(self, request, queryset):
        queryset.update(status='Cancelled')
        self.message_user(request, "Selected reservations have been marked as Cancelled.")
    cancel_reservations.short_description = "Mark selected reservations as Cancelled"

# 9. Blog Post Admin
@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at', 'is_published')
    list_editable = ('is_published',)
    list_filter = ('is_published', 'created_at')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'summary', 'content')
    date_hierarchy = 'created_at'

# 10. Contact Message Admin
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at', 'is_read')
    list_editable = ('is_read',)
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('name', 'email', 'phone', 'subject', 'message', 'created_at')
    date_hierarchy = 'created_at'
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, "Selected messages marked as read.")
    mark_as_read.short_description = "Mark selected messages as Read"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, "Selected messages marked as unread.")
    mark_as_unread.short_description = "Mark selected messages as Unread"

# 11. Newsletter Subscription Admin
@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')
    search_fields = ('email',)
    date_hierarchy = 'subscribed_at'
