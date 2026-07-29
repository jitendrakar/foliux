import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, Http404
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from .models import (
    NPITSConfig, NPITSCategory, NPITSProduct, 
    NPITSAffiliateLink, NPITSArticle, NPITSSeoLanding
)

def _get_common_context():
    """Helper to load navigation categories and system configs."""
    associate_id = NPITSConfig.get_setting("AMAZON_ASSOCIATE_ID", "npits09-21")
    categories = NPITSCategory.objects.filter(parent__isnull=True).order_by('order', 'name')
    featured_cats = NPITSCategory.objects.filter(is_featured=True)[:8]
    seo_landings = NPITSSeoLanding.objects.all()[:10]
    return {
        'associate_id': associate_id,
        'nav_categories': categories,
        'featured_categories': featured_cats,
        'nav_seo_landings': seo_landings,
    }


def home_view(request):
    """NPITS Home Page with Hero Banner, Featured Categories, Curated Deals, & Buying Guides."""
    context = _get_common_context()
    
    # Featured Products & Deals
    featured_products = NPITSProduct.objects.filter(is_active=True, is_featured=True)[:8]
    if not featured_products.exists():
        featured_products = NPITSProduct.objects.filter(is_active=True)[:8]

    top_deals = NPITSProduct.objects.filter(is_active=True).order_by('-rating', 'price')[:6]
    latest_articles = NPITSArticle.objects.filter(is_published=True)[:4]
    
    # Static list of top curated buying guides for quick access
    curated_guides = [
        {'title': 'Best 1TB HDD', 'slug': 'best-1tb-hdd', 'icon': 'fas fa-hdd', 'desc': 'Top high-capacity hard drives for storage'},
        {'title': 'Best 512GB SSD', 'slug': 'best-512gb-ssd', 'icon': 'fas fa-memory', 'desc': 'Fast high-performance SSDs for OS & apps'},
        {'title': 'Best 1TB SSD', 'slug': 'best-1tb-ssd', 'icon': 'fas fa-bolt', 'desc': 'Ultimate ultra-fast NVMe and SATA SSDs'},
        {'title': 'Best Gaming Mouse', 'slug': 'best-gaming-mouse', 'icon': 'fas fa-mouse', 'desc': 'Precision RGB ergonomic gaming mice'},
        {'title': 'Best Mechanical Keyboard', 'slug': 'best-mechanical-keyboard', 'icon': 'fas fa-keyboard', 'desc': 'Tactile mechanical switch keyboards'},
        {'title': 'Best Monitor under ₹10,000', 'slug': 'best-monitor-under-10000', 'icon': 'fas fa-desktop', 'desc': 'Full HD IPS monitors for work & play'},
        {'title': 'Best Printer for Home', 'slug': 'best-printer-for-home', 'icon': 'fas fa-print', 'desc': 'All-in-one wireless ink tank printers'},
        {'title': 'Best Laptop under ₹50,000', 'slug': 'best-laptop-under-50000', 'icon': 'fas fa-laptop', 'desc': 'Top budget performance laptops'},
    ]

    context.update({
        'meta_title': 'Nehru Place IT Services - Best Computer Hardware, SSD, HDD, Laptops & Accessories Comparison',
        'meta_description': 'Find the best deals on Computer Accessories, SSDs, HDDs, Monitors, Laptops, Keyboards, and PC Hardware with live Amazon price comparison on Nehru Place IT Services.',
        'featured_products': featured_products,
        'top_deals': top_deals,
        'latest_articles': latest_articles,
        'curated_guides': curated_guides,
    })
    return render(request, 'npits/home.html', context)


