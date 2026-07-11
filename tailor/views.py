from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.utils.text import slugify
from functools import wraps
from datetime import date, time, datetime, timedelta

from .models import (
    TailorUser, TailorService, TailorMeasurement, TailorOrder, 
    TailorAppointment, TailorGallery, TailorReview, TailorOffer, 
    TailorPayment, TailorSetting
)
from .forms import (
    TailorAppointmentForm, TailorMeasurementForm, 
    CustomerRegistrationForm, TailorLoginForm
)

# =====================================================================
# Auth Decorators
# =====================================================================
def tailor_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'tailor_user_id' not in request.session:
            messages.warning(request, "Please log in to access this page.")
            return redirect('tailor:login')
        return view_func(request, *args, **kwargs)
    return wrapper

def tailor_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'tailor_user_id' not in request.session:
            messages.warning(request, "Please log in to access this page.")
            return redirect('tailor:login')
        user_role = request.session.get('tailor_user_role')
        if user_role != 'admin':
            messages.error(request, "You do not have authorization to view this page.")
            return redirect('tailor:home')
        return view_func(request, *args, **kwargs)
    return wrapper

# Context Processor Helper
def get_tailor_settings():
    setting = TailorSetting.objects.first()
    if not setting:
        # Default placeholder settings
        setting = TailorSetting(
            brand_name="TailorX Premium Boutique",
            address="N-15, Private Colony, Sriniwaspuri, New Delhi, Delhi 110065",
            phone="+91 98718 08718",
            email="jitendra.kar@gmail.com",
            whatsapp="+91 98718 08718",
            google_map='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3504.2690906263595!2d77.2559599!3d28.5616802!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x390d1da0e6db69b3%3A0xe5426177b949989f!2sSriniwaspuri%2C%20New%20Delhi%2C%20Delhi!5e0!3m2!1sen!2sin!4v1680000000000!5m2!1sen!2sin'
        )
    return setting

# =====================================================================
# Public Pages
# =====================================================================
def home(request):
    settings_obj = get_tailor_settings()
    services_men = TailorService.objects.filter(category="Men's Tailoring", status=True)
    services_women = TailorService.objects.filter(category="Women's Tailoring", status=True)
    services_other = TailorService.objects.filter(category="Other Services", status=True)
    
    gallery_items = TailorGallery.objects.filter(status=True)[:6]
    reviews = TailorReview.objects.filter(status=True)[:6]
    offers = TailorOffer.objects.filter(status=True, end_date__gte=timezone.now().date())[:3]
    form = TailorAppointmentForm()
    
    context = {
        'settings': settings_obj,
        'services_men': services_men,
        'services_women': services_women,
        'services_other': services_other,
        'gallery': gallery_items,
        'reviews': reviews,
        'offers': offers,
        'form': form,
    }
    return render(request, 'tailor/home.html', context)


def about(request):
    settings_obj = get_tailor_settings()
    return render(request, 'tailor/about.html', {'settings': settings_obj})


def services(request):
    settings_obj = get_tailor_settings()
    services_men = TailorService.objects.filter(category="Men's Tailoring", status=True)
    services_women = TailorService.objects.filter(category="Women's Tailoring", status=True)
    services_other = TailorService.objects.filter(category="Other Services", status=True)
    context = {
        'settings': settings_obj,
        'services_men': services_men,
        'services_women': services_women,
        'services_other': services_other,
    }
    return render(request, 'tailor/services.html', context)


def gallery(request):
    settings_obj = get_tailor_settings()
    gallery_list = TailorGallery.objects.filter(status=True)
    categories = list(set([item.category for item in gallery_list]))
    context = {
        'settings': settings_obj,
        'gallery': gallery_list,
        'categories': categories,
    }
    return render(request, 'tailor/gallery.html', context)


def pricing(request):
    settings_obj = get_tailor_settings()
    services_list = TailorService.objects.filter(status=True)
    context = {
        'settings': settings_obj,
        'services': services_list,
    }
    return render(request, 'tailor/pricing.html', context)


def contact(request):
    settings_obj = get_tailor_settings()
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        name = request.POST.get('name')
        return JsonResponse({'status': 'success', 'message': f"Thank you {name}, we have received your query!"})
    return render(request, 'tailor/contact.html', {'settings': settings_obj})


