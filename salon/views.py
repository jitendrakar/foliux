from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Count, Sum
from django.utils.text import slugify
from django.utils import timezone
from functools import wraps

from .models import (
    SalonUser, SalonCategory, SalonService, SalonStylist, 
    SalonGallery, SalonTestimonial, SalonOffer, SalonBlog, 
    SalonAppointment, SalonSetting
)
from .forms import SalonAppointmentForm, CustomerRegistrationForm, SalonLoginForm

# =====================================================================
# Auth Decorators
# =====================================================================
def salon_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'salon_user_id' not in request.session:
            messages.warning(request, "Please log in to access this page.")
            return redirect('salon:login')
        return view_func(request, *args, **kwargs)
    return wrapper

def salon_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'salon_user_id' not in request.session:
            messages.warning(request, "Please log in to access this page.")
            return redirect('salon:login')
        user_role = request.session.get('salon_user_role')
        if user_role != 'admin':
            messages.error(request, "You do not have authorization to view this page.")
            return redirect('salon:home')
        return view_func(request, *args, **kwargs)
    return wrapper

# Context Processor Helper
def get_salon_settings():
    setting = SalonSetting.objects.first()
    if not setting:
        # Default placeholder settings
        setting = SalonSetting(
            salon_name="SalonX Premium",
            address="12, Luxury Galleria, MG Road, Bangalore - 560001",
            phone="+91 98718 08718",
            email="salonx.foliux@gmail.com",
            whatsapp="+91 98718 08718",
            facebook="https://facebook.com",
            instagram="https://instagram.com",
            youtube="https://youtube.com",
            opening_hours="Mon - Sun: 9:00 AM - 9:00 PM",
            google_map='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3887.973418579979!2d77.6074127!3d12.9735496!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3bae167d30f4e1f7%3A0xf695df61cf1c1f54!2sMG%20Road%2C%20Bengaluru%2C%20Karnataka!5e0!3m2!1sen!2sin!4v1680000000000!5m2!1sen!2sin'
        )
    return setting

# =====================================================================
# Public Pages
# =====================================================================
def home(request):
    settings_obj = get_salon_settings()
    categories = SalonCategory.objects.filter(status=True)
    services = SalonService.objects.filter(status=True)[:8]
    stylists = SalonStylist.objects.filter(status=True)[:4]
    gallery = SalonGallery.objects.filter(status=True)[:6]
    testimonials = SalonTestimonial.objects.filter(status=True)[:6]
    offers = SalonOffer.objects.filter(status=True, end_date__gte=timezone.now().date())[:3]
    blogs = SalonBlog.objects.filter(status=True).order_by('-created_at')[:3]
    form = SalonAppointmentForm()
    
    # FAQs
    faqs = [
        {"question": "Do I need to book an appointment in advance?", "answer": "While we welcome walk-ins, we highly recommend booking in advance to ensure your preferred stylist and time slot are available."},
        {"question": "What safety measures do you follow?", "answer": "We maintain medical-grade sanitization. All tools are sterilized after every single use, and stylists wear fresh protective gear."},
        {"question": "Which hair care products do you use?", "answer": "We exclusively use premium international brands like L'Oreal Professionnel, Kérastase, and Olaplex for all hair services."},
        {"question": "Do you offer wedding and bridal packages?", "answer": "Yes, we offer specialized pre-bridal and bridal makeover packages customized to your skin and hair type. Contact us for details."},
        {"question": "Is parking available at the salon?", "answer": "Yes, we offer complimentary valet parking for all our premium salon clients."}
    ]

    context = {
        'settings': settings_obj,
        'categories': categories,
        'services': services,
        'stylists': stylists,
        'gallery': gallery,
        'testimonials': testimonials,
        'offers': offers,
        'blogs': blogs,
        'form': form,
        'faqs': faqs,
    }
    return render(request, 'salon/home.html', context)


def about(request):
    settings_obj = get_salon_settings()
    return render(request, 'salon/about.html', {'settings': settings_obj})


def services(request):
    settings_obj = get_salon_settings()
    categories = SalonCategory.objects.filter(status=True).prefetch_related('services')
    context = {
        'settings': settings_obj,
        'categories': categories,
    }
    return render(request, 'salon/services.html', context)


