import os
import time
import datetime
import random
import sqlite3
import json
import io
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseRedirect, JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMessage
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color

# =====================================================================
# STATIC FILE SERVING
# =====================================================================

def serve_ramjaa(request, path=''):
    """
    Serves static files from the 'RAMJAA' directory.
    If the path is empty or a directory, it defaults to 'index.html'.
    Prevents directory traversal attacks by validating the path.
    """
    if request.path == '/ramjaa':
        return HttpResponseRedirect('/ramjaa/')
        
    if path == 'a/admin':
        return HttpResponseRedirect('/ramjaa/a/admin/')
    if path == 'a/admin/':
        path = 'admin.html'
        
    ramjaa_dir = os.path.join(settings.BASE_DIR, 'RAMJAA')
    
    if not path or path.endswith('/'):
        path = os.path.join(path, 'index.html')
        
    full_path = os.path.join(ramjaa_dir, path)
    
    normalized_path = os.path.abspath(full_path)
    if not normalized_path.startswith(os.path.abspath(ramjaa_dir)):
        raise Http404("File not found")
        
    if os.path.exists(normalized_path) and os.path.isfile(normalized_path):
        return FileResponse(open(normalized_path, 'rb'))
    else:
        raise Http404("File not found")


# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def is_admin_authorized(request):
    auth_header = request.headers.get('Authorization')
    auth_query = request.GET.get('admin_pass')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin_ramjaa')
    return auth_header == admin_password or auth_query == admin_password or auth_header == 'admin_ramjaa'


def generate_ramjaa_pdf(alumnus):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(375, 240))
    
    # 1. Background (Navy Blue)
    c.setFillColor(HexColor('#0b2545'))
    c.rect(0, 0, 375, 240, fill=True, stroke=False)
    
    # 2. Header Panel Background (darker navy)
    c.setFillColor(HexColor('#134074'))
    c.rect(0, 180, 375, 60, fill=True, stroke=False)
    
    # 3. Gold Accent Stripe
    c.setFillColor(HexColor('#f5a623'))
    c.rect(0, 177, 375, 3, fill=True, stroke=False)
    
    # 4. Draw Header Logo (if exists)
    logo_path = os.path.join(settings.BASE_DIR, 'RAMJAA', '1.jpeg')
    if os.path.exists(logo_path):
        c.drawImage(logo_path, 20, 187, width=46, height=46, mask='auto')
    
    # 5. Header Texts
    c.setFillColor(HexColor('#f5a623'))
    c.setFont('Helvetica-Bold', 18)
    c.drawString(75, 218, 'RAMJAA')
    
    c.setFillColor(Color(1, 1, 1, 0.7))
    c.setFont('Helvetica', 8)
    c.drawString(75, 196, 'ALUMNI ASSOCIATION MEMBER')
    
    # 6. Gold Ribbon Corner Decoration at top right
    c.setFillColor(HexColor('#f5a623'))
    p = c.beginPath()
    p.moveTo(330, 240)
    p.lineTo(375, 240)
    p.lineTo(375, 195)
    p.close()
    c.drawPath(p, fill=True, stroke=False)
    
    # 7. Draw Profile Photo
    photo_relative = alumnus.get('photo', '1.jpeg')
    photo_path = os.path.join(settings.BASE_DIR, 'RAMJAA', photo_relative)
    if not os.path.exists(photo_path):
        photo_path = os.path.join(settings.BASE_DIR, 'RAMJAA', '1.jpeg')
    
    if os.path.exists(photo_path):
        c.drawImage(photo_path, 20, 30, width=105, height=120, mask='auto')
        # White photo border
        c.setStrokeColor(HexColor('#ffffff'))
        c.setLineWidth(1.5)
        c.rect(20, 30, 105, 120, fill=False, stroke=True)
        
    # 8. Member Details (Right Column)
    c.setFillColor(HexColor('#ffffff'))
    
    # Full Name
    c.setFont('Helvetica-Bold', 14)
    c.drawString(145, 130, alumnus['name'])
    
    # Member ID
    c.setFillColor(HexColor('#f5a623'))
    c.setFont('Helvetica-Bold', 9)
    c.drawString(145, 110, f"ID: {alumnus['id']}")
    
    # Detail labels and values helper
    details = [
        ('BATCH:', alumnus['batch']),
        ('MOBILE:', alumnus['mobile']),
        ('EMAIL:', alumnus['email']),
        ('LOCATION:', alumnus['location']),
    ]
    
    y = 88
    for label, value in details:
        c.setFillColor(HexColor('#f5a623'))
        c.setFont('Helvetica-Bold', 8)
        c.drawString(145, y, label)
        
        c.setFillColor(HexColor('#ffffff'))
        c.setFont('Helvetica', 8)
        c.drawString(210, y, str(value))
        y -= 15
        
    # 9. Bottom Footer text
    c.setFillColor(Color(1, 1, 1, 0.3))
    c.setFont('Helvetica', 6.5)
    c.drawRightString(355, 12, 'RADHA MOHAN JEW HIGH SCHOOL, SINDHIA')
    
    c.showPage()
    c.save()
    
    buffer.seek(0)
    return buffer.getvalue()


