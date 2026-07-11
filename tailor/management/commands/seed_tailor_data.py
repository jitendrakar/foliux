import random
from datetime import datetime, date, timedelta, time
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from tailor.models import (
    TailorUser, TailorService, TailorMeasurement, TailorOrder, 
    TailorAppointment, TailorGallery, TailorReview, TailorOffer, 
    TailorPayment, TailorSetting
)

class Command(BaseCommand):
    help = 'Seeds the tailor database with realistic Indian boutique demo data.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding Tailor database...')

        # ----------------------------------------------------
        # 1. Clear Existing Data
        # ----------------------------------------------------
        TailorUser.objects.all().delete()
        TailorService.objects.all().delete()
        TailorMeasurement.objects.all().delete()
        TailorOrder.objects.all().delete()
        TailorAppointment.objects.all().delete()
        TailorGallery.objects.all().delete()
        TailorReview.objects.all().delete()
        TailorOffer.objects.all().delete()
        TailorPayment.objects.all().delete()
        TailorSetting.objects.all().delete()

        # ----------------------------------------------------
        # 2. Seed Settings (Address, Phone, Email specified by user)
        # ----------------------------------------------------
        setting = TailorSetting.objects.create(
            brand_name="TailorX – Premium Custom Boutique",
            address="N-15, Private Colony, Sriniwaspuri, New Delhi, Delhi 110065",
            phone="9871808718",
            email="jitendra.kar@gmail.com",
            whatsapp="9871808718",
            google_map='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3504.2690906263595!2d77.2559599!3d28.5616802!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x390d1da0e6db69b3%3A0xe5426177b949989f!2sSriniwaspuri%2C%20New%20Delhi%2C%20Delhi!5e0!3m2!1sen!2sin!4v1680000000000!5m2!1sen!2sin'
        )
        self.stdout.write('- Seeded settings')

        # ----------------------------------------------------
        # 3. Seed Admin and Customers
        # ----------------------------------------------------
        admin_user = TailorUser(
            name="Jitendra Kar",
            mobile="9871808718",
            email="jitendra.kar@gmail.com",
            address="N-15, Private Colony, Sriniwaspuri, New Delhi, Delhi 110065",
            gender="Male",
            role="admin"
        )
        admin_user.set_password("tailorx123")
        admin_user.save()

        first_names_male = ["Aarav", "Kabir", "Vivaan", "Aditya", "Arjun", "Ishan", "Sai", "Reyansh", "Krishna", "Atharva", "Shaurya", "Rohit", "Rahul", "Deepak", "Sanjay", "Vijay", "Ramesh", "Suresh", "Amit", "Vikram", "Abhishek", "Kunal", "Rohan", "Aniket", "Mayank", "Nikhil", "Pranav", "Rajat", "Sandeep", "Tushar"]
        first_names_female = ["Aadya", "Diya", "Saanvi", "Anya", "Ananya", "Aadhya", "Aaradhya", "Pihu", "Ira", "Sana", "Riya", "Anjali", "Priyanka", "Divya", "Pooja", "Neha", "Sneha", "Preeti", "Kavita", "Jyoti", "Komal", "Meera", "Nisha", "Payal", "Ritu", "Sakshi", "Tanvi", "Urvi", "Vaishnali", "Yashasvi"]
        last_names = ["Sharma", "Verma", "Patel", "Mehta", "Nair", "Joshi", "Rao", "Reddy", "Sen", "Chatterjee", "Gupta", "Singh", "Kumar", "Mishra", "Trivedi", "Shah", "Iyer", "Pillai", "Choudhury", "Das", "Bose", "Kulkarni", "Deshmukh", "Bhat", "Menon", "Dubey", "Pandey", "Saxena", "Soni", "Kapoor"]

        customers = []
        for i in range(100):
            gender = random.choice(['Male', 'Female'])
            first_name = random.choice(first_names_male) if gender == 'Male' else random.choice(first_names_female)
            last_name = random.choice(last_names)
            full_name = f"{first_name} {last_name}"
            
            email = f"{first_name.lower()}.{last_name.lower()}{i+1}@tailorx.com"
            mobile = f"{random.choice([9, 8, 7, 6])}{random.randint(100000000, 999999999)}"
            
            cust = TailorUser(
                name=full_name,
                mobile=mobile,
                email=email,
                address=f"Flat {random.randint(101, 999)}, Block {random.choice(['A', 'B', 'C', 'D'])}, Sriniwaspuri, New Delhi - 110065",
                gender=gender,
                role="customer"
            )
            cust.set_password("customer123")
            cust.save()
            customers.append(cust)

        self.stdout.write(f'- Seeded 1 Admin and {len(customers)} Customers')

        # ----------------------------------------------------
        # 4. Seed Services (20+)
        # ----------------------------------------------------
        services_data = {
            "Men's Tailoring": [
                {"name": "Premium Shirt Stitching", "price": 499, "icon": "fa-shirt", "desc": "Custom collared cuffs and tailored slim-fit stitching."},
                {"name": "Formal Trouser Stitching", "price": 599, "icon": "fa-scissors", "desc": "Flat front or pleated regular fitting trouser stitching."},
                {"name": "Bespoke 2-Piece Suit", "price": 5499, "icon": "fa-user-tie", "desc": "Custom blazer with inner lining and matching formal pants."},
                {"name": "Casual Blazer", "price": 2999, "icon": "fa-user-tie", "desc": "Unstructured linen/cotton premium blazers."},
                {"name": "Designer Sherwani", "price": 7999, "icon": "fa-scissors", "desc": "Grand wedding groom sherwani with intricate collar details."},
                {"name": "Traditional Kurta", "price": 799, "icon": "fa-scissors", "desc": "Regular fit traditional kurta with front buttons pocket."},
                {"name": "Overcoat / Trenchcoat", "price": 3999, "icon": "fa-scissors", "desc": "Warm winter trenchcoat tailor-stitched styling."}
            ],
            "Women's Tailoring": [
                {"name": "Salwar Kameez Suit", "price": 999, "icon": "fa-scissors", "desc": "Custom design kameez with lining and matching salwar/palazzo."},
                {"name": "Designer Blouse (Padded)", "price": 799, "icon": "fa-scissors", "desc": "Padded blouse styling with back string designs and deep cuts."},
                {"name": "Bridal Lehenga Stitching", "price": 8999, "icon": "fa-gem", "desc": "Custom heavy flared lehenga with dupatta setting and latkans."},
                {"name": "Premium Evening Gown", "price": 3499, "icon": "fa-scissors", "desc": "Ballroom or straight-cut luxury party gowns."},
                {"name": "Designer Dress", "price": 1499, "icon": "fa-scissors", "desc": "Custom stitch frock or midi dresses."},
                {"name": "Anarkali Kurti", "price": 1199, "icon": "fa-scissors", "desc": "Heavy flared anarkali matching churidar set."},
                {"name": "Saree Fall & Pico Work", "price": 199, "icon": "fa-scissors", "desc": "Machine fall stitching and premium thread border pico styling."}
            ],
            "Other Services": [
                {"name": "Premium Groom Wear Styling", "price": 11999, "icon": "fa-chess-king", "desc": "Wedding sherwani, matching turban, stole, and juti coordination stitching."},
                {"name": "Bridal Wear Styling Set", "price": 14999, "icon": "fa-gem", "desc": "Bespoke bridal lehenga set, matching veil draping, and blouse sets."},
                {"name": "Boutique Alterations", "price": 299, "icon": "fa-wrench", "desc": "Fit corrections, sleeve shortening, waist expansions, shoulder corrections."},
                {"name": "School / Office Uniform Set", "price": 999, "icon": "fa-school", "desc": "Standard uniform stitching (shirt + trouser or skirt + blazer)."},
                {"name": "Custom Clothing Designing", "price": 4999, "icon": "fa-pencil-ruler", "desc": "Tailor designing based on model sketches or sample digital mockups."}
            ]
        }

        all_services = []
        for cat_name, srvs in services_data.items():
            for item in srvs:
                srv = TailorService.objects.create(
                    category=cat_name,
                    service_name=item["name"],
                    price=item["price"],
                    icon=item["icon"],
                    description=item["desc"],
                    status=True
                )
                all_services.append(srv)

        self.stdout.write(f'- Seeded {len(all_services)} Services')

        # ----------------------------------------------------
        # 5. Seed Sizing Measurements (50 files)
        # ----------------------------------------------------
        measurements = []
        for i in range(50):
            cust = customers[i]
            meas = TailorMeasurement.objects.create(
                customer=cust,
                height=f"{random.randint(155, 185)} cm",
                chest=f"{random.randint(32, 46)} in",
                waist=f"{random.randint(28, 42)} in",
                hip=f"{random.randint(34, 48)} in",
                shoulder=f"{random.randint(14, 20)} in",
                sleeve=f"{random.randint(18, 26)} in",
                neck=f"{random.randint(13, 18)} in",
                inseam=f"{random.randint(28, 36)} in",
                notes=random.choice(["Slim fit preferred.", "Relaxed fit on shoulders.", "Keep sleeves slightly loose.", "Add extra inner margins.", "Comfort fitting requested."])
            )
            measurements.append(meas)

        self.stdout.write(f'- Seeded {len(measurements)} Measurement Cards')

        # ----------------------------------------------------
        # 6. Seed Orders & Payments (50 orders)
        # ----------------------------------------------------
        fabrics = ["Premium Cotton", "Linen", "Pure Silk", "Banarasi Brocade", "Italian Wool Blend", "Synthetic Polyester", "Velvet", "Chiffon", "Georgette"]
        statuses = ["New", "Cutting", "Stitching", "Trial", "Ready", "Delivered", "Cancelled"]
        pay_methods = ["Cash", "Card", "UPI", "Bank Transfer"]

        orders = []
        for i in range(50):
            # Select customer (using first 50 who have measurements)
            cust = customers[i]
            meas = measurements[i]
            srv = random.choice(all_services)
            
            # Dates
            order_date = date.today() - timedelta(days=random.randint(1, 30))
            trial_date = order_date + timedelta(days=7)
            delivery_date = order_date + timedelta(days=12)
            
            status = random.choice(statuses)
            amount = srv.price
            
            # Decide advance/balance based on status
            if status in ["Ready", "Delivered"]:
                advance = amount
                balance = 0.00
            else:
                advance = round(amount * random.choice([0.3, 0.5, 0.7]), 2)
                balance = amount - advance
                
            # Unique order number
            order_number = f"TLR-{order_date.strftime('%y%m%d')}{i+1000}"
            
            order = TailorOrder.objects.create(
                order_number=order_number,
                customer=cust,
                category=srv.category,
                service=srv,
                fabric=random.choice(fabrics),
                measurement=meas,
                trial_date=trial_date,
                delivery_date=delivery_date,
                status=status,
                amount=amount,
                advance=advance,
                balance=balance,
                created_at=datetime.combine(order_date, time(10, 0))
            )
            orders.append(order)
            
            # Seed Payments
            if advance > 0:
                TailorPayment.objects.create(
                    order=order,
                    amount_paid=advance,
                    payment_date=order.created_at,
                    payment_method=random.choice(pay_methods),
                    payment_type='Advance'
                )
                
            if status in ["Ready", "Delivered"] and balance == 0:
                # Log balance payment too
                TailorPayment.objects.create(
                    order=order,
                    amount_paid=amount - advance,
                    payment_date=datetime.combine(delivery_date, time(17, 30)),
                    payment_method=random.choice(pay_methods),
                    payment_type='Balance'
                )

        self.stdout.write(f'- Seeded {len(orders)} Orders and Payment histories')

        # ----------------------------------------------------
        # 7. Seed Appointments (25 slots)
        # ----------------------------------------------------
        appt_messages = [
            "Bringing my own silk fabric.",
            "Need uniform trial completed quick.",
            "Home visit sizing requested.",
            "Please call before coming.",
            "Discussing wedding lehenga styling.",
            "Bespoke suite trials."
        ]
        genders = ['Male', 'Female', 'Other']

        for i in range(25):
            cust = random.choice(customers)
            srv = random.choice(all_services)
            days_offset = random.randint(-10, 15)
            appt_date = date.today() + timedelta(days=days_offset)
            
            hour = random.randint(10, 19)
            minute = random.choice([0, 30])
            appt_time = datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
            
            status = 'Pending'
            if appt_date < date.today():
                status = random.choice(['Completed', 'Cancelled'])
            else:
                status = random.choice(['Pending', 'Confirmed'])
                
            TailorAppointment.objects.create(
                customer_name=cust.name,
                mobile=cust.mobile,
                email=cust.email,
                gender=random.choice(genders),
                service=srv,
                appointment_date=appt_date,
                appointment_time=appt_time,
                home_visit=random.choice([True, False, False]),
                message=random.choice(appt_messages),
                status=status
            )

        self.stdout.write(f'- Seeded {TailorAppointment.objects.count()} Appointments')

        # ----------------------------------------------------
        # 8. Seed Gallery (30 items)
        # ----------------------------------------------------
        gallery_items = [
            ("Classic Royal Sherwani", "Bridal", "https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?auto=format&fit=crop&w=500&q=80"),
            ("Navy Double-Breasted Suit", "Men", "https://images.unsplash.com/photo-1593032465175-481ac7f401a0?auto=format&fit=crop&w=500&q=80"),
            ("Pastel Floral Lehenga", "Bridal", "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?auto=format&fit=crop&w=500&q=80"),
            ("Embroidered Silk Blouse", "Boutique", "https://images.unsplash.com/photo-1610992015762-4113b700191a?auto=format&fit=crop&w=500&q=80"),
            ("Corporate Executive Uniforms", "Uniform", "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=500&q=80"),
            ("Linen Summer Suit styling", "Men", "https://images.unsplash.com/photo-1594909122845-11baa439b7bf?auto=format&fit=crop&w=500&q=80"),
            ("Red Georgette Gown Design", "Women", "https://images.unsplash.com/photo-1566174053879-31528523f8ae?auto=format&fit=crop&w=500&q=80"),
            ("Zardozi Bridal Sherwani Work", "Bridal", "https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?auto=format&fit=crop&w=500&q=80"),
            ("Classic Kurta Salwar Set", "Men", "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?auto=format&fit=crop&w=500&q=80"),
            ("School Pleated Uniform Skirt Set", "Uniform", "https://images.unsplash.com/photo-1546410531-bb4caa6b424d?auto=format&fit=crop&w=500&q=80"),
            ("Banarasi Silk Dupatta Set", "Boutique", "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=500&q=80"),
            ("Velvet Nehru Jacket Look", "Latest Designs", "https://images.unsplash.com/photo-1593032465175-481ac7f401a0?auto=format&fit=crop&w=500&q=80"),
            ("Flared Chikankari Anarkali Suit", "Women", "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?auto=format&fit=crop&w=500&q=80"),
            ("Premium Tuxedo Collar Blazer", "Latest Designs", "https://images.unsplash.com/photo-1594909122845-11baa439b7bf?auto=format&fit=crop&w=500&q=80"),
            ("Khaki Police Uniform styling", "Uniform", "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=500&q=80"),
            ("Lace Border Party Gowns", "Women", "https://images.unsplash.com/photo-1566174053879-31528523f8ae?auto=format&fit=crop&w=500&q=80"),
            ("Brocade Groomsmen Turban Work", "Bridal", "https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?auto=format&fit=crop&w=500&q=80"),
            ("Premium Corduroy Trouser Styling", "Men", "https://images.unsplash.com/photo-1594909122845-11baa439b7bf?auto=format&fit=crop&w=500&q=80"),
            ("Organza Floral Kurti Styling", "Latest Designs", "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=500&q=80"),
            ("Heavy Mirror-Work Lehenga", "Bridal", "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?auto=format&fit=crop&w=500&q=80"),
            ("Grey Woolen Blazer Stitching", "Latest Designs", "https://images.unsplash.com/photo-1593032465175-481ac7f401a0?auto=format&fit=crop&w=500&q=80"),
            ("Custom A-Line Frock Dress", "Women", "https://images.unsplash.com/photo-1566174053879-31528523f8ae?auto=format&fit=crop&w=500&q=80"),
            ("Designer Cotton Palazzo Set", "Boutique", "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=500&q=80"),
            ("Front Slit Indo-Western Gown", "Latest Designs", "https://images.unsplash.com/photo-1566174053879-31528523f8ae?auto=format&fit=crop&w=500&q=80"),
            ("White Linen Mandarin Shirt", "Men", "https://images.unsplash.com/photo-1593032465175-481ac7f401a0?auto=format&fit=crop&w=500&q=80"),
            ("High Neck Bridal Blouse Pattern", "Bridal", "https://images.unsplash.com/photo-1610992015762-4113b700191a?auto=format&fit=crop&w=500&q=80"),
            ("Trenchcoat Linen Lining work", "Boutique", "https://images.unsplash.com/photo-1594909122845-11baa439b7bf?auto=format&fit=crop&w=500&q=80"),
            ("Security Guard Peak Caps & Shirts", "Uniform", "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=500&q=80"),
            ("Handloom Cotton Kurta pajama", "Boutique", "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?auto=format&fit=crop&w=500&q=80"),
            ("Checked Tweed Jacket Styling", "Latest Designs", "https://images.unsplash.com/photo-1594909122845-11baa439b7bf?auto=format&fit=crop&w=500&q=80")
        ]

        for item in gallery_items:
            TailorGallery.objects.create(
                title=item[0],
                category=item[1],
                image=item[2],
                status=True
            )

        self.stdout.write(f'- Seeded {TailorGallery.objects.count()} Gallery Images')

        # ----------------------------------------------------
        # 9. Seed Reviews (15 reviews)
        # ----------------------------------------------------
        reviews_data = [
            ("Siddharth Roy", 5, "Stitched a custom wedding sherwani here. The fit was absolutely perfect! The details and fabric lining match international boutique standards. Thanks to Jitendra for the excellent coordination."),
            ("Aditi Sen", 5, "Loved their designer blouses! The padding was perfect and got exactly the back cut design I requested. Very reliable boutique in Delhi."),
            ("Rohan Sharma", 5, "Excellent bespoke suits. The shoulder cuts and collar lay beautifully. Extremely professional alterations service too."),
            ("Meera Nair", 5, "I had my bridal lehenga flare adjusted and matching blouse stitched here. Simply gorgeous! They delivered it 2 days before promised."),
            ("Karan Johar", 4, "Stitched 3 formal shirts. Excellent collar stiffness and cuff stitching. Only issue was a slight delay in trial date."),
            ("Priya Patel", 5, "Highly recommend their salwar palazzo sets. Very comfortable fit. Friendly tailors who understand client styling requests clearly."),
            ("Deepak Gupta", 5, "Great experience with uniform stitching. Quick turnaround time and consistent stitching across 10 uniform sets."),
            ("Sneha Iyer", 5, "Absolutely beautiful gown custom design! The fabric falls perfectly and got so many compliments at the party."),
            ("Varun Dhawan", 5, "The best Nehru jacket stitching in South Delhi. Premium velvet fabric was managed beautifully. Highly recommended!"),
            ("Kriti Sanon", 5, "Very neat fall and pico work. Quick 1-day express delivery. The pricing is very reasonable too."),
            ("Sanjay Dutt", 4, "Had formal trousers stitched. Fit around waist is perfect. Staff is polite and helpful."),
            ("Shraddha Kapoor", 5, "Loved the boutique Anarkali dress. The hand-crafted border looks very premium. Will definitely visit again."),
            ("Ranveer Singh", 5, "Outstanding custom sherwani. The collar embroidery work is top notch. They make you feel like royalty during trials."),
            ("Anushka Sharma", 5, "Clean finishing, perfect measurements. My bridal gown was styled beautifully. Excellent boutique experience!"),
            ("Rahul Gandhi", 5, "Got custom kurtas stitched. Very comfortable linen fabric fit. Quick alterations on cuffs. Superb service.")
        ]

        for item in reviews_data:
            TailorReview.objects.create(
                customer_name=item[0],
                rating=item[1],
                review=item[2],
                status=True  # Approved by default
            )

        self.stdout.write(f'- Seeded {TailorReview.objects.count()} Approved Reviews')

        # ----------------------------------------------------
        # 10. Seed Offers (10 active)
        # ----------------------------------------------------
        offers_data = [
            ("Festive Sparkle Stitching", "FESTIVE20", "Save on your wedding lehengas and groom sherwani orders.", "20% OFF", 0, 45),
            ("New User Welcome Deal", "TAILOR100", "Get flat discount on your very first shirt or trouser stitching order.", "Flat ₹100 Off", 0, 90),
            ("Midweek Style Privilege", "MIDWEEK15", "Book stitching appointments on Tuesdays/Wednesdays and get discounts.", "15% OFF", 1, 30),
            ("Bridal Grand Combo Deal", "BRIDAL5000", "Massive savings on complete pre-bridal and bridal wear combo bookings.", "Flat ₹5,000 Off", 2, 60),
            ("Bulk Uniform Discount", "UNIFORM10", "Save on orders of 10 sets of school or office uniforms.", "Flat 10% OFF", 0, 180),
            ("Monsoon Alterations Deal", "ALTERFIT", "Get discount on boutique alterations of 3 or more clothing items.", "Flat 15% OFF", 3, 20),
            ("Weekend Premium Style", "WEEKEND10", "Unwind and book bespoke suit orders on weekends for exclusive savings.", "10% OFF", 1, 10),
            ("Diwali Sherwani Promo", "DIWALI3000", "Get flat cash discount on premium groom wear sherwani packages.", "Flat ₹3,000 Off", 10, 40),
            ("Corporate Client Deal", "CORPSTYLE", "Exclusive corporate club member privileges on formal wear stitching.", "Flat 12% OFF", 0, 365),
            ("Groom Makeover Styling", "GROOM20", "Special tailoring discounts for grooms and groomsmen suit sets.", "20% OFF", 2, 50)
        ]

        for idx, item in enumerate(offers_data):
            start = date.today() - timedelta(days=item[4])
            end = date.today() + timedelta(days=item[5])
            TailorOffer.objects.create(
                title=item[0],
                code=item[1],
                description=item[2],
                discount=item[3],
                start_date=start,
                end_date=end,
                status=True
            )

        self.stdout.write(f'- Seeded {TailorOffer.objects.count()} Discount Offers')
        self.stdout.write(self.style.SUCCESS('Successfully seeded TailorX database with premium boutique demo data.'))
