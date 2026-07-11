from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

class TailorUser(models.Model):
    """
    Model for Tailor Users (Admins and Customers) stored in tailor_users.
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
    address = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tailor_users'
        verbose_name = 'Tailor User'
        verbose_name_plural = 'Tailor Users'

    def __str__(self):
        return f"{self.name} ({self.role})"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


class TailorService(models.Model):
    """
    Model for Tailoring Services stored in tailor_services.
    """
    CATEGORY_CHOICES = (
        ("Men's Tailoring", "Men's Tailoring"),
        ("Women's Tailoring", "Women's Tailoring"),
        ("Other Services", "Other Services"),
    )
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    service_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    icon = models.CharField(max_length=100, default="fa-scissors", help_text="FontAwesome icon class name")
    description = models.TextField()
    status = models.BooleanField(default=True)

    class Meta:
        db_table = 'tailor_services'
        verbose_name = 'Tailoring Service'
        verbose_name_plural = 'Tailoring Services'

    def __str__(self):
        return self.service_name


class TailorMeasurement(models.Model):
    """
    Model for Sizing Measurements stored in tailor_measurements.
    """
    customer = models.ForeignKey(TailorUser, on_delete=models.CASCADE, db_column='customer_id', related_name='measurements')
    height = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. 175 cm")
    chest = models.CharField(max_length=50, blank=True, null=True)
    waist = models.CharField(max_length=50, blank=True, null=True)
    hip = models.CharField(max_length=50, blank=True, null=True)
    shoulder = models.CharField(max_length=50, blank=True, null=True)
    sleeve = models.CharField(max_length=50, blank=True, null=True)
    neck = models.CharField(max_length=50, blank=True, null=True)
    inseam = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tailor_measurements'
        verbose_name = 'Measurement'
        verbose_name_plural = 'Measurements'

    def __str__(self):
        return f"Sizing for {self.customer.name} (Updated {self.updated_at.date()})"


class TailorOrder(models.Model):
    """
    Model for Tailoring Orders stored in tailor_orders.
    """
    STATUS_CHOICES = (
        ('New', 'New'),
        ('Cutting', 'Cutting'),
        ('Stitching', 'Stitching'),
        ('Trial', 'Trial'),
        ('Ready', 'Ready'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    )
    order_number = models.CharField(max_length=100, unique=True)
    customer = models.ForeignKey(TailorUser, on_delete=models.CASCADE, db_column='customer_id', related_name='orders')
    category = models.CharField(max_length=100)
    service = models.ForeignKey(TailorService, on_delete=models.CASCADE, db_column='service_id')
    fabric = models.CharField(max_length=255, blank=True, null=True)
    measurement = models.ForeignKey(TailorMeasurement, on_delete=models.SET_NULL, db_column='measurement_id', blank=True, null=True)
    trial_date = models.DateField(blank=True, null=True)
    delivery_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    advance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tailor_orders'
        verbose_name = 'Tailor Order'
        verbose_name_plural = 'Tailor Orders'

    def __str__(self):
        return f"Order {self.order_number} ({self.customer.name})"


class TailorAppointment(models.Model):
    """
    Model for Tailoring Appointments stored in tailor_appointments.
    """
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )
    customer_name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=20)
    email = models.EmailField()
    gender = models.CharField(max_length=20)
    service = models.ForeignKey(TailorService, on_delete=models.CASCADE, db_column='service_id')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    home_visit = models.BooleanField(default=False)
    message = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tailor_appointments'
        verbose_name = 'Tailor Appointment'
        verbose_name_plural = 'Tailor Appointments'

    def __str__(self):
        return f"Appt #{self.id} - {self.customer_name} ({self.appointment_date})"


class TailorGallery(models.Model):
    """
    Model for Boutique Designs Gallery stored in tailor_gallery.
    """
    CATEGORY_CHOICES = (
        ('Men', 'Men'),
        ('Women', 'Women'),
        ('Bridal', 'Bridal'),
        ('Boutique', 'Boutique'),
        ('Uniform', 'Uniform'),
        ('Latest Designs', 'Latest Designs'),
    )
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    image = models.ImageField(upload_to='tailor/gallery/', null=True, blank=True)
    status = models.BooleanField(default=True)

    class Meta:
        db_table = 'tailor_gallery'
        verbose_name = 'Gallery Design'
        verbose_name_plural = 'Gallery Designs'

    def __str__(self):
        return self.title

    @property
    def get_image(self):
        if self.image:
            if str(self.image).startswith('http://') or str(self.image).startswith('https://'):
                return self.image
            return self.image.url
        return 'https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?auto=format&fit=crop&w=500&q=80'


class TailorReview(models.Model):
    """
    Model for Testimonials/Reviews stored in tailor_reviews.
    """
    customer_name = models.CharField(max_length=255)
    rating = models.IntegerField(default=5)
    review = models.TextField()
    status = models.BooleanField(default=False)  # Requires admin approval by default

    class Meta:
        db_table = 'tailor_reviews'
        verbose_name = 'Customer Review'
        verbose_name_plural = 'Customer Reviews'

    def __str__(self):
        return f"{self.customer_name} - {self.rating} Stars"


class TailorOffer(models.Model):
    """
    Model for coupons/discounts/festival offers stored in tailor_offers.
    """
    title = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    discount = models.CharField(max_length=100, help_text="e.g. 20% OFF or Flat ₹500 Off")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.BooleanField(default=True)

    class Meta:
        db_table = 'tailor_offers'
        verbose_name = 'Offer Coupon'
        verbose_name_plural = 'Offer Coupons'

    def __str__(self):
        return f"{self.title} ({self.code})"


class TailorPayment(models.Model):
    """
    Model for payments (advance, balance) stored in tailor_payments.
    """
    TYPE_CHOICES = (
        ('Advance', 'Advance'),
        ('Balance', 'Balance'),
        ('Full', 'Full'),
    )
    order = models.ForeignKey(TailorOrder, on_delete=models.CASCADE, db_column='order_id', related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(max_length=50, default='Cash')
    payment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    class Meta:
        db_table = 'tailor_payments'
        verbose_name = 'Payment Record'
        verbose_name_plural = 'Payment Records'

    def __str__(self):
        return f"Payment ₹{self.amount_paid} for Order {self.order.order_number}"


class TailorSetting(models.Model):
    """
    Model for Tailor boutique settings stored in tailor_settings.
    """
    brand_name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='tailor/uploads/', null=True, blank=True)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    whatsapp = models.CharField(max_length=20)
    google_map = models.TextField()

    class Meta:
        db_table = 'tailor_settings'
        verbose_name = 'Boutique Setting'
        verbose_name_plural = 'Boutique Settings'

    def __str__(self):
        return self.brand_name