def book_appointment(request):
    settings_obj = get_tailor_settings()
    if request.method == 'POST':
        form = TailorAppointmentForm(request.POST)
        if form.is_valid():
            appt = form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': f"Appointment successfully booked for {appt.appointment_date} at {appt.appointment_time}!",
                    'booking_id': appt.id
                })
            messages.success(request, f"Appointment requested (ID: {appt.id}). We will call you soon!")
            return redirect('tailor:book_appointment')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'errors': form.errors})
    else:
        form = TailorAppointmentForm()
    return render(request, 'tailor/book.html', {'settings': settings_obj, 'form': form})


def measurement_request(request):
    settings_obj = get_tailor_settings()
    # Check if customer is logged in to prepopulate name/mobile
    customer = None
    if 'tailor_user_id' in request.session:
        customer = TailorUser.objects.filter(id=request.session['tailor_user_id']).first()
        
    if request.method == 'POST':
        form = TailorMeasurementForm(request.POST)
        if form.is_valid():
            # If user is logged in, save size to their account
            if customer:
                measurement = form.save(commit=False)
                measurement.customer = customer
                measurement.save()
                messages.success(request, "Your size measurements have been updated successfully!")
                return redirect('tailor:profile')
            else:
                # If guest, require booking details or simulate submission
                name = request.POST.get('guest_name')
                mobile = request.POST.get('guest_mobile')
                email = request.POST.get('guest_email')
                
                # Create a guest user first
                guest_user, created = TailorUser.objects.get_or_create(
                    mobile=mobile,
                    defaults={'name': name, 'email': email, 'role': 'customer'}
                )
                
                measurement = form.save(commit=False)
                measurement.customer = guest_user
                measurement.save()
                
                messages.success(request, f"Measurements submitted successfully for {name}! We will verify them shortly.")
                return redirect('tailor:home')
        else:
            messages.error(request, "Failed to submit measurements. Please check the sizing fields.")
    else:
        form = TailorMeasurementForm()
    
    return render(request, 'tailor/measurement_request.html', {
        'settings': settings_obj,
        'form': form,
        'customer': customer
    })


def track_order(request):
    settings_obj = get_tailor_settings()
    order = None
    searched = False
    
    if request.method == 'POST' or ('order_number' in request.GET and 'mobile' in request.GET):
        order_number = request.POST.get('order_number') or request.GET.get('order_number')
        mobile = request.POST.get('mobile') or request.GET.get('mobile')
        searched = True
        
        order = TailorOrder.objects.filter(
            order_number=order_number, 
            customer__mobile=mobile
        ).select_related('service', 'customer').first()
        
        if not order:
            messages.error(request, "No order found matching these details. Please check the order and mobile numbers.")
            
    return render(request, 'tailor/track.html', {
        'settings': settings_obj,
        'order': order,
        'searched': searched
    })

# =====================================================================
# Customer Authentication & Profile
# =====================================================================
def tailor_login(request):
    settings_obj = get_tailor_settings()
    if request.method == 'POST':
        form = TailorLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                user = TailorUser.objects.get(email=email)
                if user.check_password(password):
                    request.session['tailor_user_id'] = user.id
                    request.session['tailor_user_role'] = user.role
                    request.session['tailor_user_name'] = user.name
                    
                    messages.success(request, f"Welcome back, {user.name}!")
                    if user.role == 'admin':
                        return redirect('tailor:dashboard_home')
                    else:
                        return redirect('tailor:profile')
                else:
                    messages.error(request, "Invalid password.")
            except TailorUser.DoesNotExist:
                messages.error(request, "A user with this email does not exist.")
    else:
        form = TailorLoginForm()
    return render(request, 'tailor/login.html', {'settings': settings_obj, 'form': form})


def tailor_register(request):
    settings_obj = get_tailor_settings()
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.role = 'customer'
            user.save()
            messages.success(request, "Registration successful! You can now log in.")
            return redirect('tailor:login')
    else:
        form = CustomerRegistrationForm()
    return render(request, 'tailor/register.html', {'settings': settings_obj, 'form': form})


def tailor_logout(request):
    request.session.flush()
    messages.success(request, "Logged out successfully.")
    return redirect('tailor:home')


