from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from .models import Category, MenuItem, GalleryItem, Testimonial, BlogPost, ContactMessage, Reservation, NewsletterSubscription
from .forms import ReservationForm, ContactForm, NewsletterForm

def home(request):
    featured_items = MenuItem.objects.filter(is_available=True).filter(Q(is_best_seller=True) | Q(is_chef_special=True))[:6]
    categories = Category.objects.all()[:4]
    testimonials = Testimonial.objects.filter(is_featured=True)[:3]
    recent_posts = BlogPost.objects.filter(is_published=True)[:3]
    gallery_items = GalleryItem.objects.all()[:8]
    
    reservation_form = ReservationForm()
    newsletter_form = NewsletterForm()
    
    context = {
        'featured_items': featured_items,
        'categories': categories,
        'testimonials': testimonials,
        'recent_posts': recent_posts,
        'gallery_items': gallery_items,
        'reservation_form': reservation_form,
        'newsletter_form': newsletter_form,
        'active_page': 'home',
    }
    return render(request, 'restaurant/home.html', context)

def about(request):
    testimonials = Testimonial.objects.filter(is_featured=True)[:3]
    context = {
        'testimonials': testimonials,
        'active_page': 'about',
    }
    return render(request, 'restaurant/about.html', context)

def menu(request):
    query = request.GET.get('q', '')
    category_slug = request.GET.get('category', '')
    is_veg = request.GET.get('veg', '')
    is_best_seller = request.GET.get('best_seller', '')
    is_chef_special = request.GET.get('chef_special', '')
    sort_by = request.GET.get('sort', '')
    
    items = MenuItem.objects.filter(is_available=True)
    
    if query:
        items = items.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category_slug:
        items = items.filter(category__slug=category_slug)
    if is_veg == '1':
        items = items.filter(is_veg=True)
    if is_best_seller == '1':
        items = items.filter(is_best_seller=True)
    if is_chef_special == '1':
        items = items.filter(is_chef_special=True)
        
    if sort_by == 'price_asc':
        items = items.order_by('price')
    elif sort_by == 'price_desc':
        items = items.order_by('-price')
        
    categories = Category.objects.all()
    
    context = {
        'items': items,
        'categories': categories,
        'selected_category': category_slug,
        'query': query,
        'is_veg': is_veg,
        'is_best_seller': is_best_seller,
        'is_chef_special': is_chef_special,
        'sort_by': sort_by,
        'active_page': 'menu',
    }
    return render(request, 'restaurant/menu.html', context)

def categories(request):
    categories_list = Category.objects.all()
    context = {
        'categories_list': categories_list,
        'active_page': 'categories',
    }
    return render(request, 'restaurant/categories.html', context)

def specials(request):
    special_items = MenuItem.objects.filter(is_available=True, is_chef_special=True)
    context = {
        'special_items': special_items,
        'active_page': 'specials',
    }
    return render(request, 'restaurant/specials.html', context)

def gallery(request):
    items = GalleryItem.objects.all()
    context = {
        'items': items,
        'active_page': 'gallery',
    }
    return render(request, 'restaurant/gallery.html', context)

def reservation(request):
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your table has been reserved successfully! We will contact you soon to confirm.")
            return redirect('reservation')
        else:
            messages.error(request, "There was an error in your reservation details. Please check below.")
    else:
        form = ReservationForm()
        
    context = {
        'form': form,
        'active_page': 'reservation',
    }
    return render(request, 'restaurant/reservation.html', context)

def testimonials(request):
    reviews = Testimonial.objects.all()
    context = {
        'reviews': reviews,
        'active_page': 'testimonials',
    }
    return render(request, 'restaurant/testimonials.html', context)

def blog_list(request):
    posts = BlogPost.objects.filter(is_published=True)
    context = {
        'posts': posts,
        'active_page': 'blog',
    }
    return render(request, 'restaurant/blog_list.html', context)

def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    recent_posts = BlogPost.objects.filter(is_published=True).exclude(id=post.id)[:3]
    context = {
        'post': post,
        'recent_posts': recent_posts,
        'active_page': 'blog',
    }
    return render(request, 'restaurant/blog_detail.html', context)

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you for contacting us! We will get back to you shortly.")
            return redirect('contact')
        else:
            messages.error(request, "There was an error in your contact form. Please check below.")
    else:
        form = ContactForm()
        
    context = {
        'form': form,
        'active_page': 'contact',
    }
    return render(request, 'restaurant/contact.html', context)

def newsletter_subscribe(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, "Email address is required.")
            return redirect(request.META.get('HTTP_REFERER', 'home'))
            
        if NewsletterSubscription.objects.filter(email=email).exists():
            messages.info(request, "You are already subscribed to our newsletter.")
        else:
            NewsletterSubscription.objects.create(email=email)
            messages.success(request, "Thank you for subscribing to our newsletter!")
            
    return redirect(request.META.get('HTTP_REFERER', 'home'))