def pricing(request):
    settings_obj = get_salon_settings()
    categories = SalonCategory.objects.filter(status=True).prefetch_related('services')
    context = {
        'settings': settings_obj,
        'categories': categories,
    }
    return render(request, 'salon/pricing.html', context)


def gallery(request):
    settings_obj = get_salon_settings()
    gallery_images = SalonGallery.objects.filter(status=True)
    # Extract unique categories
    categories = list(set([item.category for item in gallery_images]))
    context = {
        'settings': settings_obj,
        'gallery': gallery_images,
        'categories': categories,
    }
    return render(request, 'salon/gallery.html', context)


def team(request):
    settings_obj = get_salon_settings()
    stylists = SalonStylist.objects.filter(status=True)
    context = {
        'settings': settings_obj,
        'stylists': stylists,
    }
    return render(request, 'salon/team.html', context)


def blog_list(request):
    settings_obj = get_salon_settings()
    blogs = SalonBlog.objects.filter(status=True).order_by('-created_at')
    context = {
        'settings': settings_obj,
        'blogs': blogs,
    }
    return render(request, 'salon/blog_list.html', context)


def blog_detail(request, slug):
    settings_obj = get_salon_settings()
    blog = get_object_or_404(SalonBlog, slug=slug, status=True)
    recent_blogs = SalonBlog.objects.filter(status=True).exclude(id=blog.id).order_by('-created_at')[:4]
    context = {
        'settings': settings_obj,
        'blog': blog,
        'recent_blogs': recent_blogs,
    }
    return render(request, 'salon/blog_detail.html', context)


def contact(request):
    settings_obj = get_salon_settings()
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # AJAX contact message mock
        name = request.POST.get('name')
        return JsonResponse({'status': 'success', 'message': f"Thank you {name}, we have received your message!"})
    return render(request, 'salon/contact.html', {'settings': settings_obj})


def offers(request):
    settings_obj = get_salon_settings()
    all_offers = SalonOffer.objects.filter(status=True)
    context = {
        'settings': settings_obj,
        'offers': all_offers,
    }
    return render(request, 'salon/offers.html', context)


def book_appointment(request):
    settings_obj = get_salon_settings()
    if request.method == 'POST':
        form = SalonAppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save()
            
            # If AJAX request
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success', 
                    'message': f"Appointment successfully requested for {appointment.appointment_date} at {appointment.appointment_time}!",
                    'booking_id': appointment.id
                })
            
            messages.success(request, f"Your appointment (ID: {appointment.id}) has been booked. We will contact you soon!")
            return redirect('salon:book_appointment')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'errors': form.errors})
    else:
        form = SalonAppointmentForm()
    
    return render(request, 'salon/book.html', {'settings': settings_obj, 'form': form})

# =====================================================================
# Customer Authentication & Profile
# =====================================================================
def salon_login(request):
    settings_obj = get_salon_settings()
    if request.method == 'POST':
        form = SalonLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                user = SalonUser.objects.get(email=email)
                if user.check_password(password):
                    request.session['salon_user_id'] = user.id
                    request.session['salon_user_role'] = user.role
                    request.session['salon_user_name'] = user.name
                    
                    messages.success(request, f"Welcome back, {user.name}!")
                    if user.role == 'admin':
                        return redirect('salon:dashboard_home')
                    else:
                        return redirect('salon:profile')
                else:
                    messages.error(request, "Invalid password.")
            except SalonUser.DoesNotExist:
                messages.error(request, "A user with this email does not exist.")
    else:
        form = SalonLoginForm()
    return render(request, 'salon/login.html', {'settings': settings_obj, 'form': form})


def salon_register(request):
    settings_obj = get_salon_settings()
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.role = 'customer'
            user.save()
            messages.success(request, "Registration successful! You can now log in.")
            return redirect('salon:login')
    else:
        form = CustomerRegistrationForm()
    return render(request, 'salon/register.html', {'settings': settings_obj, 'form': form})


def salon_logout(request):
    request.session.flush()
    messages.success(request, "Logged out successfully.")
    return redirect('salon:home')


@salon_login_required
def salon_profile(request):
    settings_obj = get_salon_settings()
    user_id = request.session.get('salon_user_id')
    user = get_object_or_404(SalonUser, id=user_id)
    
    # We query appointments matching customer's email or mobile
    appointments = SalonAppointment.objects.filter(
        email=user.email
    ).order_by('-appointment_date', '-appointment_time')

    context = {
        'settings': settings_obj,
        'user': user,
        'appointments': appointments,
    }
    return render(request, 'salon/profile.html', context)