@tailor_login_required
def tailor_profile(request):
    settings_obj = get_tailor_settings()
    user_id = request.session.get('tailor_user_id')
    user = get_object_or_404(TailorUser, id=user_id)
    
    # Get user orders
    orders = TailorOrder.objects.filter(customer=user).select_related('service').order_by('-created_at')
    
    # Get user measurements
    measurements = TailorMeasurement.objects.filter(customer=user).order_by('-updated_at')
    
    context = {
        'settings': settings_obj,
        'user': user,
        'orders': orders,
        'measurements': measurements,
    }
    return render(request, 'tailor/profile.html', context)

# =====================================================================
# Admin Dashboard
# =====================================================================
@tailor_admin_required
def dashboard_home(request):
    settings_obj = get_tailor_settings()
    
    # Metrics
    total_customers = TailorUser.objects.filter(role='customer').count()
    total_orders = TailorOrder.objects.count()
    pending_orders = TailorOrder.objects.exclude(status__in=['Delivered', 'Cancelled']).count()
    completed_orders = TailorOrder.objects.filter(status='Delivered').count()
    
    # Revenue (total amount collected as advance or balance)
    revenue = TailorPayment.objects.aggregate(total=Sum('amount_paid'))['total'] or 0.00
    
    # Today's appointments
    today = date.today()
    today_appts = TailorAppointment.objects.filter(appointment_date=today).select_related('service')
    
    # Recent orders
    recent_orders = TailorOrder.objects.select_related('customer', 'service').order_by('-created_at')[:8]
    
    # Charts preparations
    orders_by_status = list(TailorOrder.objects.values('status').annotate(count=Count('id')))
    orders_by_category = list(TailorOrder.objects.values('category').annotate(count=Count('id')))
    
    # Monthly orders (simulated via last 6 months list)
    monthly_data = []
    for i in range(5, -1, -1):
        target_month = (datetime.now() - timedelta(days=i*30)).date()
        month_start = target_month.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        count = TailorOrder.objects.filter(created_at__date__range=[month_start, month_end]).count()
        rev = TailorPayment.objects.filter(payment_date__date__range=[month_start, month_end]).aggregate(total=Sum('amount_paid'))['total'] or 0.00
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'orders': count,
            'revenue': float(rev)
        })

    context = {
        'settings': settings_obj,
        'total_customers': total_customers,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'revenue': revenue,
        'today_appointments': today_appts,
        'recent_orders': recent_orders,
        'orders_by_status': orders_by_status,
        'orders_by_category': orders_by_category,
        'monthly_data': monthly_data,
        'active_tab': 'dashboard'
    }
    return render(request, 'tailor/dashboard/home.html', context)

# =====================================================================
# Dashboard CRUD - Customers
# =====================================================================
@tailor_admin_required
def dashboard_customers(request):
    settings_obj = get_tailor_settings()
    query = request.GET.get('q', '')
    
    customers_list = TailorUser.objects.filter(role='customer').order_by('-created_at')
    if query:
        customers_list = customers_list.filter(
            Q(name__icontains=query) | 
            Q(mobile__icontains=query) | 
            Q(email__icontains=query)
        )
        
    enhanced_customers = []
    for cust in customers_list:
        order_count = TailorOrder.objects.filter(customer=cust).count()
        measure_count = TailorMeasurement.objects.filter(customer=cust).count()
        enhanced_customers.append({
            'id': cust.id,
            'name': cust.name,
            'mobile': cust.mobile,
            'email': cust.email,
            'address': cust.address,
            'gender': cust.gender,
            'order_count': order_count,
            'measure_count': measure_count
        })
        
    context = {
        'settings': settings_obj,
        'customers': enhanced_customers,
        'query': query,
        'active_tab': 'customers'
    }
    return render(request, 'tailor/dashboard/customers.html', context)


@tailor_admin_required
def dashboard_customer_edit(request, pk):
    settings_obj = get_tailor_settings()
    customer = get_object_or_404(TailorUser, pk=pk, role='customer')
    if request.method == 'POST':
        customer.name = request.POST.get('name')
        customer.mobile = request.POST.get('mobile')
        customer.email = request.POST.get('email')
        customer.address = request.POST.get('address')
        customer.gender = request.POST.get('gender')
        customer.save()
        messages.success(request, f"Customer '{customer.name}' updated successfully.")
        return redirect('tailor:dashboard_customers')
    return render(request, 'tailor/dashboard/customer_form.html', {'settings': settings_obj, 'customer': customer})


