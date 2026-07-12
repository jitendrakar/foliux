from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator

class RestaurantInfo(models.Model):
    name = models.CharField(max_length=100, default="L'Étoile Dorée")
    logo = models.ImageField(upload_to='restaurant_info/', blank=True, null=True)
    tagline = models.CharField(max_length=200, default="Fine Dining & Culinary Excellence")
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    whatsapp_number = models.CharField(max_length=20, blank=True, help_text="Enter number with country code, e.g. +123456789")
    about_text = models.TextField(help_text="Detailed story for the About section")
    google_maps_iframe = models.TextField(blank=True, help_text="Embed iframe src or complete iframe code from Google Maps")
    
    class Meta:
        verbose_name = "Restaurant Information"
        verbose_name_plural = "Restaurant Information"

    def __str__(self):
        return self.name

class OpeningHour(models.Model):
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]
    day = models.CharField(max_length=15, choices=DAY_CHOICES, unique=True)
    opens_at = models.TimeField(blank=True, null=True)
    closes_at = models.TimeField(blank=True, null=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']

    def __str__(self):
        if self.is_closed:
            return f"{self.day}: Closed"
        return f"{self.day}: {self.opens_at.strftime('%I:%M %p')} - {self.closes_at.strftime('%I:%M %p')}"

class SocialLink(models.Model):
    PLATFORM_CHOICES = [
        ('Facebook', 'Facebook'),
        ('Instagram', 'Instagram'),
        ('Twitter', 'Twitter'),
        ('YouTube', 'YouTube'),
        ('TripAdvisor', 'TripAdvisor'),
        ('Yelp', 'Yelp'),
    ]
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES)
    url = models.URLField()
    icon_class = models.CharField(max_length=50, help_text="FontAwesome icon class, e.g., 'fa-brands fa-instagram'")

    def __str__(self):
        return self.platform

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/')
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['display_order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class MenuItem(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='menu/')
    is_veg = models.BooleanField(default=True, verbose_name="Is Vegetarian")
    is_best_seller = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    is_chef_special = models.BooleanField(default=False)

    class Meta:
        ordering = ['category', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class GalleryItem(models.Model):
    CATEGORY_CHOICES = [
        ('Food', 'Dishes & Drinks'),
        ('Ambiance', 'Restaurant Ambiance'),
        ('Chef', 'Chefs & Kitchen'),
    ]
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='gallery/')
    caption = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    def __str__(self):
        return f"{self.title} ({self.category})"

class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100, default="Valued Customer")
    review_text = models.TextField()
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=5)
    image = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    is_featured = models.BooleanField(default=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"{self.name} - {self.rating} Stars"

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
    ]
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    date = models.DateField()
    time = models.TimeField()
    guests = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    special_request = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    class Meta:
        ordering = ['-date', '-time']

    def __str__(self):
        return f"Reservation for {self.name} ({self.guests} guests) on {self.date} at {self.time}"

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    summary = models.TextField(help_text="Short excerpt displayed in blog list")
    content = models.TextField()
    image = models.ImageField(upload_to='blog/')
    author = models.CharField(max_length=100, default="Chef de Cuisine")
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=150)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"

class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
