from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

class SalonUser(models.Model):
    """
    Model for Salon Users (Admins and Customers) stored in salon_users.
    Uses custom session-based authentication to remain completely independent.
    """
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('customer', 'Customer'),
    )
    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  # Hashed password
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'salon_users'
        verbose_name = 'Salon User'
        verbose_name_plural = 'Salon Users'

    def __str__(self):
        return f"{self.name} ({self.role})"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


class SalonCategory(models.Model):
    """
    Model for Salon Categories stored in salon_categories.
    """
    category_name = models.CharField(max_length=100)
    status = models.BooleanField(default=True)

    class Meta:
        db_table = 'salon_categories'
        verbose_name = 'Salon Category'
        verbose_name_plural = 'Salon Categories'

    def __str__(self):
        return self.category_name


class SalonService(models.Model):
    """
    Model for Salon Services stored in salon_services.
    """
    category = models.ForeignKey(SalonCategory, on_delete=models.CASCADE, db_column='category_id', related_name='services')
    service_name = models.CharField(max_length=255)
    price = models.DecimalField(max_length=10, decimal_places=2, max_digits=10)
    duration = models.IntegerField(help_text="Duration in minutes")
    description = models.TextField()
    image = models.ImageField(upload_to='salon/services/', null=True, blank=True)
    status = models.BooleanField(default=True)

    class Meta:
        db_table = 'salon_services'
        verbose_name = 'Salon Service'
        verbose_name_plural = 'Salon Services'

    def __str__(self):
        return self.service_name

    @property
    def get_image(self):
        if self.image:
            if str(self.image).startswith('http://') or str(self.image).startswith('https://'):
                return self.image
            return self.image.url
        return 'https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=600&q=80'


class SalonStylist(models.Model):
    """
    Model for Salon Stylists stored in salon_stylists.
    """
    name = models.CharField(max_length=255)
    designation = models.CharField(max_length=100)
    experience = models.CharField(max_length=100, help_text="e.g. 5 Years")
    photo = models.ImageField(upload_to='salon/stylists/', null=True, blank=True)
    description = models.TextField()
    status = models.BooleanField(default=True)

    class Meta:
        db_table = 'salon_stylists'
        verbose_name = 'Salon Stylist'
        verbose_name_plural = 'Salon Stylists'

    def __str__(self):
        return self.name

    @property
    def get_photo(self):
        if self.photo:
            if str(self.photo).startswith('http://') or str(self.photo).startswith('https://'):
                return self.photo
            return self.photo.url
        return 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=600&q=80'


class SalonGallery(models.Model):
    """
    Model for Salon Gallery stored in salon_gallery.
    """
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100, help_text="e.g. Hair, Spa, Skin, Bridal, Before After")
    image = models.ImageField(upload_to='salon/gallery/', null=True, blank=True)
    status = models.BooleanField(default=True)

    class Meta:
        db_table = 'salon_gallery'
        verbose_name = 'Salon Gallery'
        verbose_name_plural = 'Salon Gallery Images'

    def __str__(self):
        return self.title

    @property
    def get_image(self):
        if self.image:
            if str(self.image).startswith('http://') or str(self.image).startswith('https://'):
                return self.image
            return self.image.url
        return 'https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=600&q=80'


class SalonTestimonial(models.Model):
    """
    Model for Salon Testimonials stored in salon_testimonials.
    """
    customer_name = models.CharField(max_length=255)
    rating = models.IntegerField(default=5)
    review = models.TextField()
    photo = models.ImageField(upload_to='salon/testimonials/', null=True, blank=True)
    status = models.BooleanField(default=True)

    class Meta:
        db_table = 'salon_testimonials'
        verbose_name = 'Salon Testimonial'
        verbose_name_plural = 'Salon Testimonials'

    def __str__(self):
        return f"{self.customer_name} ({self.rating} stars)"

    @property
    def get_photo(self):
        if self.photo:
            if str(self.photo).startswith('http://') or str(self.photo).startswith('https://'):
                return self.photo
            return self.photo.url
        return 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=150&q=80'


class SalonOffer(models.Model):
    """
    Model for Salon Offers stored in salon_offers.
    """
    title = models.CharField(max_length=255)
    description = models.TextField()
    discount = models.CharField(max_length=100)
    image = models.ImageField(upload_to='salon/offers/', null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.BooleanField(default=True)

    class Meta:
        db_table = 'salon_offers'
        verbose_name = 'Salon Offer'
        verbose_name_plural = 'Salon Offers'

    def __str__(self):
        return self.title

    @property
    def get_image(self):
        if self.image:
            if str(self.image).startswith('http://') or str(self.image).startswith('https://'):
                return self.image
            return self.image.url
        return 'https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=600&q=80'


class SalonBlog(models.Model):
    """
    Model for Salon Blogs stored in salon_blogs.
    """
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    image = models.ImageField(upload_to='salon/blogs/', null=True, blank=True)
    short_description = models.TextField()
    description = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    status = models.BooleanField(default=True)

    class Meta:
        db_table = 'salon_blogs'
        verbose_name = 'Salon Blog'
        verbose_name_plural = 'Salon Blogs'

    def __str__(self):
        return self.title

    @property
    def get_image(self):
        if self.image:
            if str(self.image).startswith('http://') or str(self.image).startswith('https://'):
                return self.image
            return self.image.url
        return 'https://images.unsplash.com/photo-1562322140-8baeececf3df?auto=format&fit=crop&w=600&q=80'


class SalonAppointment(models.Model):
    """
    Model for Salon Appointments stored in salon_appointments.
    """
    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Unisex/Other', 'Unisex/Other'),
    )
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )
    customer_name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=20)
    email = models.EmailField()
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    service = models.ForeignKey(SalonService, on_delete=models.CASCADE, db_column='service_id', related_name='appointments')
    stylist = models.ForeignKey(SalonStylist, on_delete=models.CASCADE, db_column='stylist_id', related_name='appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    message = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'salon_appointments'
        verbose_name = 'Salon Appointment'
        verbose_name_plural = 'Salon Appointments'

    def __str__(self):
        return f"Appt #{self.id} - {self.customer_name} ({self.appointment_date})"


class SalonSetting(models.Model):
    """
    Model for Salon Settings stored in salon_settings.
    """
    salon_name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='salon/uploads/', null=True, blank=True)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    whatsapp = models.CharField(max_length=20)
    facebook = models.CharField(max_length=255, blank=True, null=True)
    instagram = models.CharField(max_length=255, blank=True, null=True)
    youtube = models.CharField(max_length=255, blank=True, null=True)
    google_map = models.TextField(help_text="Iframe URL or embed code")
    opening_hours = models.TextField()

    class Meta:
        db_table = 'salon_settings'
        verbose_name = 'Salon Setting'
        verbose_name_plural = 'Salon Settings'

    def __str__(self):
        return self.salon_name

    @property
    def get_logo(self):
        if self.logo:
            if str(self.logo).startswith('http://') or str(self.logo).startswith('https://'):
                return self.logo
            return self.logo.url
        return ''