@tailor_admin_required
def dashboard_customer_delete(request, pk):
    customer = get_object_or_404(TailorUser, pk=pk, role='customer')
    name = customer.name
    customer.delete()
    messages.success(request, f"Customer '{name}' deleted.")
    return redirect('tailor:dashboard_customers')

# =====================================================================
# Dashboard CRUD - Measurements
# =====================================================================
@tailor_admin_required
def dashboard_measurements(request):
    settings_obj = get_tailor_settings()
    measurements = TailorMeasurement.objects.select_related('customer').order_by('-updated_at')
    context = {
        'settings': settings_obj,
        'measurements': measurements,
        'active_tab': 'measurements'
    }
    return render(request, 'tailor/dashboard/measurements.html', context)


@tailor_admin_required
def dashboard_measurement_add(request):
    settings_obj = get_tailor_settings()
    customers = TailorUser.objects.filter(role='customer')
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        customer = get_object_or_404(TailorUser, id=customer_id)
        
        form = TailorMeasurementForm(request.POST)
        if form.is_valid():
            measurement = form.save(commit=False)
            measurement.customer = customer
            measurement.save()
            messages.success(request, f"Measurements recorded for {customer.name}.")
            return redirect('tailor:dashboard_measurements')
    else:
        form = TailorMeasurementForm()
    return render(request, 'tailor/dashboard/measurement_form.html', {'settings': settings_obj, 'form': form, 'customers': customers, 'action': 'Add'})


@tailor_admin_required
def dashboard_measurement_edit(request, pk):
    settings_obj = get_tailor_settings()
    measurement = get_object_or_404(TailorMeasurement, pk=pk)
    if request.method == 'POST':
        form = TailorMeasurementForm(request.POST, instance=measurement)
        if form.is_valid():
            form.save()
            messages.success(request, f"Measurements updated for {measurement.customer.name}.")
            return redirect('tailor:dashboard_measurements')
    else:
        form = TailorMeasurementForm(instance=measurement)
    return render(request, 'tailor/dashboard/measurement_form.html', {'settings': settings_obj, 'form': form, 'action': 'Edit', 'measurement': measurement})

# =====================================================================
# Dashboard CRUD - Orders & Billing
# =====================================================================
@tailor_admin_required
def dashboard_orders(request):
    settings_obj = get_tailor_settings()
    status_filter = request.GET.get('status', '')
    
    orders = TailorOrder.objects.select_related('customer', 'service').order_by('-created_at')
    if status_filter:
        orders = orders.filter(status=status_filter)
        
    context = {
        'settings': settings_obj,
        'orders': orders,
        'status_filter': status_filter,
        'active_tab': 'orders'
    }
    return render(request, 'tailor/dashboard/orders.html', context)


@tailor_admin_required
def dashboard_order_add(request):
    settings_obj = get_tailor_settings()
    customers = TailorUser.objects.filter(role='customer')
    services_list = TailorService.objects.filter(status=True)
    
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        service_id = request.POST.get('service')
        fabric = request.POST.get('fabric')
        trial_date = request.POST.get('trial_date') or None
        delivery_date = request.POST.get('delivery_date')
        status = request.POST.get('status', 'New')
        amount = float(request.POST.get('amount'))
        advance = float(request.POST.get('advance', 0.00))
        balance = amount - advance
        
        customer = get_object_or_404(TailorUser, id=customer_id)
        service = get_object_or_404(TailorService, id=service_id)
        
        # Get customer's latest measurement record
        measurement = TailorMeasurement.objects.filter(customer=customer).order_by('-updated_at').first()
        
        # Generate unique order number (TLR + timestamp)
        order_number = f"TLR-{timezone.now().strftime('%y%m%d')}{random_digits(4)}"
        while TailorOrder.objects.filter(order_number=order_number).exists():
            order_number = f"TLR-{timezone.now().strftime('%y%m%d')}{random_digits(4)}"
            
        order = TailorOrder.objects.create(
            order_number=order_number,
            customer=customer,
            category=service.category,
            service=service,
            fabric=fabric,
            measurement=measurement,
            trial_date=trial_date,
            delivery_date=delivery_date,
            status=status,
            amount=amount,
            advance=advance,
            balance=balance
        )
        
        # Log payment if advance was paid
        if advance > 0:
            TailorPayment.objects.create(
                order=order,
                amount_paid=advance,
                payment_type='Advance',
                payment_method='Cash'
            )
            
        messages.success(request, f"Order '{order.order_number}' placed successfully.")
        return redirect('tailor:dashboard_orders')
        
    return render(request, 'tailor/dashboard/order_form.html', {
        'settings': settings_obj,
        'customers': customers,
        'services': services_list,
        'action': 'Add'
    })


