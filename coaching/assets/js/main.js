/**
 * Global JavaScript Functionality
 * Success Academy Coaching Institute
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Lightbox Gallery Integration
    const galleryPlaceholder = document.getElementById('galleryGrid');
    if (galleryPlaceholder) {
        // Event delegation to capture clicks on dynamic gallery cards
        galleryPlaceholder.addEventListener('click', function (e) {
            const card = e.target.closest('.gallery-item-card');
            if (card) {
                const imgSrc = card.getAttribute('data-img');
                const title = card.getAttribute('data-title');
                
                const lightboxModal = document.getElementById('lightboxModal');
                const lightboxImg = document.getElementById('lightboxImg');
                const lightboxCaption = document.getElementById('lightboxCaption');
                
                if (imgSrc && lightboxModal) {
                    lightboxImg.src = imgSrc;
                    lightboxCaption.textContent = title || '';
                    
                    const modal = new bootstrap.Modal(lightboxModal);
                    modal.show();
                }
            }
        });
    }

    // 2. Category Filter for Gallery Page
    const filterButtons = document.querySelectorAll('.gallery-filter-btn');
    if (filterButtons.length > 0) {
        filterButtons.forEach(button => {
            button.addEventListener('click', function () {
                filterButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');

                const filterValue = this.getAttribute('data-filter');
                const filterItems = document.querySelectorAll('.gallery-item-wrapper');

                filterItems.forEach(item => {
                    if (filterValue === 'all' || item.getAttribute('data-category') === filterValue) {
                        item.style.display = 'block';
                    } else {
                        item.style.display = 'none';
                    }
                });
            });
        });
    }

    // 3. AJAX Form - Contact Form Submission (Mocked with LocalStorage)
    const contactForm = document.getElementById('contactForm');
    const contactAlert = document.getElementById('contactAlert');

    if (contactForm) {
        contactForm.addEventListener('submit', function (e) {
            e.preventDefault();
            
            const submitBtn = contactForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Sending...';
            
            const name = document.getElementById('c_name').value;
            const email = document.getElementById('c_email').value;
            const phone = document.getElementById('c_phone').value;
            const subject = document.getElementById('c_subject').value;
            const message = document.getElementById('c_msg').value;
            
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
                
                if (window.DB) {
                    window.DB.addEnquiry({
                        name: name,
                        email: email,
                        phone: phone,
                        subject: subject,
                        message: message,
                        type: 'General Enquiry'
                    });
                    
                    if (contactAlert) {
                        contactAlert.className = 'alert alert-success';
                        contactAlert.innerHTML = '<strong>Message Sent successfully!</strong> Thank you for contacting Success Academy. We have logged your request in our local data engine. Our counselor will review it in the admin dashboard.';
                        contactAlert.style.display = 'block';
                        contactForm.reset();
                        window.scrollTo({
                            top: contactAlert.offsetTop - 100,
                            behavior: 'smooth'
                        });
                    }
                }
            }, 800);
        });
    }

    // 4. AJAX Form - Quick Enquiry Form Submission (Mocked with LocalStorage)
    const quickEnquiryForm = document.getElementById('quickEnquiryForm');
    const enquiryAlert = document.getElementById('enquiryAlert');

    if (quickEnquiryForm) {
        quickEnquiryForm.addEventListener('submit', function (e) {
            e.preventDefault();
            
            const submitBtn = quickEnquiryForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Submitting...';
            
            const name = document.getElementById('eq_name').value;
            const phone = document.getElementById('eq_phone').value;
            const email = document.getElementById('eq_email').value;
            const courseSelect = document.getElementById('eq_course');
            const course_id = courseSelect.value;
            const course_title = courseSelect.options[courseSelect.selectedIndex].text;
            const message = document.getElementById('eq_msg').value || 'Quick Enquiry Callback';
            
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
                
                if (window.DB) {
                    window.DB.addEnquiry({
                        name: name,
                        phone: phone,
                        email: email,
                        course_id: course_id,
                        subject: `Callback: ${course_title}`,
                        message: message,
                        type: 'Admission Quick'
                    });
                    
                    if (enquiryAlert) {
                        enquiryAlert.className = 'alert alert-success py-2 mb-3';
                        enquiryAlert.innerHTML = 'Enquiry logged! Our academic advisor will contact you within 24 hours.';
                        enquiryAlert.style.display = 'block';
                        quickEnquiryForm.reset();
                    }
                }
            }, 600);
        });
    }

    // 5. AJAX Form - Online Admission Form (Mocked with LocalStorage & Base64 image reader)
    const admissionForm = document.getElementById('admissionForm');
    const admissionAlert = document.getElementById('admissionAlert');

    if (admissionForm) {
        admissionForm.addEventListener('submit', function (e) {
            e.preventDefault();
            
            const submitBtn = admissionForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin me-2"></i>Processing Registration...';
            
            const student_name = document.getElementById('ad_name').value;
            const father_name = document.getElementById('ad_father').value;
            const mobile = document.getElementById('ad_phone').value;
            const email = document.getElementById('ad_email').value;
            const className = document.getElementById('ad_class').value;
            const courseSelect = document.getElementById('ad_course');
            const course_id = courseSelect.value;
            const course_title = courseSelect.options[courseSelect.selectedIndex].text;
            const address = document.getElementById('ad_address').value;
            
            const photoInput = document.getElementById('ad_photo');
            
            const saveRegistration = (photoBase64) => {
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                    
                    if (window.DB) {
                        const refId = window.DB.addAdmission({
                            student_name: student_name,
                            father_name: father_name,
                            mobile: mobile,
                            email: email,
                            class_name: className,
                            course_id: course_id,
                            course_title: course_title,
                            address: address,
                            photo_path: photoBase64
                        });
                        
                        if (admissionAlert) {
                            admissionAlert.className = 'alert alert-success';
                            admissionAlert.innerHTML = `<strong>Registration Successful!</strong> Your application has been logged under reference #${refId} in our local engine. Please visit the admin dashboard to review your status.`;
                            admissionAlert.style.display = 'block';
                            admissionForm.reset();
                            window.scrollTo({
                                top: admissionAlert.offsetTop - 120,
                                behavior: 'smooth'
                            });
                        }
                    }
                }, 1000);
            };
            
            // Read photo as Base64 if uploaded
            if (photoInput && photoInput.files[0]) {
                const reader = new FileReader();
                reader.onload = function (event) {
                    saveRegistration(event.target.result);
                };
                reader.readAsDataURL(photoInput.files[0]);
            } else {
                saveRegistration('');
            }
        });
    }
});