def category_detail_view(request, slug):
    """Category Product Listing Page with Filtering and Pagination."""
    category = get_object_or_404(NPITSCategory, slug=slug)
    context = _get_common_context()

    # Base Queryset
    subcats = category.subcategories.all()
    cat_ids = [category.id] + list(subcats.values_list('id', flat=True))
    products_qs = NPITSProduct.objects.filter(category_id__in=cat_ids, is_active=True)

    # Filter by Capacity
    capacity_filter = request.GET.get('capacity')
    if capacity_filter:
        products_qs = products_qs.filter(capacity__iexact=capacity_filter)

    # Filter by Brand
    brand_filter = request.GET.get('brand')
    if brand_filter:
        products_qs = products_qs.filter(brand__iexact=brand_filter)

    # Filter by Max Price
    max_price = request.GET.get('max_price')
    if max_price and max_price.isdigit():
        products_qs = products_qs.filter(price__lte=float(max_price))

    # Sort
    sort_by = request.GET.get('sort', 'featured')
    if sort_by == 'price_low':
        products_qs = products_qs.order_by('price')
    elif sort_by == 'price_high':
        products_qs = products_qs.order_by('-price')
    elif sort_by == 'rating':
        products_qs = products_qs.order_by('-rating')
    else:
        products_qs = products_qs.order_by('-is_featured', '-rating')

    # Available Brands & Capacities for filter sidebar
    available_brands = NPITSProduct.objects.filter(category_id__in=cat_ids, is_active=True).values_list('brand', flat=True).distinct()
    available_capacities = NPITSProduct.objects.filter(category_id__in=cat_ids, is_active=True).exclude(capacity='').values_list('capacity', flat=True).distinct()

    # Best Product (Highest Rating / Featured) & Best Price (Lowest Price)
    all_cat_products = NPITSProduct.objects.filter(category_id__in=cat_ids, is_active=True)
    best_product = all_cat_products.order_by('-is_featured', '-rating', '-review_count').first()
    best_price_product = all_cat_products.order_by('price').first()

    paginator = Paginator(products_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context.update({
        'category': category,
        'subcategories': subcats,
        'products': page_obj,
        'best_product': best_product,
        'best_price_product': best_price_product,
        'available_brands': available_brands,
        'available_capacities': available_capacities,
        'meta_title': f"Best {category.name} in India - Reviews & Lowest Prices | Nehru Place IT Services",
        'meta_description': f"Browse top-rated {category.name} with price comparison, technical specs, user ratings, and direct Amazon deals.",
    })
    return render(request, 'npits/category_detail.html', context)


def product_detail_view(request, slug):
    """Detailed Product View with Specs, Pros/Cons, Rating, Affiliate Buy Link, and Schema.org Markup."""
    product = get_object_or_404(NPITSProduct, slug=slug, is_active=True)
    context = _get_common_context()

    # Tracked Amazon Buy Link
    amazon_buy_url = product.get_tracked_amazon_url()
    
    # Related Products in same category
    related_products = NPITSProduct.objects.filter(category=product.category, is_active=True).exclude(id=product.id)[:4]
    affiliate_links = product.affiliate_links.filter(in_stock=True)

    # Schema.org Product JSON-LD structured data
    schema_markup = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": product.title,
        "image": [product.image_url] if product.image_url else [],
        "description": product.short_description or product.title,
        "sku": product.asin or str(product.id),
        "brand": {
            "@type": "Brand",
            "name": product.brand
        },
        "offers": {
            "@type": "Offer",
            "url": amazon_buy_url,
            "priceCurrency": "INR",
            "price": str(product.price),
            "availability": "https://schema.org/InStock",
            "seller": {
                "@type": "Organization",
                "name": "Amazon India"
            }
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": str(product.rating),
            "reviewCount": str(product.review_count)
        }
    }

    context.update({
        'product': product,
        'amazon_buy_url': amazon_buy_url,
        'affiliate_links': affiliate_links,
        'related_products': related_products,
        'schema_markup_json': json.dumps(schema_markup),
        'meta_title': product.meta_title or f"{product.title} - Price, Specs & Review | Nehru Place IT Services",
        'meta_description': product.meta_description or f"Buy {product.title} at best price of ₹{product.price}. Features: {product.short_description[:120] if product.short_description else product.title}.",
    })
    return render(request, 'npits/product_detail.html', context)


def seo_landing_view(request, slug):
    """Custom SEO Landing Page View (e.g. /npits/best-1tb-hdd/, /npits/best-512gb-ssd/)."""
    context = _get_common_context()
    
    # Try fetching database NPITSSeoLanding
    landing = NPITSSeoLanding.objects.filter(slug=slug).first()
    
    if landing:
        products_qs = landing.featured_products.filter(is_active=True)
        if not products_qs.exists() and landing.target_category:
            products_qs = NPITSProduct.objects.filter(category=landing.target_category, is_active=True)
            if landing.capacity_filter:
                products_qs = products_qs.filter(capacity__icontains=landing.capacity_filter)
            if landing.max_price:
                products_qs = products_qs.filter(price__lte=landing.max_price)
        
        products = products_qs.order_by('-rating', 'price')[:10]
        
        context.update({
            'landing': landing,
            'title': landing.title,
            'h1_title': landing.h1_title,
            'intro_text': landing.intro_text,
            'products': products,
            'meta_title': landing.meta_title or f"{landing.title} | Nehru Place IT Services",
            'meta_description': landing.meta_description or f"Find the best choices for {landing.title} with complete buying advice and Amazon price comparison.",
        })
        return render(request, 'npits/seo_landing.html', context)

    # Dynamic fallback based on slug keywords
    clean_slug = slug.replace('best-', '').replace('-in-india', '').replace('-', ' ')
    matched_products = NPITSProduct.objects.filter(
        Q(title__icontains=clean_slug) | Q(category__name__icontains=clean_slug) | Q(capacity__icontains=clean_slug),
        is_active=True
    ).order_by('-rating', 'price')[:10]

    if not matched_products.exists():
        matched_products = NPITSProduct.objects.filter(is_active=True)[:10]

    dynamic_title = slug.replace('-', ' ').title()
    context.update({
        'title': dynamic_title,
        'h1_title': f"Top Recommended {dynamic_title}",
        'intro_text': f"Explore our expert recommendation list for {dynamic_title}. Updated with current Amazon India prices, customer ratings, and technical specifications.",
        'products': matched_products,
        'meta_title': f"{dynamic_title} - Price & Buyer Guide | Nehru Place IT Services",
        'meta_description': f"Compare and buy {dynamic_title} at lowest prices on Amazon India.",
    })
    return render(request, 'npits/seo_landing.html', context)


