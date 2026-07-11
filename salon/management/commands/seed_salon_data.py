import random
from datetime import datetime, date, timedelta
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.utils import timezone
from salon.models import (
    SalonUser, SalonCategory, SalonService, SalonStylist, 
    SalonGallery, SalonTestimonial, SalonOffer, SalonBlog, 
    SalonAppointment, SalonSetting
)

class Command(BaseCommand):
    help = 'Seeds the salon database with realistic Indian demo data.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding Salon database...')

        # ----------------------------------------------------
        # 1. Clear Existing Data (only for salon app)
        # ----------------------------------------------------
        SalonUser.objects.all().delete()
        SalonCategory.objects.all().delete()
        SalonService.objects.all().delete()
        SalonStylist.objects.all().delete()
        SalonGallery.objects.all().delete()
        SalonTestimonial.objects.all().delete()
        SalonOffer.objects.all().delete()
        SalonBlog.objects.all().delete()
        SalonAppointment.objects.all().delete()
        SalonSetting.objects.all().delete()

        # ----------------------------------------------------
        # 2. Seed Settings
        # ----------------------------------------------------
        setting = SalonSetting.objects.create(
            salon_name="SalonX – Premium Indian Unisex Salon",
            address="Level 2, Premium Galleria Mall, Brigade Road, Bangalore, Karnataka - 560001",
            phone="+91 98718 08718",
            email="bookings@salonx.com",
            whatsapp="+91 98718 08718",
            facebook="https://facebook.com/salonx",
            instagram="https://instagram.com/salonx_premium",
            youtube="https://youtube.com/salonx_india",
            opening_hours="Mon - Sun: 9:00 AM - 9:30 PM",
            google_map='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3887.973418579979!2d77.6074127!3d12.9735496!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3bae167d30f4e1f7%3A0xf695df61cf1c1f54!2sMG%20Road%2C%20Bengaluru%2C%20Karnataka!5e0!3m2!1sen!2sin!4v1680000000000!5m2!1sen!2sin'
        )
        self.stdout.write('- Seeded settings')

        # ----------------------------------------------------
        # 3. Seed Admin and Customers (101 users total)
        # ----------------------------------------------------
        # Admin User
        admin_user = SalonUser(
            name="Jitendra Kar",
            mobile="9871808718",
            email="jitendra.kar@gmail.com",
            role="admin"
        )
        admin_user.set_password("salonx123")
        admin_user.save()

        # Lists for generating customers
        first_names_male = ["Aarav", "Kabir", "Vivaan", "Aditya", "Arjun", "Ishan", "Sai", "Reyansh", "Krishna", "Atharva", "Shaurya", "Rohit", "Rahul", "Deepak", "Sanjay", "Vijay", "Ramesh", "Suresh", "Amit", "Vikram", "Abhishek", "Kunal", "Rohan", "Aniket", "Mayank", "Nikhil", "Pranav", "Rajat", "Sandeep", "Tushar"]
        first_names_female = ["Aadya", "Diya", "Saanvi", "Anya", "Ananya", "Aadhya", "Aaradhya", "Pihu", "Ira", "Sana", "Riya", "Anjali", "Priyanka", "Divya", "Pooja", "Neha", "Sneha", "Preeti", "Kavita", "Jyoti", "Komal", "Meera", "Nisha", "Payal", "Ritu", "Sakshi", "Tanvi", "Urvi", "Vaishnali", "Yashasvi"]
        last_names = ["Sharma", "Verma", "Patel", "Mehta", "Nair", "Joshi", "Rao", "Reddy", "Sen", "Chatterjee", "Gupta", "Singh", "Kumar", "Mishra", "Trivedi", "Shah", "Iyer", "Pillai", "Choudhury", "Das", "Bose", "Kulkarni", "Deshmukh", "Bhat", "Menon", "Dubey", "Pandey", "Saxena", "Soni", "Kapoor"]

        customers = []
        # Generate 100 customer users
        for i in range(100):
            gender = random.choice(['male', 'female'])
            first_name = random.choice(first_names_male) if gender == 'male' else random.choice(first_names_female)
            last_name = random.choice(last_names)
            full_name = f"{first_name} {last_name}"
            
            email = f"{first_name.lower()}.{last_name.lower()}{i+1}@gmail.com"
            mobile = f"{random.choice([9, 8, 7, 6])}{random.randint(100000000, 999999999)}"
            
            cust = SalonUser(
                name=full_name,
                mobile=mobile,
                email=email,
                role="customer"
            )
            cust.set_password("customer123")
            cust.save()
            customers.append(cust)

        self.stdout.write(f'- Seeded 1 Admin and {len(customers)} Customers')

        # ----------------------------------------------------
        # 4. Seed Stylists (10)
        # ----------------------------------------------------
        stylist_data = [
            {"name": "Rajesh Kumar", "designation": "Creative Director & Master Stylist", "experience": "12 Years", "desc": "Expert in precision haircuts, custom hair styling, and advanced bridal work. Trained at Vidal Sassoon Academy, London."},
            {"name": "Priya Nair", "designation": "Senior Skin & Beauty Expert", "experience": "9 Years", "desc": "Specialist in dermalogica facials, anti-aging therapies, and premium bridal makeup. Highly experienced in Indian skin types."},
            {"name": "Anil Sharma", "designation": "Master Hair Therapist & Colorist", "experience": "8 Years", "desc": "Expert in Keratin, Olaplex treatments, Global Hair Coloring, and balayage highlights. Knows what suits your hair best."},
            {"name": "Kavita Reddy", "designation": "Senior Makeup Artist", "experience": "7 Years", "desc": "Specialist in HD Bridal Makeup, Airbrush Makeup, and portfolio shoots. Has styled several model events in South India."},
            {"name": "Sanjay Mehta", "designation": "Senior Barber & Grooming Expert", "experience": "6 Years", "desc": "Expert in men's premium haircuts, beard styling, hot towel shaves, and skin detailing for men."},
            {"name": "Meera Joshi", "designation": "Spa Therapist & Wellness Specialist", "experience": "10 Years", "desc": "Certified in Swedish, Deep Tissue, and Aromatherapy massages. Specializes in stress relief and body rejuvenation."},
            {"name": "Rohan Das", "designation": "Creative Hair Stylist", "experience": "5 Years", "desc": "Specialist in modern haircuts, trendy hair tattoos, blow dry styles, and temporary extensions for party makeovers."},
            {"name": "Sneha Sen", "designation": "Nail Artist & Extension Specialist", "experience": "4 Years", "desc": "Passionate about Gel nail extensions, Acrylic overlays, 3D Nail Art, and luxury pedicure treatments."},
            {"name": "Vikram Singh", "designation": "Hair Care Consultant & Stylist", "experience": "6 Years", "desc": "Specialist in hair-fall treatments, dandruff therapies, and customized hair spa rituals."},
            {"name": "Divya Gupta", "designation": "Bridal Makeover Consultant", "experience": "5 Years", "desc": "Expert in bridal hair extensions, saree draping, premium makeup packages, and pre-bridal grooming rituals."}
        ]

        stylist_photos = [
            "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80",
            "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=300&q=80",
            "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=300&q=80",
            "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=300&q=80",
            "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80",
            "https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=300&q=80",
            "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=300&q=80",
            "https://images.unsplash.com/photo-1567532939604-b6b5b0db2604?auto=format&fit=crop&w=300&q=80",
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80",
            "https://images.unsplash.com/photo-1554151228-14d9def656e4?auto=format&fit=crop&w=300&q=80"
        ]

        stylists = []
        for idx, item in enumerate(stylist_data):
            stylist = SalonStylist.objects.create(
                name=item["name"],
                designation=item["designation"],
                experience=item["experience"],
                description=item["desc"],
                photo=stylist_photos[idx],
                status=True
            )
            stylists.append(stylist)

        self.stdout.write(f'- Seeded {len(stylists)} Stylists')

        # ----------------------------------------------------
        # 5. Seed Categories & Services (25+)
        # ----------------------------------------------------
        services_by_cat = {
            "Hair (Men)": [
                {"name": "Executive Hair Cut & Styling", "price": 399, "dur": 30, "desc": "Clean trim, wash, conditioning, and professional styling.", "img": "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=400&q=80"},
                {"name": "Luxury Beard Trim & Detailing", "price": 249, "dur": 20, "desc": "Razor detailing, hot towel compress, and premium beard oil application.", "img": "https://images.unsplash.com/photo-1621605815971-fbc98d665033?auto=format&fit=crop&w=400&q=80"},
                {"name": "Men's Hair Color (L'Oreal)", "price": 999, "dur": 45, "desc": "Ammonia-free grey coverage or fashion streak hair coloring.", "img": "https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=400&q=80"},
                {"name": "Premium Men's Anti-Hairfall Spa", "price": 1199, "dur": 50, "desc": "Scalp scrub, hair mask application, steam, and high-frequency therapy.", "img": "https://images.unsplash.com/photo-1517832606299-7ae9b720a186?auto=format&fit=crop&w=400&q=80"}
            ],
            "Hair (Women)": [
                {"name": "Signature Hair Cut & Blow Dry", "price": 799, "dur": 45, "desc": "Advanced multi-layer haircut tailored by expert stylist with wash and styling.", "img": "https://images.unsplash.com/photo-1595476108010-b4d1f102b1b1?auto=format&fit=crop&w=400&q=80"},
                {"name": "Global Hair Color (Kérastase)", "price": 2499, "dur": 90, "desc": "Rich, premium global hair color with ultimate shine and complete grey coverage.", "img": "https://images.unsplash.com/photo-1605497746444-ac9dbd324ce9?auto=format&fit=crop&w=400&q=80"},
                {"name": "Balayage Highlights", "price": 3499, "dur": 120, "desc": "Hand-painted natural-looking highlights customized to your skin undertone.", "img": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=400&q=80"},
                {"name": "Olaplex Hair Reconstruct Treatment", "price": 2999, "dur": 60, "desc": "Deep molecular treatment to repair broken hair bonds and bring back life to damaged hair.", "img": "https://images.unsplash.com/photo-1562322140-8baeececf3df?auto=format&fit=crop&w=400&q=80"},
                {"name": "Kérastase Luxury Hair Spa", "price": 1799, "dur": 60, "desc": "Premium deep-conditioning hair spa treatment with massage for soft, frizz-free locks.", "img": "https://images.unsplash.com/photo-1519699047748-de8e457a634e?auto=format&fit=crop&w=400&q=80"}
            ],
            "Skin Care & Facials": [
                {"name": "Dermalogica Brightening Facial", "price": 2499, "dur": 60, "desc": "Premium customized facial using Dermalogica products to reduce dark spots and revive glow.", "img": "https://images.unsplash.com/photo-1512290923902-8a9f81dc236c?auto=format&fit=crop&w=400&q=80"},
                {"name": "O3+ Bridal Glow Facial", "price": 2999, "dur": 75, "desc": "Advanced whitening facial that deep cleanses, lightens tan, and leaves skin luminous.", "img": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?auto=format&fit=crop&w=400&q=80"},
                {"name": "Insta-DeTan Pack (Face & Neck)", "price": 499, "dur": 25, "desc": "Express tan removal pack formulated with natural fruit extracts and cooling mint.", "img": "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?auto=format&fit=crop&w=400&q=80"},
                {"name": "Charcoal Deep Cleanse Facial", "price": 1299, "dur": 45, "desc": "Pore tightening, blackhead removal, and oil balancing with pure activated charcoal.", "img": "https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?auto=format&fit=crop&w=400&q=80"}
            ],
            "Spa & Wellness": [
                {"name": "Swedish Full Body Massage", "price": 1799, "dur": 60, "desc": "Relaxing strokes with organic aroma oils to stimulate blood circulation and ease tension.", "img": "https://images.unsplash.com/photo-1600334089648-b0d9d3028eb2?auto=format&fit=crop&w=400&q=80"},
                {"name": "Deep Tissue Therapeutic Massage", "price": 2199, "dur": 60, "desc": "Targeted deep pressure to release chronic muscle knots and structural body pain.", "img": "https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=400&q=80"},
                {"name": "Relaxing Foot Reflexology", "price": 699, "dur": 30, "desc": "Acupressure point massage on soles to relieve body fatigue and restore balance.", "img": "https://images.unsplash.com/photo-1519699047748-de8e457a634e?auto=format&fit=crop&w=400&q=80"}
            ],
            "Nail Studio": [
                {"name": "Luxury Manicure (O.P.I)", "price": 699, "dur": 40, "desc": "Exfoliating scrub, nail shaping, cuticle care, hand massage, and professional OPI nail lacquer.", "img": "https://images.unsplash.com/photo-1610992015762-4113b700191a?auto=format&fit=crop&w=400&q=80"},
                {"name": "Luxury Pedicure (O.P.I)", "price": 899, "dur": 50, "desc": "Relaxing warm soak, foot scrub, dead skin removal, massage, and expert polish.", "img": "https://images.unsplash.com/photo-1519415510236-718bdfcd89c9?auto=format&fit=crop&w=400&q=80"},
                {"name": "Gel Nail Extensions (Set of 10)", "price": 1999, "dur": 75, "desc": "Premium glass extension tips with UV-cured gel overlay and custom base paint.", "img": "https://images.unsplash.com/photo-1604654894610-df4906f2426d?auto=format&fit=crop&w=400&q=80"},
                {"name": "Chrome Nail Art", "price": 399, "dur": 20, "desc": "Trendy mirror-effect metallic chrome styling on all 10 fingers.", "img": "https://images.unsplash.com/photo-1604654894610-df4906f2426d?auto=format&fit=crop&w=400&q=80"}
            ],
            "Bridal & Makeups": [
                {"name": "High Definition (HD) Bridal Makeup", "price": 9999, "dur": 150, "desc": "Flawless camera-ready makeup, luxury hair setting, draping, and customized lash applications.", "img": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=400&q=80"},
                {"name": "Airbrush Bridal Makeup", "price": 14999, "dur": 180, "desc": "Liquid mist foundation application for sweatproof, waterproof, 18-hour matte finish.", "img": "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?auto=format&fit=crop&w=400&q=80"},
                {"name": "Glamorous Party Makeup", "price": 2999, "dur": 60, "desc": "Elegant evening makeup, light contouring, eyeshadow, lipstick, and hair settings.", "img": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=400&q=80"},
                {"name": "Saree Draping & Styling", "price": 499, "dur": 20, "desc": "Traditional or modern style saree pleating, setting, and secure pinning.", "img": "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?auto=format&fit=crop&w=400&q=80"}
            ],
            "Packages & Combos": [
                {"name": "Pre-Bridal Glow Ritual (2 Days)", "price": 7999, "dur": 360, "desc": "Waxing, body scrub, O3+ facial, luxury pedicure, manicure, and hair spa.", "img": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=400&q=80"},
                {"name": "Luxury Groom Makeover", "price": 4999, "dur": 150, "desc": "Tan removal, premium facial, executive haircut, hair spa, beard detailing, and manicure.", "img": "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=400&q=80"},
                {"name": "Express Grooming Combo", "price": 1199, "dur": 60, "desc": "Haircut, beard trim, detanning scrub, and a quick hair spa.", "img": "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=400&q=80"}
            ]
        }

        all_services = []
        for cat_name, srvs in services_by_cat.items():
            cat = SalonCategory.objects.create(category_name=cat_name, status=True)
            for item in srvs:
                srv = SalonService.objects.create(
                    category=cat,
                    service_name=item["name"],
                    price=item["price"],
                    duration=item["dur"],
                    description=item["desc"],
                    image=item["img"],
                    status=True
                )
                all_services.append(srv)

        self.stdout.write(f'- Seeded {SalonCategory.objects.count()} Categories and {len(all_services)} Services')

        # ----------------------------------------------------
        # 6. Seed Gallery (30 images)
        # ----------------------------------------------------
        gallery_data = [
            ("Classic Undercut Styling", "Hair", "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=500&q=80"),
            ("Elegant Bridal Hair Buns", "Bridal", "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=500&q=80"),
            ("Aromatherapy Oil Massage", "Spa", "https://images.unsplash.com/photo-1600334089648-b0d9d3028eb2?auto=format&fit=crop&w=500&q=80"),
            ("Glow Facial Clay Application", "Skin", "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?auto=format&fit=crop&w=500&q=80"),
            ("Hair Makeover Transformation", "Before After", "https://images.unsplash.com/photo-1595476108010-b4d1f102b1b1?auto=format&fit=crop&w=500&q=80"),
            ("Global Blonde Balayage Work", "Hair", "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=500&q=80"),
            ("HD Bridal Face Makeup Session", "Bridal", "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=500&q=80"),
            ("Hot Stone Therapy Session", "Spa", "https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=500&q=80"),
            ("Hydro Therapy Facial Glow", "Skin", "https://images.unsplash.com/photo-1512290923902-8a9f81dc236c?auto=format&fit=crop&w=500&q=80"),
            ("Keratin Smoothing Treatment", "Before After", "https://images.unsplash.com/photo-1562322140-8baeececf3df?auto=format&fit=crop&w=500&q=80"),
            ("Modern Bob Haircut styling", "Hair", "https://images.unsplash.com/photo-1595476108010-b4d1f102b1b1?auto=format&fit=crop&w=500&q=80"),
            ("South Indian Bridal Look", "Bridal", "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?auto=format&fit=crop&w=500&q=80"),
            ("Soothing Herbal Face Steam", "Skin", "https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?auto=format&fit=crop&w=500&q=80"),
            ("Deep Tissue Shoulder Massage", "Spa", "https://images.unsplash.com/photo-1600334089648-b0d9d3028eb2?auto=format&fit=crop&w=500&q=80"),
            ("Beard Grooming Makeover", "Before After", "https://images.unsplash.com/photo-1621605815971-fbc98d665033?auto=format&fit=crop&w=500&q=80"),
            ("Sleek Pompadour haircut", "Hair", "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=500&q=80"),
            ("North Indian Wedding Styling", "Bridal", "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=500&q=80"),
            ("Deep Clean Detox Scrub", "Skin", "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?auto=format&fit=crop&w=500&q=80"),
            ("Luxury Ayurvedic Foot Bath", "Spa", "https://images.unsplash.com/photo-1519415510236-718bdfcd89c9?auto=format&fit=crop&w=500&q=80"),
            ("Dandruff Scalp Treatment", "Before After", "https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=500&q=80"),
            ("L'Oreal Professional Highlights", "Hair", "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=500&q=80"),
            ("Traditional Mehendi & Makeup", "Bridal", "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?auto=format&fit=crop&w=500&q=80"),
            ("Skin De-tan Treatment Mask", "Skin", "https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?auto=format&fit=crop&w=500&q=80"),
            ("Relaxing Neck & Back Massage", "Spa", "https://images.unsplash.com/photo-1600334089648-b0d9d3028eb2?auto=format&fit=crop&w=500&q=80"),
            ("Dull to Radiant Facial Glow", "Before After", "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?auto=format&fit=crop&w=500&q=80"),
            ("Youthful Gel Nail Art work", "Hair", "https://images.unsplash.com/photo-1604654894610-df4906f2426d?auto=format&fit=crop&w=500&q=80"),
            ("Premium Christian Bridal Styling", "Bridal", "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=500&q=80"),
            ("Charcoal Peel Off Pore Care", "Skin", "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?auto=format&fit=crop&w=500&q=80"),
            ("Tibetan Sound bowl wellness", "Spa", "https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=500&q=80"),
            ("Hair Extension Volume Add", "Before After", "https://images.unsplash.com/photo-1562322140-8baeececf3df?auto=format&fit=crop&w=500&q=80")
        ]

        for item in gallery_data:
            SalonGallery.objects.create(
                title=item[0],
                category=item[1],
                image=item[2],
                status=True
            )

        self.stdout.write(f'- Seeded {SalonGallery.objects.count()} Gallery Images')

        # ----------------------------------------------------
        # 7. Seed Testimonials (15)
        # ----------------------------------------------------
        testimonial_data = [
            ("Aarav Sharma", 5, "I visited for a haircut and shave. Rajesh is an absolute pro! The attention to detail was exceptional, and the salon's ambiance is super luxurious. Best salon in Bangalore, hands down."),
            ("Sanya Malhotra", 5, "Priya Nair is a magician! I had my bridal makeup done by her and she made me look exactly how I had envisioned. Got so many compliments. Highly recommend their bridal packages."),
            ("Kabir Singh", 5, "The Swedish massage was incredibly relaxing. The staff is polite, and they offer a welcome drink. They maintain very high levels of sanitization. Worth every rupee!"),
            ("Anjali Gupta", 4, "Got a global hair color and Keratin done. Anil explained the whole process clearly and recommended the perfect shades. The results are amazing. Deducting 1 star because of a 15-minute wait time."),
            ("Rahul Verma", 5, "Superb men's grooming station. Sanjay really knows beard styling. The hot towel shave was so refreshing. Will definitely be a regular here."),
            ("Pooja Patel", 5, "Amazing experience with Dermalogica facial. My skin feels so soft and refreshed. Priya's massage during the facial was so soothing."),
            ("Vivaan Mehta", 5, "Had hair fall issues and tried their customized hair spa. After 3 sessions, my hair fall has reduced significantly. The consultation was very detailed."),
            ("Neha Sen", 5, "Got acrylic nail extensions done by Sneha. The finishing is flawless, and the nail art design is so elegant. Got so many compliments on my hands!"),
            ("Amit Rao", 5, "Felt extremely premium. The valet service is quick. The staff is professional. Best haircut experience I have had in a long time."),
            ("Kavita Nair", 5, "Highly recommend their O3+ facial. It has completely lightened my tan. Excellent customer service and beautiful decor."),
            ("Vijay Iyer", 4, "Good service, very polite stylists. Had a hair cut and clean up. Everything was sanitized in front of me."),
            ("Sneha Hegde", 5, "Booked a pre-bridal package. From waxing to facials and hair spa, everything was handled beautifully over 2 days. Made me feel so relaxed before my wedding."),
            ("Aditya Roy", 5, "Clean, classy, and highly professional. Rajesh gave me a great fade cut. They play soft music which adds to the premium feel."),
            ("Divya Deshmukh", 5, "Best pedicure ever! The massage chairs are so comfortable, and they use high-quality OPI products. Very clean and hygienic."),
            ("Rohan Gupta", 5, "Had deep tissue massage to relieve muscle stress from workouts. Meera was highly skilled and relieved all the tension. Felt extremely relaxed.")
        ]

        testimonial_photos = [
            "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=100&q=80",
            "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=100&q=80",
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=100&q=80",
            "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=100&q=80",
            "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=100&q=80",
            "https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=100&q=80",
            "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=100&q=80",
            "https://images.unsplash.com/photo-1567532939604-b6b5b0db2604?auto=format&fit=crop&w=100&q=80",
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=100&q=80",
            "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&q=80",
            "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=100&q=80",
            "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=100&q=80",
            "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=100&q=80",
            "https://images.unsplash.com/photo-1567532939604-b6b5b0db2604?auto=format&fit=crop&w=100&q=80",
            "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=100&q=80"
        ]

        for idx, item in enumerate(testimonial_data):
            SalonTestimonial.objects.create(
                customer_name=item[0],
                rating=item[1],
                review=item[2],
                photo=testimonial_photos[idx],
                status=True
            )

        self.stdout.write(f'- Seeded {SalonTestimonial.objects.count()} Testimonials')

        # ----------------------------------------------------
        # 8. Seed Offers (10)
        # ----------------------------------------------------
        offers_data = [
            ("Monsoon Glam Magic", "Get a fresh new look this rainy season with our special packages.", "20% OFF", 5, 20),
            ("Bridal Glow Ritual", "Ensure you glow on your big day. Book our pre-bridal ritual and get massive discounts.", "Flat Rs. 2000 Off", 0, 60),
            ("Happy Hours Midweek", "Pamper yourself during weekdays between 11 AM and 4 PM.", "Flat 15% OFF", 1, 30),
            ("Student Sparkle Discount", "Show your student ID card and unlock premium salon services at student-friendly prices.", "15% OFF", 0, 180),
            ("Weekend Pamper Session", "Unwind after a busy week with our special hair spa and massage combos.", "Flat 10% OFF", 2, 10),
            ("Festive Sparkle Package", "Celebrate Diwali with our exclusive skin whitening and hair styling combo package.", "Flat Rs. 1500 Off", 15, 45),
            ("Membership Welcome Offer", "Join our salon premium club today and get a complimentary hair therapy spa on your first visit.", "Free Hair Spa", 0, 365),
            ("Valentine Couple Retreat", "Book any twin full-body therapeutic massaged sessions and enjoy complementary fruit facials.", "Free Fruit Facial", 10, 40),
            ("New User Special", "First time at SalonX? Book an appointment online and get a discount on any haircut or styling.", "Flat Rs. 150 Off", 0, 90),
            ("Pre-Bridal Groom Package", "Complete hair and skin grooming packages for the dapper Indian groom.", "Flat 20% OFF", 5, 50)
        ]

        offer_images = [
            "https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1512290923902-8a9f81dc236c?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1595476108010-b4d1f102b1b1?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1600334089648-b0d9d3028eb2?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1519699047748-de8e457a634e?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1621605815971-fbc98d665033?auto=format&fit=crop&w=500&q=80"
        ]

        for idx, item in enumerate(offers_data):
            start = date.today() - timedelta(days=item[3])
            end = date.today() + timedelta(days=item[4])
            SalonOffer.objects.create(
                title=item[0],
                description=item[1],
                discount=item[2],
                image=offer_images[idx],
                start_date=start,
                end_date=end,
                status=True
            )

        self.stdout.write(f'- Seeded {SalonOffer.objects.count()} Offers')

        # ----------------------------------------------------
        # 9. Seed Blogs (20 articles)
        # ----------------------------------------------------
        blogs_data = [
            ("5 Secrets to Prevent Hair Fall in Indian Weather", "Hair Care", 
             "Discover simple but highly effective natural remedies and styling routines to combat hair fall during humid Indian seasons.",
             "Indian weather can be tough on hair. With high humidity during monsoon and extreme heat in summers, hair roots weaken easily. "
             "In this article, our senior hair therapist Anil Sharma details 5 simple secrets to protect your hair: "
             "1. Avoid hot water washes; 2. Massage with lightweight rosemary oil weekly; 3. Eat curry leaves daily for iron; "
             "4. Do not tie wet hair; 5. Use sulfate-free shampoos. Read on to get the full hair-care routine..."),
            
            ("Ultimate Skin Care Routine for Glowing Indian Bridal Look", "Skin Care",
             "A step-by-step 3-month grooming guide for brides-to-be to get flawless glowing skin before their wedding day.",
             "Getting that luminous, radiant bridal glow requires a structured approach. "
             "Priya Nair, our beauty expert, suggests starting at least 30 to 90 days before the wedding day: "
             "- Month 1: Focus on deep cleansing and tan removal (monthly hydrafacials). "
             "- Month 2: Introduce skin brightening boosters and Vitamin C serums. "
             "- Month 3: Deep hydration therapies, stress-relief massages, and avoiding any new products to prevent allergies..."),
            
            ("Why Charcoal Facials are a Must for Urban Dwellers", "Beauty",
             "Are you exposed to traffic pollution daily? Charcoal facials can deep-clean your pores and reverse skin damage.",
             "Polluted city air carries micro-dust particles that settle deep into your pores, leading to blackheads, acne, and dullness. "
             "Charcoal has natural magnetic properties that pull out impurities from deep within the skin. "
             "Our Charcoal Deep Cleanse facial provides instant rejuvenation, controls excess oil, and tightens pores in just 45 minutes..."),
            
            ("Top Hair Color Trends for 2026: Balayage, Highlights, Global", "Hair Color",
             "Ready to refresh your style? Check out these gorgeous hair color trends that perfectly suit warm Indian skin tones.",
             "2026 is all about natural dimension and sun-kissed textures. "
             "From hand-painted caramel balayage to warm honey highlights, there are several options that look stunning on dark Indian hair. "
             "Master colorist Anil Sharma outlines how to choose the right tone based on your skin undertone, and how to maintain the vibrancy..."),
            
            ("The Art of Modern Men's Grooming: More Than Just a Trim", "Salon Tips",
             "Men's grooming has evolved. Learn how hot towel treatments, beard oils, and scalp care can elevate your professional look.",
             "Gone are the days when men's grooming was restricted to a quick 10-minute trim. "
             "Today's dapper Indian gentleman understands that healthy hair and well-detailed beards are a crucial part of personal branding. "
             "Explore the benefits of facial detox treatments, beard spa, and scalp nourishment rituals offered at SalonX..."),
            
            ("How to Choose the Perfect Bridal Makeup for Your Face Type", "Wedding",
             "HD, Airbrush, or Matte? We break down the differences to help you choose the best wedding day makeup.",
             "Every bride wants to look flawless under high-definition cameras and bright stage lighting. "
             "However, choice of makeup depends on your skin type: "
             "- Airbrush is perfect for oily skin as it is sweatproof and water-resistant. "
             "- HD makeup is great for dry skin as it gives a natural dewy finish. "
             "Consult with our bridal makeup artist Kavita Reddy to make the best choice..."),
            
            ("7 Essential Tips to Protect Colored Hair from Sun Damage", "Hair Color",
             "Colored your hair recently? Follow these expert tips to prevent your expensive hair color from fading in the harsh Indian sun.",
             "UV rays are the number one enemy of dyed hair. They oxidize the color molecules, making highlights look brassy. "
             "Keep your color fresh by using UV protection hair sprays, washing with cold water, using color-protecting masques, "
             "and wearing a hat or scarf when step out during peak afternoon hours..."),
            
            ("Understanding Dandruff: Root Causes and Professional Solutions", "Hair Care",
             "Dandruff isn't just dry skin – it's a fungal issue. Learn about effective treatments to get a clean, healthy scalp.",
             "A flaky scalp can be embarrassing and lead to severe hair fall. "
             "Contrary to popular belief, dandruff is often caused by Malassezia, a yeast-like fungus that feeds on scalp oils. "
             "We discuss why normal anti-dandruff shampoos fail, and how professional salicylic acid scrubs and high-frequency scalp therapies work..."),
            
            ("The Magic of Swedish Massage: Physical and Mental Benefits", "Spa",
             "Feeling stressed from work? Learn how a 60-minute Swedish massage can detoxify your body and calm your mind.",
             "Sitting at a desk for 9 hours daily builds tension in the neck, shoulders, and lower back. "
             "Swedish massage uses long, gliding strokes (effleurage) and kneading (petrissage) to improve blood flow, "
             "release lactic acid buildup, and lower cortisol levels, helping you sleep better and feel completely relaxed..."),
            
            ("Nail Art Ideas that are Perfect for the Festive Season", "Latest Trends",
             "From chrome gradients to traditional gold motifs, explore beautiful nail styling trends for upcoming Indian festivals.",
             "Festivals are the perfect time to pamper your hands. "
             "This year, chrome nail extensions, metallic foil lines, and subtle gold glitter ombre are highly trending. "
             "Nail artist Sneha Sen shares easy nail care tips at home, and what kind of gel extensions last the longest..."),
            
            ("How to Get Rid of Dark Circles: Dermatologist-Approved Tips", "Skin Care",
             "Late-night screens causing dark circles? Try these skin care habits and under-eye spa treatments to look fresh.",
             "Dark circles can make you look tired and aged. "
             "While genetics play a role, lack of sleep, dehydration, and constant screen exposure exacerbate them. "
             "Our skin specialist recommends hyaluronic acid creams, caffeine serums, and specialized under-eye micro-current treatments..."),
            
            ("Pre-Bridal Grooming Checklist: When to start what", "Wedding",
             "Don't leave your grooming to the last week! Follow our master bridal checklist starting from 3 months before.",
             "A complete timeline checklist: "
             "- 3 Months: Hair coloring, weight management, laser/IPL consultations. "
             "- 2 Months: Facial treatments, body polishing, hair spa. "
             "- 1 Month: Trial makeup, trial hair styling, manicure/pedicure. "
             "- 1 Week: Waxing, threading, detanning pack, and relaxing spa. "
             "- 1 Day: Hydrating mask and a good night's sleep!"),
            
            ("5 Groom's Makeover Tips for the Modern Indian Wedding", "Wedding",
             "Grooms need pampering too! Here is how the modern Indian groom can look sharp, fresh, and polished on his wedding day.",
             "The spotlight is equally on the groom. "
             "To look your best next to the bride, start grooming 2 weeks prior: "
             "1. Get a professional haircut 5 days before (gives it time to settle); 2. Beard detailing with hot towel; "
             "3. A hydrating detan facial; 4. Manicure to ensure hands look clean in close-ups; 5. Express hair spa for shine..."),
            
            ("Keratin vs Olaplex: Which Hair Treatment is Right for You?", "Hair Care",
             "Confused between Keratin smoothing and Olaplex repair? Learn the difference so you choose the right therapy.",
             "Keratin is a protein treatment that coats the outer layer of hair to eliminate frizz, making it straight and smooth. "
             "Olaplex is a bond builder that works inside the hair shaft to repair damage from coloring or heat. "
             "If your hair is dry and frizzy, choose Keratin. If it is weak, broken, and chemically damaged, choose Olaplex..."),
            
            ("How Often Should You Get a Facial? A Skin Expert Explains", "Skin Care",
             "Is monthly facial really necessary? We analyze different skin types and recommend the ideal facial intervals.",
             "Skin cells regenerate every 28 days. "
             "Getting a professional facial once a month helps remove dead skin cells, clears clogged pores, and boosts collagen production. "
             "However, if you have acne-prone skin, a deep-cleanse charcoal facial every 15 days is recommended, while sensitive skin might need 6 weeks..."),
            
            ("Beard Grooming 101: How to maintain soft, itch-free facial hair", "Salon Tips",
             "Growing a beard is easy, maintaining it is an art. Learn how to wash, oil, and comb your beard for a neat look.",
             "An unkempt beard looks unprofessional. "
             "To avoid beard itch and dandruff (beardruffe), wash with a mild beard wash, apply a few drops of argan-based beard oil daily, "
             "and use a wooden comb to style. We also recommend monthly beard spa treatments for deep conditioning..."),
            
            ("Natural Remedies to Treat Frizzy Hair in Monsoon", "Hair Care",
             "Humid monsoon winds can turn hair into a frizzy mess. Learn simple tricks to keep your locks smooth and manageable.",
             "Monsoon humidity makes hair absorb moisture from the air, causing it to swell and frizz. "
             "Control it by using leave-in conditioners, sleeping on satin pillowcases, avoiding hair dryers on hot settings, "
             "and getting a weekly salon nourishing spa session..."),
            
            ("The Ultimate Guide to Foot Reflexology: Why Your Feet Need a Spa", "Spa",
             "Walking all day? Read about the health benefits of reflexology and how foot spa can rejuvenate your entire body.",
             "Your feet contain thousands of nerve endings connected to different organs. "
             "Foot reflexology uses targeted pressure on these points to improve digestion, reduce headache, and lower stress. "
             "It is the perfect 30-minute express wellness routine after a hectic shopping or travel weekend..."),
            
            ("Top 5 Makeup Blunders to Avoid on Your Wedding Day", "Wedding",
             "Ensure you look timeless. Learn about the most common bridal makeup mistakes and how to avoid them.",
             "Bridal makeup mistakes can ruin photos: "
             "1. Using foundation with SPF (causes white flashback in flash photography); "
             "2. Not matching face makeup with neck and hands; 3. Over-contouring; "
             "4. Trying new skin care products 2 days before; 5. Using non-waterproof mascara. "
             "Always trust a certified makeup artist..."),
            
            ("Why You Should Switch to Ammonia-Free Hair Colors Today", "Hair Color",
             "Ammonia-free hair colors are gentler on scalp and hair. Discover why it is the healthier choice for grey coverage.",
             "Traditional hair dyes use ammonia to swell the hair cuticles, which causes damage, dry texture, and scalp itching. "
             "Ammonia-free colors use oil-delivery systems to deposit pigment gently, protecting the hair's natural moisture "
             "and leaving it looking shinier and smelling great. SalonX uses premium ammonia-free colors for all clients...")
        ]

        blog_images = [
            "https://images.unsplash.com/photo-1562322140-8baeececf3df?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1605497746444-ac9dbd324ce9?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1517832606299-7ae9b720a186?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1600334089648-b0d9d3028eb2?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1604654894610-df4906f2426d?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1562322140-8baeececf3df?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1621605815971-fbc98d665033?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1595476108010-b4d1f102b1b1?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1519415510236-718bdfcd89c9?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=500&q=80",
            "https://images.unsplash.com/photo-1605497746444-ac9dbd324ce9?auto=format&fit=crop&w=500&q=80"
        ]

        for idx, item in enumerate(blogs_data):
            SalonBlog.objects.create(
                title=item[0],
                slug=slugify(item[0]),
                short_description=item[2],
                description=item[3],
                image=blog_images[idx],
                status=True
            )

        self.stdout.write(f'- Seeded {SalonBlog.objects.count()} Blog Articles')

        # ----------------------------------------------------
        # 10. Seed Appointments (50)
        # ----------------------------------------------------
        appointment_messages = [
            "Please assign Aarav if possible.",
            "First time visit, excited!",
            "I have a wedding to attend in the evening, please be on time.",
            "Interested in pre-bridal package options.",
            "Need a scalp check before the spa.",
            "Please make sure tools are sanitized.",
            "Need a quick blow dry styling too.",
            "", "", "", "" # some empty messages
        ]

        genders = ['Male', 'Female', 'Unisex/Other']
        statuses = ['Pending', 'Confirmed', 'Completed', 'Cancelled']

        for i in range(50):
            # Select random customer
            cust = random.choice(customers)
            # Select random service & stylist
            srv = random.choice(all_services)
            sty = random.choice(stylists)
            
            # Date range: past 20 days to future 15 days
            days_offset = random.randint(-20, 15)
            appt_date = date.today() + timedelta(days=days_offset)
            
            # Time: between 10:00 AM and 7:00 PM
            hour = random.randint(10, 19)
            minute = random.choice([0, 15, 30, 45])
            appt_time = datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
            
            # Status: past dates should be Completed/Cancelled, future should be Pending/Confirmed
            if appt_date < date.today():
                status = random.choice(['Completed', 'Completed', 'Completed', 'Cancelled'])
            else:
                status = random.choice(['Pending', 'Confirmed', 'Confirmed'])
                
            SalonAppointment.objects.create(
                customer_name=cust.name,
                mobile=cust.mobile,
                email=cust.email,
                gender=random.choice(genders),
                service=srv,
                stylist=sty,
                appointment_date=appt_date,
                appointment_time=appt_time,
                message=random.choice(appointment_messages),
                status=status,
                created_at=timezone.now() - timedelta(days=random.randint(1, 10))
            )

        self.stdout.write(f'- Seeded {SalonAppointment.objects.count()} Appointments')
        self.stdout.write(self.style.SUCCESS('Successfully seeded SalonX database with premium demo data.'))
