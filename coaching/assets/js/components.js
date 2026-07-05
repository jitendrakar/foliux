/**
 * Client-Side Shared Components Loader
 * Success Academy Coaching Institute
 */

document.addEventListener('DOMContentLoaded', function () {
    const settings = window.DB ? window.DB.getSettings() : {};
    
    // Inject Header
    const headerPlaceholder = document.getElementById('header-placeholder');
    if (headerPlaceholder) {
        const isAdmissionOpen = settings.admission_status == 1;
        const currentPath = window.location.pathname;
        const currentFile = currentPath.substring(currentPath.lastIndexOf('/') + 1) || 'index.html';
        
        // Is admin directory context
        const isAdmin = currentPath.includes('/admin');
        const baseUrl = isAdmin ? '../' : '';
        
        let headerHtml = `
            <!-- Top Bar Strip -->
            <div class="top-bar d-none d-lg-block">
                <div class="container">
                    <div class="row align-items-center">
                        <div class="col-md-7">
                            <span class="me-3"><i class="fa-solid fa-phone me-2 text-warning"></i> Call: <a href="tel:${settings.contact_phone.replace(/\s+/g, '')}">${settings.contact_phone}</a></span>
                            <span><i class="fa-solid fa-envelope me-2 text-warning"></i> Email: <a href="mailto:${settings.contact_email}">${settings.contact_email}</a></span>
                        </div>
                        <div class="col-md-5 text-end">
                            <span class="me-3"><i class="fa-regular fa-clock me-2 text-warning"></i> ${settings.working_hours}</span>
                            ${isAdmissionOpen ? `<a href="${baseUrl}admission.html" class="badge bg-danger text-white py-2 px-3 fw-bold text-uppercase"><i class="fa-solid fa-graduation-cap me-1"></i> Admissions Open 2026-27</a>` : ''}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Header / Main Navigation -->
            <nav class="navbar navbar-expand-lg navbar-light sticky-top shadow-sm">
                <div class="container">
                    <a class="navbar-brand fw-bold fs-4 text-uppercase" href="${baseUrl}index.html">
                        <i class="fa-solid fa-graduation-cap text-primary fs-3"></i> Success <span>Academy</span>
                    </a>
                    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNavbar" aria-controls="mainNavbar" aria-expanded="false" aria-label="Toggle navigation">
                        <span class="navbar-toggler-icon"></span>
                    </button>
                    
                    <div class="collapse navbar-collapse" id="mainNavbar">
                        <ul class="navbar-nav ms-auto mb-2 mb-lg-0 align-items-lg-center">
                            <li class="nav-item">
                                <a class="nav-link ${currentFile === 'index.html' ? 'active' : ''}" href="${baseUrl}index.html">Home</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link ${currentFile === 'about.html' ? 'active' : ''}" href="${baseUrl}about.html">About Us</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link ${currentFile === 'courses.html' ? 'active' : ''}" href="${baseUrl}courses.html">Courses</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link ${currentFile === 'faculty.html' ? 'active' : ''}" href="${baseUrl}faculty.html">Faculty</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link ${currentFile === 'results.html' ? 'active' : ''}" href="${baseUrl}results.html">Results</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link ${currentFile === 'gallery.html' ? 'active' : ''}" href="${baseUrl}gallery.html">Gallery</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link ${currentFile === 'blog.html' || currentFile === 'blog-details.html' ? 'active' : ''}" href="${baseUrl}blog.html">Blog/News</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link ${currentFile === 'contact.html' ? 'active' : ''}" href="${baseUrl}contact.html">Contact</a>
                            </li>
                            <li class="nav-item ms-lg-3 mt-3 mt-lg-0">
                                <a href="${baseUrl}admission.html" class="btn btn-secondary text-white btn-sm px-4 py-2"><i class="fa-solid fa-file-signature me-1"></i> Apply Online</a>
                            </li>
                        </ul>
                    </div>
                </div>
            </nav>
            
            ${isAdmissionOpen ? `
            <!-- Mobile Admissions Ribbon (Visible on phone only) -->
            <div class="admission-banner d-lg-none">
                <a href="${baseUrl}admission.html" class="text-white text-decoration-none">
                    <i class="fa-solid fa-bullhorn me-2 animate-bounce"></i> Admissions Open for 2026-27! Apply Now
                </a>
            </div>` : ''}
        `;
        
        headerPlaceholder.innerHTML = headerHtml;
        
        // Sticky nav scroll handler
        const navbar = headerPlaceholder.querySelector('.navbar');
        if (navbar) {
            window.addEventListener('scroll', function () {
                if (window.scrollY > 80) {
                    navbar.classList.add('sticky-nav');
                } else {
                    navbar.classList.remove('sticky-nav');
                }
            });
        }
    }

    // Inject Footer
    const footerPlaceholder = document.getElementById('footer-placeholder');
    if (footerPlaceholder) {
        const currentPath = window.location.pathname;
        const isAdmin = currentPath.includes('/admin');
        const baseUrl = isAdmin ? '../' : '';
        
        let footerHtml = `
            <!-- Footer Section -->
            <footer class="footer-section">
                <div class="container">
                    <div class="row g-4">
                        <!-- Column 1: About -->
                        <div class="col-lg-4 col-md-6">
                            <h4 class="text-white fw-bold mb-3">Success Academy</h4>
                            <p class="text-white-50 mb-4">Success Academy is Rajasthan's premier coaching center dedicated to training students for IIT-JEE, NEET, Civil Services, government exams, and strengthening school foundations. We nurture potential into top results.</p>
                            <div class="footer-social-icons">
                                ${settings.facebook_url ? `<a href="${settings.facebook_url}" target="_blank"><i class="fa-brands fa-facebook-f"></i></a>` : ''}
                                ${settings.instagram_url ? `<a href="${settings.instagram_url}" target="_blank"><i class="fa-brands fa-instagram"></i></a>` : ''}
                                ${settings.youtube_url ? `<a href="${settings.youtube_url}" target="_blank"><i class="fa-brands fa-youtube"></i></a>` : ''}
                                <a href="#" target="_blank"><i class="fa-brands fa-x-twitter"></i></a>
                            </div>
                        </div>
                        
                        <!-- Column 2: Quick Links -->
                        <div class="col-lg-2 col-md-6">
                            <h5>Quick Links</h5>
                            <ul class="footer-links">
                                <li><a href="${baseUrl}index.html">Home</a></li>
                                <li><a href="${baseUrl}about.html">About Us</a></li>
                                <li><a href="${baseUrl}courses.html">Courses Offered</a></li>
                                <li><a href="${baseUrl}faculty.html">Our Faculty</a></li>
                                <li><a href="${baseUrl}results.html">Success Stories</a></li>
                                <li><a href="${baseUrl}gallery.html">Campus Gallery</a></li>
                            </ul>
                        </div>
                        
                        <!-- Column 3: Exams -->
                        <div class="col-lg-3 col-md-6">
                            <h5>Popular Courses</h5>
                            <ul class="footer-links">
                                <li><a href="${baseUrl}courses.html?cat=JEE">IIT-JEE Main &amp; Adv</a></li>
                                <li><a href="${baseUrl}courses.html?cat=NEET">NEET Medical Prep</a></li>
                                <li><a href="${baseUrl}courses.html?cat=UPSC">UPSC Foundation</a></li>
                                <li><a href="${baseUrl}courses.html?cat=NDA">NDA Entrance</a></li>
                                <li><a href="${baseUrl}courses.html?cat=Foundation">NTSE &amp; Olympiads</a></li>
                                <li><a href="${baseUrl}courses.html?cat=Government">SSC &amp; Govt Exams</a></li>
                            </ul>
                        </div>
                        
                        <!-- Column 4: Contact & Newsletter -->
                        <div class="col-lg-3 col-md-6">
                            <h5>Contact Us</h5>
                            <p class="mb-2 text-white-50"><i class="fa-solid fa-location-dot me-2 text-warning"></i> ${settings.office_address}</p>
                            <p class="mb-2"><i class="fa-solid fa-phone me-2 text-warning"></i> <a href="tel:${settings.contact_phone.replace(/\s+/g, '')}" class="text-white-50">${settings.contact_phone}</a></p>
                            <p class="mb-4"><i class="fa-solid fa-envelope me-2 text-warning"></i> <a href="mailto:${settings.contact_email}" class="text-white-50">${settings.contact_email}</a></p>
                            
                            <h6 class="text-white mb-2 fw-semibold">Subscribe Newsletter</h6>
                            <form id="newsletterForm" class="input-group">
                                <input type="email" class="form-control form-control-sm" placeholder="Enter Email" required>
                                <button class="btn btn-secondary btn-sm" type="submit"><i class="fa-solid fa-paper-plane"></i></button>
                            </form>
                            <div id="newsletterMsg" class="mt-2 small text-success" style="display:none;">Thank you for subscribing!</div>
                        </div>
                    </div>
                    
                    <!-- Copyright & Legals -->
                    <div class="footer-bottom text-center">
                        <div class="row align-items-center">
                            <div class="col-md-6 text-md-start mb-3 mb-md-0">
                                <p class="mb-0">&copy; ${new Date().getFullYear()} Success Academy Coaching Institute (Demo). All Rights Reserved.</p>
                            </div>
                            <div class="col-md-6 text-md-end">
                                <a href="#" class="text-white-50 me-3 small">Privacy Policy</a>
                                <a href="#" class="text-white-50 small">Terms &amp; Conditions</a>
                            </div>
                        </div>
                    </div>
                </div>
            </footer>

            <!-- Floating Call & WhatsApp Widgets -->
            <div class="floating-widgets">
                <!-- Click-to-Call -->
                <a href="tel:${settings.contact_phone.replace(/\s+/g, '')}" class="widget-btn widget-call" title="Call Us Now">
                    <i class="fa-solid fa-phone"></i>
                </a>
                <!-- WhatsApp Widget -->
                <a href="https://wa.me/${settings.contact_whatsapp.replace(/[\s+]+/g, '')}?text=Hello%20Success%20Academy%2C%20I%20am%20interested%20in%20courses%20for%20the%20academic%20year%202026-27." target="_blank" class="widget-btn widget-whatsapp" title="Chat on WhatsApp">
                    <i class="fa-brands fa-whatsapp"></i>
                </a>
            </div>

            <!-- Image Lightbox Modal -->
            <div class="modal fade lightbox-modal" id="lightboxModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered modal-lg">
                    <div class="modal-content">
                        <div class="modal-body text-center">
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            <img src="" id="lightboxImg" class="img-fluid rounded shadow" alt="Zoomed view">
                            <h5 class="text-white mt-3" id="lightboxCaption"></h5>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        footerPlaceholder.innerHTML = footerHtml;
        
        // Bind Newsletter Submit
        const newsletterForm = document.getElementById('newsletterForm');
        const newsletterMsg = document.getElementById('newsletterMsg');
        if (newsletterForm) {
            newsletterForm.addEventListener('submit', function (e) {
                e.preventDefault();
                newsletterMsg.style.display = 'block';
                newsletterForm.reset();
                setTimeout(() => {
                    newsletterMsg.style.display = 'none';
                }, 4000);
            });
        }
    }
});