# =====================================================================
# Admin Dashboard & Statistics
# =====================================================================
@salon_admin_required
def dashboard_home(request):
    settings_obj = get_salon_settings()
    
    # Statistics
    total_appointments = SalonAppointment.objects.count()
    pending_appointments = SalonAppointment.objects.filter(status='Pending').count()
    completed_appointments = SalonAppointment.objects.filter(status='Completed').count()
    
    # Revenue estimation based on services completed
    completed_appt_revenue = SalonAppointment.objects.filter(
        status='Completed'
    ).aggregate(total=Sum('service__price'))['total'] or 0.0
    
    total_services = SalonService.objects.count()
    total_stylists = SalonStylist.objects.count()
    total_customers = SalonUser.objects.filter(role='customer').count()
    
    # Recent appointments
    recent_appts = SalonAppointment.objects.select_related('service', 'stylist').order_by('-created_at')[:8]
    
    # Appointment charts prep
    status_chart_data = list(SalonAppointment.objects.values('status').annotate(count=Count('id')))
    category_chart_data = list(SalonAppointment.objects.values('service__category__category_name').annotate(count=Count('id')))

    context = {
        'settings': settings_obj,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'completed_appointments': completed_appointments,
        'revenue': completed_appt_revenue,
        'total_services': total_services,
        'total_stylists': total_stylists,
        'total_customers': total_customers,
        'recent_appointments': recent_appts,
        'status_chart_data': status_chart_data,
        'category_chart_data': category_chart_data,
        'active_tab': 'dashboard'
    }
    return render(request, 'salon/dashboard/home.html', context)

# =====================================================================
# Dashboard CRUD - Appointments
# =====================================================================
@salon_admin_required
def dashboard_appointments(request):
    settings_obj = get_salon_settings()
    status_filter = request.GET.get('status', '')
    
    appointments = SalonAppointment.objects.select_related('service', 'stylist').order_by('-appointment_date', '-appointment_time')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
        
    context = {
        'settings': settings_obj,
        'appointments': appointments,
        'status_filter': status_filter,
        'active_tab': 'appointments'
    }
    return render(request, 'salon/dashboard/appointments.html', context)


@salon_admin_required
def dashboard_appointment_update(request, pk):
    appointment = get_object_or_404(SalonAppointment, pk=pk)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['Pending', 'Confirmed', 'Completed', 'Cancelled']:
            appointment.status = status
            appointment.save()
            messages.success(request, f"Appointment status updated to {status}.")
        else:
            messages.error(request, "Invalid status choice.")
    return redirect('salon:dashboard_appointments')

# =====================================================================
# Dashboard CRUD - Services
# =====================================================================
@salon_admin_required
def dashboard_services(request):
    settings_obj = get_salon_settings()
    services_list = SalonService.objects.select_related('category').all()
    context = {
        'settings': settings_obj,
        'services': services_list,
        'active_tab': 'services'
    }
    return render(request, 'salon/dashboard/services.html', context)


@salon_admin_required
def dashboard_service_add(request):
    settings_obj = get_salon_settings()
    categories = SalonCategory.objects.all()
    if request.method == 'POST':
        category_id = request.POST.get('category')
        service_name = request.POST.get('service_name')
        price = request.POST.get('price')
        duration = request.POST.get('duration')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        status = request.POST.get('status') == 'on'
        
        category = get_object_or_404(SalonCategory, id=category_id)
        
        service = SalonService.objects.create(
            category=category,
            service_name=service_name,
            price=price,
            duration=duration,
            description=description,
            image=image,
            status=status
        )
        messages.success(request, f"Service '{service.service_name}' added successfully.")
        return redirect('salon:dashboard_services')
        
    return render(request, 'salon/dashboard/service_form.html', {'settings': settings_obj, 'categories': categories, 'action': 'Add'})


