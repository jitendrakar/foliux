from .models import RestaurantInfo, OpeningHour, SocialLink

def restaurant_context(request):
    info = RestaurantInfo.objects.first()
    if not info:
        # Create a default instance for visual demonstration if none exists in db
        info = RestaurantInfo(
            name="L'Étoile Dorée",
            tagline="Fine Dining & Culinary Excellence",
            phone="+1 (555) 123-4567",
            email="reservations@letoiledoree.com",
            address="123 Gourmet Boulevard, Foodie City, FC 90210",
            whatsapp_number="+15551234567",
            about_text="Established in 2018, L'Étoile Dorée brings the elegance of classic French techniques combined with modern global flavors to your table. Our team led by Chef Pierre Laurent focuses on using fresh, seasonal, locally-sourced ingredients to create unforgettable dishes that excite the senses.",
            google_maps_iframe='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3022.2157071060975!2d-73.98784412342938!3d40.75797873483665!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x89c2585f55555555%3A0x5eebdc409386d34e!2sTimes%20Square!5e0!3m2!1sen!2sus!4v1700000000000!5m2!1sen!2sus'
        )
    
    opening_hours = OpeningHour.objects.all()
    social_links = SocialLink.objects.all()
    
    return {
        'restaurant_info': info,
        'opening_hours': opening_hours,
        'social_links': social_links,
    }