def search_view(request):
    """Multi-Field Search Page."""
    query = request.GET.get('q', '').strip()
    context = _get_common_context()

    products_qs = NPITSProduct.objects.none()
    if query:
        products_qs = NPITSProduct.objects.filter(
            Q(title__icontains=query) |
            Q(brand__icontains=query) |
            Q(category__name__icontains=query) |
            Q(capacity__icontains=query) |
            Q(short_description__icontains=query),
            is_active=True
        ).order_by('-rating', 'price')

    paginator = Paginator(products_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context.update({
        'query': query,
        'products': page_obj,
        'total_results': products_qs.count(),
        'meta_title': f"Search results for '{query}' | Nehru Place IT Services",
        'meta_description': f"Search results for {query} hardware and computer accessories on Nehru Place IT Services.",
    })
    return render(request, 'npits/search_results.html', context)


def blog_list_view(request):
    """IT Buying Guides and Articles List Page."""
    context = _get_common_context()
    articles_list = NPITSArticle.objects.filter(is_published=True)

    paginator = Paginator(articles_list, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context.update({
        'articles': page_obj,
        'meta_title': 'IT Hardware Buying Guides & Computer Comparison Articles | Nehru Place IT Services',
        'meta_description': 'Read expert IT buying guides, SSD vs HDD comparisons, gaming hardware recommendations, and laptop buying advice on Nehru Place IT Services.',
    })
    return render(request, 'npits/blog_list.html', context)


def blog_detail_view(request, slug):
    """Article & Buying Guide Detail Page."""
    article = get_object_or_404(NPITSArticle, slug=slug, is_published=True)
    context = _get_common_context()

    related_articles = NPITSArticle.objects.filter(is_published=True).exclude(id=article.id)[:3]
    top_recommended_products = NPITSProduct.objects.filter(is_active=True, is_featured=True)[:4]

    context.update({
        'article': article,
        'related_articles': related_articles,
        'top_recommended_products': top_recommended_products,
        'meta_title': article.meta_title or f"{article.title} | Nehru Place IT Services",
        'meta_description': article.meta_description or article.summary[:150],
    })
    return render(request, 'npits/blog_detail.html', context)


def sitemap_view(request):
    """Dynamic XML Sitemap for NPITS Pages."""
    domain = request.build_absolute_uri('/')[:-1]
    
    urls = [
        f"{domain}/npits/",
        f"{domain}/npits/blog/",
    ]
    
    for cat in NPITSCategory.objects.all():
        urls.append(f"{domain}/npits/c/{cat.slug}/")

    for prod in NPITSProduct.objects.filter(is_active=True):
        urls.append(f"{domain}/npits/p/{prod.slug}/")

    for land in NPITSSeoLanding.objects.all():
        urls.append(f"{domain}/npits/{land.slug}/")

    for art in NPITSArticle.objects.filter(is_published=True):
        urls.append(f"{domain}/npits/blog/{art.slug}/")

    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        xml_content += f'  <url><loc>{u}</loc><changefreq>weekly</changefreq></url>\n'
    xml_content += '</urlset>'

    return HttpResponse(xml_content, content_type="application/xml")


def autocomplete_view(request):
    """JSON API Endpoint for Real-Time Search Suggestions as User Types."""
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    products = NPITSProduct.objects.filter(
        Q(title__icontains=query) | Q(brand__icontains=query) | Q(category__name__icontains=query),
        is_active=True
    ).select_related('category')[:8]

    results = []
    for p in products:
        results.append({
            'title': p.title,
            'slug': p.slug,
            'url': f"/npits/p/{p.slug}/",
            'price': f"₹{p.price:,.0f}",
            'brand': p.brand,
            'category': p.category.name,
            'image': p.image_url
        })

    return JsonResponse({'results': results})