@salon_admin_required
def dashboard_service_edit(request, pk):
    settings_obj = get_salon_settings()
    service = get_object_or_404(SalonService, pk=pk)
    categories = SalonCategory.objects.all()
    if request.method == 'POST':
        category_id = request.POST.get('category')
        service.category = get_object_or_404(SalonCategory, id=category_id)
        service.service_name = request.POST.get('service_name')
        service.price = request.POST.get('price')
        service.duration = request.POST.get('duration')
        service.description = request.POST.get('description')
        if request.FILES.get('image'):
            service.image = request.FILES.get('image')
        service.status = request.POST.get('status') == 'on'
        service.save()
        messages.success(request, f"Service '{service.service_name}' updated successfully.")
        return redirect('salon:dashboard_services')
        
    context = {
        'settings': settings_obj,
        'service': service,
        'categories': categories,
        'action': 'Edit'
    }
    return render(request, 'salon/dashboard/service_form.html', context)


@salon_admin_required
def dashboard_service_delete(request, pk):
    service = get_object_or_404(SalonService, pk=pk)
    name = service.service_name
    service.delete()
    messages.success(request, f"Service '{name}' was deleted.")
    return redirect('salon:dashboard_services')

# =====================================================================
# Dashboard CRUD - Stylists
# =====================================================================
@salon_admin_required
def dashboard_stylists(request):
    settings_obj = get_salon_settings()
    stylists = SalonStylist.objects.all()
    context = {
        'settings': settings_obj,
        'stylists': stylists,
        'active_tab': 'stylists'
    }
    return render(request, 'salon/dashboard/stylists.html', context)


@salon_admin_required
def dashboard_stylist_add(request):
    settings_obj = get_salon_settings()
    if request.method == 'POST':
        name = request.POST.get('name')
        designation = request.POST.get('designation')
        experience = request.POST.get('experience')
        description = request.POST.get('description')
        photo = request.FILES.get('photo')
        status = request.POST.get('status') == 'on'
        
        SalonStylist.objects.create(
            name=name,
            designation=designation,
            experience=experience,
            description=description,
            photo=photo,
            status=status
        )
        messages.success(request, f"Stylist '{name}' added successfully.")
        return redirect('salon:dashboard_stylists')
        
    return render(request, 'salon/dashboard/stylist_form.html', {'settings': settings_obj, 'action': 'Add'})


@salon_admin_required
def dashboard_stylist_edit(request, pk):
    settings_obj = get_salon_settings()
    stylist = get_object_or_404(SalonStylist, pk=pk)
    if request.method == 'POST':
        stylist.name = request.POST.get('name')
        stylist.designation = request.POST.get('designation')
        stylist.experience = request.POST.get('experience')
        stylist.description = request.POST.get('description')
        if request.FILES.get('photo'):
            stylist.photo = request.FILES.get('photo')
        stylist.status = request.POST.get('status') == 'on'
        stylist.save()
        messages.success(request, f"Stylist '{stylist.name}' updated successfully.")
        return redirect('salon:dashboard_stylists')
        
    context = {
        'settings': settings_obj,
        'stylist': stylist,
        'action': 'Edit'
    }
    return render(request, 'salon/dashboard/stylist_form.html', context)


@salon_admin_required
def dashboard_stylist_delete(request, pk):
    stylist = get_object_or_404(SalonStylist, pk=pk)
    name = stylist.name
    stylist.delete()
    messages.success(request, f"Stylist '{name}' was deleted.")
    return redirect('salon:dashboard_stylists')

# =====================================================================
# Dashboard CRUD - Gallery
# =====================================================================
@salon_admin_required
def dashboard_gallery(request):
    settings_obj = get_salon_settings()
    gallery_list = SalonGallery.objects.all()
    context = {
        'settings': settings_obj,
        'gallery': gallery_list,
        'active_tab': 'gallery'
    }
    return render(request, 'salon/dashboard/gallery.html', context)