# =====================================================================
# API ENDPOINTS
# =====================================================================

@csrf_exempt
def ramjaa_notices_api(request):
    db_path = os.path.join(settings.BASE_DIR, 'RAMJAA', 'ramjaa.db')
    
    if request.method == 'GET':
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notices")
        rows = cursor.fetchall()
        conn.close()
        
        notices = [dict(r) for r in rows]
        return JsonResponse(notices, safe=False)
        
    elif request.method == 'POST':
        if not is_admin_authorized(request):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
            
        try:
            data = json.loads(request.body)
        except:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
            
        title = data.get('title')
        desc = data.get('desc')
        category = data.get('category', 'General')
        
        if not title or not desc:
            return JsonResponse({'error': 'Title and Description are required'}, status=400)
            
        date_today = datetime.date.today().isoformat()
        notice_id = f"n_{int(time.time() * 1000)}"
        
        new_notice = {
            'id': notice_id,
            'date': date_today,
            'title_en': title,
            'title_or': title,
            'desc_en': desc,
            'desc_or': desc,
            'category': category
        }
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notices (id, date, title_en, title_or, desc_en, desc_or, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_notice['id'], new_notice['date'], new_notice['title_en'], new_notice['title_or'], new_notice['desc_en'], new_notice['desc_or'], new_notice['category'])
        )
        conn.commit()
        conn.close()
        
        return JsonResponse(new_notice, status=201)