@tailor_admin_required
def dashboard_order_edit(request, pk):
    settings_obj = get_tailor_settings()
    order = get_object_or_404(TailorOrder, pk=pk)
    customers = TailorUser.objects.filter(role='customer')
    services_list = TailorService.objects.filter(status=True)
    
    if request.method == 'POST':
        order.customer = get_object_or_404(TailorUser, id=request.POST.get('customer'))
        order.service = get_object_or_404(TailorService, id=request.POST.get('service'))
        order.category = order.service.category
        order.fabric = request.POST.get('fabric')
        order.trial_date = request.POST.get('trial_date') or None
        order.delivery_date = request.POST.get('delivery_date')
        order.status = request.POST.get('status')
        order.amount = float(request.POST.get('amount'))
        order.advance = float(request.POST.get('advance', 0.00))
        order.balance = order.amount - order.advance
        order.save()
        
        messages.success(request, f"Order '{order.order_number}' updated successfully.")
        return redirect('tailor:dashboard_orders')
        
    return render(request, 'tailor/dashboard/order_form.html', {
        'settings': settings_obj,
        'order': order,
        'customers': customers,
        'services': services_list,
        'action': 'Edit'
    })


@tailor_admin_required
def dashboard_order_delete(request, pk):
    order = get_object_or_404(TailorOrder, pk=pk)
    num = order.order_number
    order.delete()
    messages.success(request, f"Order '{num}' was deleted.")
    return redirect('tailor:dashboard_orders')


@tailor_admin_required
def dashboard_order_invoice(request, pk):
    settings_obj = get_tailor_settings()
    order = get_object_or_404(TailorOrder, pk=pk)
    payments = order.payments.all()
    context = {
        'settings': settings_obj,
        'order': order,
        'payments': payments
    }
    return render(request, 'tailor/dashboard/invoice.html', context)


def random_digits(n):
    import random
    return "".join([str(random.randint(0, 9)) for _ in range(n)])

# =====================================================================
# Dashboard CRUD - Appointments
# =====================================================================
@tailor_admin_required
def dashboard_appointments(request):
    settings_obj = get_tailor_settings()
    appointments = TailorAppointment.objects.select_related('service').order_by('-appointment_date', '-appointment_time')
    context = {
        'settings': settings_obj,
        'appointments': appointments,
        'active_tab': 'appointments'
    }
    return render(request, 'tailor/dashboard/appointments.html', context)


@tailor_admin_required
def dashboard_appointment_update(request, pk):
    appt = get_object_or_404(TailorAppointment, pk=pk)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['Pending', 'Confirmed', 'Completed', 'Cancelled']:
            appt.status = status
            appt.save()
            messages.success(request, f"Appointment status updated to {status}.")
        else:
            messages.error(request, "Invalid status choice.")
    return redirect('tailor:dashboard_appointments')

# =====================================================================
# Dashboard CRUD - Payments
# =====================================================================
@tailor_admin_required
def dashboard_payments(request):
    settings_obj = get_tailor_settings()
    payments = TailorPayment.objects.select_related('order__customer').order_by('-payment_date')
    orders = TailorOrder.objects.filter(balance__gt=0).select_related('customer')
    context = {
        'settings': settings_obj,
        'payments': payments,
        'orders': orders,
        'active_tab': 'payments'
    }
    return render(request, 'tailor/dashboard/payments.html', context)


@tailor_admin_required
def dashboard_payment_add(request):
    if request.method == 'POST':
        order_id = request.POST.get('order')
        amount = float(request.POST.get('amount_paid'))
        method = request.POST.get('payment_method')
        ptype = request.POST.get('payment_type')
        
        order = get_object_or_404(TailorOrder, id=order_id)
        
        # Create payment record
        TailorPayment.objects.create(
            order=order,
            amount_paid=amount,
            payment_method=method,
            payment_type=ptype
        )
        
        # Recalculate order payment totals
        total_paid = order.payments.aggregate(total=Sum('amount_paid'))['total'] or 0.00
        order.advance = total_paid
        order.balance = order.amount - total_paid
        order.save()
        
        messages.success(request, f"Payment of ₹{amount} recorded for Order {order.order_number}.")
    return redirect('tailor:dashboard_payments')