@salon_admin_required
def dashboard_gallery_add(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        category = request.POST.get('category')
        image = request.FILES.get('image')
        status = request.POST.get('status') == 'on'
        
        SalonGallery.objects.create(
            title=title,
            category=category,
            image=image,
            status=status
        )
        messages.success(request, f"Gallery item '{title}' added.")
    return redirect('salon:dashboard_gallery')


@salon_admin_required
def dashboard_gallery_delete(request, pk):
    item = get_object_or_404(SalonGallery, pk=pk)
    item.delete()
    messages.success(request, "Gallery item deleted.")
    return redirect('salon:dashboard_gallery')

# =====================================================================
# Dashboard CRUD - Testimonials
# =====================================================================
@salon_admin_required
def dashboard_testimonials(request):
    settings_obj = get_salon_settings()
    testimonials = SalonTestimonial.objects.all()
    context = {
        'settings': settings_obj,
        'testimonials': testimonials,
        'active_tab': 'testimonials'
    }
    return render(request, 'salon/dashboard/testimonials.html', context)


@salon_admin_required
def dashboard_testimonial_add(request):
    settings_obj = get_salon_settings()
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name')
        rating = request.POST.get('rating')
        review = request.POST.get('review')
        photo = request.FILES.get('photo')
        status = request.POST.get('status') == 'on'
        
        SalonTestimonial.objects.create(
            customer_name=customer_name,
            rating=rating,
            review=review,
            photo=photo,
            status=status
        )
        messages.success(request, "Testimonial added successfully.")
        return redirect('salon:dashboard_testimonials')
    return render(request, 'salon/dashboard/testimonial_form.html', {'settings': settings_obj, 'action': 'Add'})


@salon_admin_required
def dashboard_testimonial_edit(request, pk):
    settings_obj = get_salon_settings()
    testimonial = get_object_or_404(SalonTestimonial, pk=pk)
    if request.method == 'POST':
        testimonial.customer_name = request.POST.get('customer_name')
        testimonial.rating = request.POST.get('rating')
        testimonial.review = request.POST.get('review')
        if request.FILES.get('photo'):
            testimonial.photo = request.FILES.get('photo')
        testimonial.status = request.POST.get('status') == 'on'
        testimonial.save()
        messages.success(request, "Testimonial updated successfully.")
        return redirect('salon:dashboard_testimonials')
        
    context = {
        'settings': settings_obj,
        'testimonial': testimonial,
        'action': 'Edit'
    }
    return render(request, 'salon/dashboard/testimonial_form.html', context)


@salon_admin_required
def dashboard_testimonial_delete(request, pk):
    testimonial = get_object_or_404(SalonTestimonial, pk=pk)
    testimonial.delete()
    messages.success(request, "Testimonial deleted.")
    return redirect('salon:dashboard_testimonials')

# =====================================================================
# Dashboard CRUD - Offers
# =====================================================================
@salon_admin_required
def dashboard_offers(request):
    settings_obj = get_salon_settings()
    offers_list = SalonOffer.objects.all()
    context = {
        'settings': settings_obj,
        'offers': offers_list,
        'active_tab': 'offers'
    }
    return render(request, 'salon/dashboard/offers.html', context)


@salon_admin_required
def dashboard_offer_add(request):
    settings_obj = get_salon_settings()
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        discount = request.POST.get('discount')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        image = request.FILES.get('image')
        status = request.POST.get('status') == 'on'
        
        SalonOffer.objects.create(
            title=title,
            description=description,
            discount=discount,
            start_date=start_date,
            end_date=end_date,
            image=image,
            status=status
        )
        messages.success(request, "Offer created successfully.")
        return redirect('salon:dashboard_offers')
    return render(request, 'salon/dashboard/offer_form.html', {'settings': settings_obj, 'action': 'Add'})


@salon_admin_required
def dashboard_offer_edit(request, pk):
    settings_obj = get_salon_settings()
    offer = get_object_or_404(SalonOffer, pk=pk)
    if request.method == 'POST':
        offer.title = request.POST.get('title')
        offer.description = request.POST.get('description')
        offer.discount = request.POST.get('discount')
        offer.start_date = request.POST.get('start_date')
        offer.end_date = request.POST.get('end_date')
        if request.FILES.get('image'):
            offer.image = request.FILES.get('image')
        offer.status = request.POST.get('status') == 'on'
        offer.save()
        messages.success(request, "Offer updated successfully.")
        return redirect('salon:dashboard_offers')
        
    context = {
        'settings': settings_obj,
        'offer': offer,
        'action': 'Edit'
    }
    return render(request, 'salon/dashboard/offer_form.html', context)


@salon_admin_required
def dashboard_offer_delete(request, pk):
    offer = get_object_or_404(SalonOffer, pk=pk)
    offer.delete()
    messages.success(request, "Offer deleted.")
    return redirect('salon:dashboard_offers')

# =====================================================================
# Dashboard CRUD - Blogs
# =====================================================================
@salon_admin_required
def dashboard_blogs(request):
    settings_obj = get_salon_settings()
    blogs_list = SalonBlog.objects.all().order_by('-created_at')
    context = {
        'settings': settings_obj,
        'blogs': blogs_list,
        'active_tab': 'blogs'
    }
    return render(request, 'salon/dashboard/blogs.html', context)


@salon_admin_required
def dashboard_blog_add(request):
    settings_obj = get_salon_settings()
    if request.method == 'POST':
        title = request.POST.get('title')
        short_description = request.POST.get('short_description')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        status = request.POST.get('status') == 'on'
        
        slug = slugify(title)
        # Handle duplicate slugs
        original_slug = slug
        count = 1
        while SalonBlog.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{count}"
            count += 1
            
        SalonBlog.objects.create(
            title=title,
            slug=slug,
            short_description=short_description,
            description=description,
            image=image,
            status=status
        )
        messages.success(request, "Blog post created successfully.")
        return redirect('salon:dashboard_blogs')
    return render(request, 'salon/dashboard/blog_form.html', {'settings': settings_obj, 'action': 'Add'})


@salon_admin_required
def dashboard_blog_edit(request, pk):
    settings_obj = get_salon_settings()
    blog = get_object_or_404(SalonBlog, pk=pk)
    if request.method == 'POST':
        blog.title = request.POST.get('title')
        blog.short_description = request.POST.get('short_description')
        blog.description = request.POST.get('description')
        if request.FILES.get('image'):
            blog.image = request.FILES.get('image')
        blog.status = request.POST.get('status') == 'on'
        blog.save()
        messages.success(request, "Blog post updated successfully.")
        return redirect('salon:dashboard_blogs')
        
    context = {
        'settings': settings_obj,
        'blog': blog,
        'action': 'Edit'
    }
    return render(request, 'salon/dashboard/blog_form.html', context)


@salon_admin_required
def dashboard_blog_delete(request, pk):
    blog = get_object_or_404(SalonBlog, pk=pk)
    blog.delete()
    messages.success(request, "Blog post deleted.")
    return redirect('salon:dashboard_blogs')

# =====================================================================
# Dashboard - Customers
# =====================================================================
@salon_admin_required
def dashboard_customers(request):
    settings_obj = get_salon_settings()
    customers = SalonUser.objects.filter(role='customer').order_by('-created_at')
    
    # Enhance customers with appointment counts
    enhanced_customers = []
    for customer in customers:
        appts = SalonAppointment.objects.filter(email=customer.email)
        enhanced_customers.append({
            'id': customer.id,
            'name': customer.name,
            'mobile': customer.mobile,
            'email': customer.email,
            'created_at': customer.created_at,
            'appointment_count': appts.count(),
            'completed_count': appts.filter(status='Completed').count()
        })
        
    context = {
        'settings': settings_obj,
        'customers': enhanced_customers,
        'active_tab': 'customers'
    }
    return render(request, 'salon/dashboard/customers.html', context)

# =====================================================================
# Dashboard - Settings
# =====================================================================
@salon_admin_required
def dashboard_settings(request):
    settings_obj = get_salon_settings()
    
    # If the setting record is a mock/new one, let's persist it first
    if not settings_obj.pk:
        settings_obj.save()
        
    if request.method == 'POST':
        settings_obj.salon_name = request.POST.get('salon_name')
        settings_obj.phone = request.POST.get('phone')
        settings_obj.email = request.POST.get('email')
        settings_obj.whatsapp = request.POST.get('whatsapp')
        settings_obj.facebook = request.POST.get('facebook')
        settings_obj.instagram = request.POST.get('instagram')
        settings_obj.youtube = request.POST.get('youtube')
        settings_obj.address = request.POST.get('address')
        settings_obj.opening_hours = request.POST.get('opening_hours')
        settings_obj.google_map = request.POST.get('google_map')
        
        if request.FILES.get('logo'):
            settings_obj.logo = request.FILES.get('logo')
            
        settings_obj.save()
        messages.success(request, "Salon settings updated successfully.")
        return redirect('salon:dashboard_settings')
        
    context = {
        'settings': settings_obj,
        'active_tab': 'settings'
    }
    return render(request, 'salon/dashboard/settings.html', context)