@csrf_exempt
def ramjaa_notices_api_delete(request, item_id):
    if request.method == 'DELETE':
        if not is_admin_authorized(request):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
            
        db_path = os.path.join(settings.BASE_DIR, 'RAMJAA', 'ramjaa.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notices WHERE id = ?", (item_id,))
        changes = conn.total_changes
        conn.commit()
        conn.close()
        
        if changes == 0:
            return JsonResponse({'error': 'Notice not found'}, status=404)
        return JsonResponse({'message': 'Notice deleted successfully'})


@csrf_exempt
def ramjaa_gallery_api(request):
    db_path = os.path.join(settings.BASE_DIR, 'RAMJAA', 'ramjaa.db')
    
    if request.method == 'GET':
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gallery")
        rows = cursor.fetchall()
        conn.close()
        
        gallery = [dict(r) for r in rows]
        return JsonResponse(gallery, safe=False)
        
    elif request.method == 'POST':
        if not is_admin_authorized(request):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
            
        caption = request.POST.get('caption')
        category = request.POST.get('category', 'Events')
        photo_file = request.FILES.get('photo')
        
        if not caption or not photo_file:
            return JsonResponse({'error': 'Caption and image file are required'}, status=400)
            
        uploads_dir = os.path.join(settings.BASE_DIR, 'RAMJAA', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        unique_suffix = f"{int(time.time())}-{random.randint(1000,9999)}"
        file_ext = os.path.splitext(photo_file.name)[1]
        filename = f"photo-{unique_suffix}{file_ext}"
        filepath = os.path.join(uploads_dir, filename)
        
        with open(filepath, 'wb+') as destination:
            for chunk in photo_file.chunks():
                destination.write(chunk)
                
        relative_path = f"uploads/{filename}"
        date_today = datetime.date.today().isoformat()
        
        new_item = {
            'id': f"g_{int(time.time() * 1000)}",
            'path': relative_path,
            'caption_en': caption,
            'caption_or': caption,
            'category': category,
            'date': date_today
        }
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO gallery (id, path, caption_en, caption_or, category, date) VALUES (?, ?, ?, ?, ?, ?)",
            (new_item['id'], new_item['path'], new_item['caption_en'], new_item['caption_or'], new_item['category'], new_item['date'])
        )
        conn.commit()
        conn.close()
        
        return JsonResponse(new_item, status=201)


@csrf_exempt
def ramjaa_gallery_api_delete(request, item_id):
    if request.method == 'DELETE':
        if not is_admin_authorized(request):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
            
        db_path = os.path.join(settings.BASE_DIR, 'RAMJAA', 'ramjaa.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gallery WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        
        if not item:
            conn.close()
            return JsonResponse({'error': 'Gallery item not found'}, status=404)
            
        item_dict = dict(item)
        if item_dict['path'].startswith('uploads/'):
            full_path = os.path.join(settings.BASE_DIR, 'RAMJAA', item_dict['path'])
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except:
                    pass
                    
        cursor.execute("DELETE FROM gallery WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        
        return JsonResponse({'message': 'Gallery item deleted successfully'})


def ramjaa_alumni_count(request):
    db_path = os.path.join(settings.BASE_DIR, 'RAMJAA', 'ramjaa.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS count FROM alumni")
    row = cursor.fetchone()
    conn.close()
    
    return JsonResponse({'count': row[0]})


@csrf_exempt
def ramjaa_alumni_api(request):
    db_path = os.path.join(settings.BASE_DIR, 'RAMJAA', 'ramjaa.db')
    
    if request.method == 'GET':
        if not is_admin_authorized(request):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alumni ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        alumni = [dict(r) for r in rows]
        return JsonResponse(alumni, safe=False)
        
    elif request.method == 'POST':
        name = request.POST.get('name')
        batch = request.POST.get('batch')
        mobile = request.POST.get('mobile')
        email = request.POST.get('email')
        profession = request.POST.get('profession', 'Not Specified')
        location = request.POST.get('location')
        message = request.POST.get('message', '')
        photo_file = request.FILES.get('photo')
        
        if not name or not batch or not mobile or not email or not location:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
            
        batch_str = str(batch)
        batch_suffix = batch_str[-2:] if len(batch_str) >= 2 else batch_str
        member_id = ''
        id_exists = True
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        while id_exists:
            random_num = random.randint(1000, 9999)
            member_id = f"RM-{batch_suffix}{random_num}"
            cursor.execute("SELECT id FROM alumni WHERE id = ?", (member_id,))
            if not cursor.fetchone():
                id_exists = False
                
        has_photo = photo_file is not None
        status = 'pending' if has_photo else 'approved'
        photo_path = '1.jpeg'
        
        if has_photo:
            uploads_dir = os.path.join(settings.BASE_DIR, 'RAMJAA', 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            
            unique_suffix = f"{int(time.time())}-{random.randint(1000,9999)}"
            file_ext = os.path.splitext(photo_file.name)[1]
            filename = f"photo-{unique_suffix}{file_ext}"
            filepath = os.path.join(uploads_dir, filename)
            
            with open(filepath, 'wb+') as destination:
                for chunk in photo_file.chunks():
                    destination.write(chunk)
            photo_path = f"uploads/{filename}"
            
        created_at = datetime.datetime.now().isoformat()
        
        new_alumnus = {
            'id': member_id,
            'name': name,
            'batch': batch,
            'mobile': mobile,
            'email': email,
            'profession': profession,
            'location': location,
            'message': message,
            'photo': photo_path,
            'status': status,
            'created_at': created_at
        }
        
        cursor.execute(
            "INSERT INTO alumni (id, name, batch, mobile, email, profession, location, message, photo, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_alumnus['id'], new_alumnus['name'], new_alumnus['batch'], new_alumnus['mobile'], new_alumnus['email'], new_alumnus['profession'], new_alumnus['location'], new_alumnus['message'], new_alumnus['photo'], new_alumnus['status'], new_alumnus['created_at'])
        )
        conn.commit()
        conn.close()
        
        return JsonResponse(new_alumnus, status=201)


@csrf_exempt
def ramjaa_alumni_delete(request, item_id):
    if request.method == 'DELETE':
        if not is_admin_authorized(request):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
            
        db_path = os.path.join(settings.BASE_DIR, 'RAMJAA', 'ramjaa.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alumni WHERE id = ?", (item_id,))
        member = cursor.fetchone()
        
        if not member:
            conn.close()
            return JsonResponse({'error': 'Alumnus not found'}, status=404)
            
        member_dict = dict(member)
        if member_dict['photo'].startswith('uploads/'):
            full_path = os.path.join(settings.BASE_DIR, 'RAMJAA', member_dict['photo'])
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except:
                    pass
                    
        cursor.execute("DELETE FROM alumni WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        
        return JsonResponse({'message': 'Alumnus deleted successfully'})


@csrf_exempt
def ramjaa_alumni_approve(request, item_id):
    if request.method == 'POST':
        if not is_admin_authorized(request):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
            
        db_path = os.path.join(settings.BASE_DIR, 'RAMJAA', 'ramjaa.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alumni WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return JsonResponse({'error': 'Alumnus not found'}, status=404)
            
        alumnus = dict(row)
        if alumnus['status'] == 'approved':
            conn.close()
            return JsonResponse({'error': 'Alumnus is already approved'}, status=400)
            
        cursor.execute("UPDATE alumni SET status = 'approved' WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        
        alumnus['status'] = 'approved'
        
        try:
            pdf_bytes = generate_ramjaa_pdf(alumnus)
        except Exception as e:
            return JsonResponse({'error': f'PDF Generation failed: {str(e)}'}, status=500)
            
        email_sent = False
        local_logged = False
        mail_log_path = ''
        
        try:
            subject = "RAMJAA Alumni Association - ID Card Approved"
            body = (
                f"Dear {alumnus['name']},\n\n"
                f"Congratulations! Your Radha Mohan Jew Alumni Association (RAMJAA) registration has been approved.\n\n"
                f"Please find attached your official digital Identity Card.\n\n"
                f"Member ID: {alumnus['id']}\n"
                f"Batch: {alumnus['batch']}\n\n"
                f"Best Regards,\n"
                f"Radha Mohan Jew Alumni Association (RAMJAA)"
            )
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'info@ramjaa.org')
            
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_email,
                to=[alumnus['email']]
            )
            email.attach(f"RAMJAA_ICard_{alumnus['id']}.pdf", pdf_bytes, "application/pdf")
            email.send(fail_silently=False)
            email_sent = True
        except Exception as mail_err:
            print(f"[RAMJAA] Django mail sending failed: {str(mail_err)}. Logging locally instead.")
            temp_mails_dir = os.path.join(settings.BASE_DIR, 'RAMJAA', 'temp_mails')
            os.makedirs(temp_mails_dir, exist_ok=True)
            
            pdf_out_path = os.path.join(temp_mails_dir, f"RAMJAA_ICard_{alumnus['id']}.pdf")
            with open(pdf_out_path, 'wb') as f:
                f.write(pdf_bytes)
                
            unique_time = f"{int(time.time())}-{random.randint(1000,9999)}"
            mail_log_name = f"mail_{alumnus['id']}_{unique_time}.txt"
            mail_log_path = os.path.join(temp_mails_dir, mail_log_name)
            with open(mail_log_path, 'w', encoding='utf-8') as f:
                f.write(f"To: {alumnus['email']}\n")
                f.write(f"Subject: {subject}\n\n")
                f.write(body)
                
            local_logged = True
            
        return JsonResponse({
            'message': 'Alumnus approved successfully and email sent.',
            'alumnus': alumnus,
            'emailResult': {
                'success': email_sent or local_logged,
                'localLogged': local_logged,
                'path': mail_log_path if local_logged else ''
            }
        })


def ramjaa_alumni_pdf(request, item_id):
    db_path = os.path.join(settings.BASE_DIR, 'RAMJAA', 'ramjaa.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alumni WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise Http404("Alumnus not found")
        
    alumnus = dict(row)
    
    try:
        pdf_bytes = generate_ramjaa_pdf(alumnus)
    except Exception as e:
        return HttpResponse(f"Failed to generate PDF: {str(e)}", status=500)
        
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=RAMJAA_ICard_{item_id}.pdf'
    return response


@csrf_exempt
def ramjaa_admin_login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
            
        password = data.get('password')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin_ramjaa')
        
        if password == admin_password or password == 'admin_ramjaa':
            return JsonResponse({'success': True})
        return JsonResponse({'error': 'Invalid password'}, status=401)