# =====================================================================
# Dashboard CRUD - Gallery
# =====================================================================
@tailor_admin_required
def dashboard_gallery(request):
    settings_obj = get_tailor_settings()
    gallery_list = TailorGallery.objects.all()
    context = {
        'settings': settings_obj,
        'gallery': gallery_list,
        'active_tab': 'gallery'
    }
    return render(request, 'tailor/dashboard/gallery.html', context)


@tailor_admin_required
def dashboard_gallery_add(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        category = request.POST.get('category')
        image = request.FILES.get('image') or request.POST.get('image_url')
        status = request.POST.get('status') == 'on'
        
        TailorGallery.objects.create(
            title=title,
            category=category,
            image=image,
            status=status
        )
        messages.success(request, "Gallery item added successfully.")
    return redirect('tailor:dashboard_gallery')


@tailor_admin_required
def dashboard_gallery_delete(request, pk):
    item = get_object_or_404(TailorGallery, pk=pk)
    item.delete()
    messages.success(request, "Gallery item deleted.")
    return redirect('tailor:dashboard_gallery')

# =====================================================================
# Dashboard CRUD - Services/Pricing
# =====================================================================
@tailor_admin_required
def dashboard_pricing(request):
    settings_obj = get_tailor_settings()
    services_list = TailorService.objects.all()
    context = {
        'settings': settings_obj,
        'services': services_list,
        'active_tab': 'pricing'
    }
    return render(request, 'tailor/dashboard/pricing.html', context)


@tailor_admin_required
def dashboard_pricing_add(request):
    settings_obj = get_tailor_settings()
    if request.method == 'POST':
        category = request.POST.get('category')
        service_name = request.POST.get('service_name')
        price = request.POST.get('price')
        icon = request.POST.get('icon') or 'fa-scissors'
        description = request.POST.get('description')
        status = request.POST.get('status') == 'on'
        
        TailorService.objects.create(
            category=category,
            service_name=service_name,
            price=price,
            icon=icon,
            description=description,
            status=status
        )
        messages.success(request, f"Service '{service_name}' added successfully.")
        return redirect('tailor:dashboard_pricing')
    return render(request, 'tailor/dashboard/pricing_form.html', {'settings': settings_obj, 'action': 'Add'})


@tailor_admin_required
def dashboard_pricing_edit(request, pk):
    settings_obj = get_tailor_settings()
    service = get_object_or_404(TailorService, pk=pk)
    if request.method == 'POST':
        service.category = request.POST.get('category')
        service.service_name = request.POST.get('service_name')
        service.price = request.POST.get('price')
        service.icon = request.POST.get('icon')
        service.description = request.POST.get('description')
        service.status = request.POST.get('status') == 'on'
        service.save()
        messages.success(request, f"Service '{service.service_name}' updated successfully.")
        return redirect('tailor:dashboard_pricing')
    return render(request, 'tailor/dashboard/pricing_form.html', {'settings': settings_obj, 'service': service, 'action': 'Edit'})


@tailor_admin_required
def dashboard_pricing_delete(request, pk):
    service = get_object_or_404(TailorService, pk=pk)
    name = service.service_name
    service.delete()
    messages.success(request, f"Service '{name}' was deleted.")
    return redirect('tailor:dashboard_pricing')

# =====================================================================
# Dashboard CRUD - Reviews
# =====================================================================
@tailor_admin_required
def dashboard_reviews(request):
    settings_obj = get_tailor_settings()
    reviews = TailorReview.objects.all()
    context = {
        'settings': settings_obj,
        'reviews': reviews,
        'active_tab': 'reviews'
    }
    return render(request, 'tailor/dashboard/reviews.html', context)


@tailor_admin_required
def dashboard_review_approve(request, pk):
    review = get_object_or_404(TailorReview, pk=pk)
    review.status = True
    review.save()
    messages.success(request, "Review approved and is now visible on main website.")
    return redirect('tailor:dashboard_reviews')


@tailor_admin_required
def dashboard_review_delete(request, pk):
    review = get_object_or_404(TailorReview, pk=pk)
    review.delete()
    messages.success(request, "Review deleted.")
    return redirect('tailor:dashboard_reviews')

# =====================================================================
# Dashboard CRUD - Offers
# =====================================================================
@tailor_admin_required
def dashboard_offers(request):
    settings_obj = get_tailor_settings()
    offers = TailorOffer.objects.all()
    context = {
        'settings': settings_obj,
        'offers': offers,
        'active_tab': 'offers'
    }
    return render(request, 'tailor/dashboard/offers.html', context)


@tailor_admin_required
def dashboard_offer_add(request):
    settings_obj = get_tailor_settings()
    if request.method == 'POST':
        title = request.POST.get('title')
        code = request.POST.get('code')
        description = request.POST.get('description')
        discount = request.POST.get('discount')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        status = request.POST.get('status') == 'on'
        
        TailorOffer.objects.create(
            title=title,
            code=code,
            description=description,
            discount=discount,
            start_date=start_date,
            end_date=end_date,
            status=status
        )
        messages.success(request, "Offer coupon created successfully.")
        return redirect('tailor:dashboard_offers')
    return render(request, 'tailor/dashboard/offer_form.html', {'settings': settings_obj, 'action': 'Add'})


@tailor_admin_required
def dashboard_offer_edit(request, pk):
    settings_obj = get_tailor_settings()
    offer = get_object_or_404(TailorOffer, pk=pk)
    if request.method == 'POST':
        offer.title = request.POST.get('title')
        offer.code = request.POST.get('code')
        offer.description = request.POST.get('description')
        offer.discount = request.POST.get('discount')
        offer.start_date = request.POST.get('start_date')
        offer.end_date = request.POST.get('end_date')
        offer.status = request.POST.get('status') == 'on'
        offer.save()
        messages.success(request, "Offer coupon updated successfully.")
        return redirect('tailor:dashboard_offers')
    return render(request, 'tailor/dashboard/offer_form.html', {'settings': settings_obj, 'offer': offer, 'action': 'Edit'})


@tailor_admin_required
def dashboard_offer_delete(request, pk):
    offer = get_object_or_404(TailorOffer, pk=pk)
    offer.delete()
    messages.success(request, "Offer coupon deleted.")
    return redirect('tailor:dashboard_offers')

# =====================================================================
# Dashboard Reports
# =====================================================================
@tailor_admin_required
def dashboard_reports(request):
    settings_obj = get_tailor_settings()
    
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    orders = TailorOrder.objects.select_related('customer', 'service').all()
    payments = TailorPayment.objects.select_related('order__customer').all()
    
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
        payments = payments.filter(payment_date__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)
        payments = payments.filter(payment_date__date__lte=end_date)
        
    total_sales = orders.aggregate(total=Sum('amount'))['total'] or 0.00
    total_received = payments.aggregate(total=Sum('amount_paid'))['total'] or 0.00
    total_outstanding = total_sales - total_received
    
    context = {
        'settings': settings_obj,
        'orders': orders,
        'payments': payments,
        'total_sales': total_sales,
        'total_received': total_received,
        'total_outstanding': total_outstanding,
        'start_date': start_date,
        'end_date': end_date,
        'active_tab': 'reports'
    }
    return render(request, 'tailor/dashboard/reports.html', context)

# =====================================================================
# Dashboard Settings
# =====================================================================
@tailor_admin_required
def dashboard_settings(request):
    settings_obj = get_tailor_settings()
    if not settings_obj.pk:
        settings_obj.save()
        
    if request.method == 'POST':
        settings_obj.brand_name = request.POST.get('brand_name')
        settings_obj.phone = request.POST.get('phone')
        settings_obj.email = request.POST.get('email')
        settings_obj.whatsapp = request.POST.get('whatsapp')
        settings_obj.address = request.POST.get('address')
        settings_obj.google_map = request.POST.get('google_map')
        
        if request.FILES.get('logo'):
            settings_obj.logo = request.FILES.get('logo')
            
        settings_obj.save()
        messages.success(request, "Boutique settings updated successfully.")
        return redirect('tailor:dashboard_settings')
        
    context = {
        'settings': settings_obj,
        'active_tab': 'settings'
    }
    return render(request, 'tailor/dashboard/settings.html', context)
