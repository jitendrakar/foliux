/**
 * Client-Side Admin Auth & Components Loader
 * Success Academy Coaching Institute
 */

(function () {
    const currentPath = window.location.pathname;
    const isLoginPage = currentPath.endsWith('login.html');
    
    // 1. Session Authentication Check
    if (!sessionStorage.getItem('sa_admin_logged_in')) {
        if (!isLoginPage) {
            window.location.href = 'login.html';
            return;
        }
    } else {
        if (isLoginPage) {
            window.location.href = 'index.html';
            return;
        }
    }

    // 2. Load Layout Elements on DOM Load
    document.addEventListener('DOMContentLoaded', function () {
        if (isLoginPage) return;

        const adminName = sessionStorage.getItem('sa_admin_name') || 'Administrator';
        const currentFile = currentPath.substring(currentPath.lastIndexOf('/') + 1) || 'index.html';
        
        // Inject Sidebar
        const sidebarPlaceholder = document.getElementById('admin-sidebar-placeholder');
        if (sidebarPlaceholder) {
            sidebarPlaceholder.innerHTML = `
                <aside class="admin-sidebar">
                    <div class="admin-sidebar-brand text-center">
                        <h4 class="text-white fw-bold mb-0 text-uppercase"><i class="fa-solid fa-graduation-cap text-warning me-2"></i>Success</h4>
                        <small class="text-white-50">Academy Admin Panel</small>
                    </div>
                    
                    <ul class="admin-nav">
                        <li class="admin-nav-item ${currentFile === 'index.html' ? 'active' : ''}">
                            <a href="index.html"><i class="fa-solid fa-chart-line"></i> <span>Dashboard</span></a>
                        </li>
                        <li class="admin-nav-item ${currentFile === 'courses.html' ? 'active' : ''}">
                            <a href="courses.html"><i class="fa-solid fa-book"></i> <span>Manage Courses</span></a>
                        </li>
                        <li class="admin-nav-item ${currentFile === 'faculty.html' ? 'active' : ''}">
                            <a href="faculty.html"><i class="fa-solid fa-chalkboard-user"></i> <span>Manage Faculty</span></a>
                        </li>
                        <li class="admin-nav-item ${currentFile === 'students.html' ? 'active' : ''}">
                            <a href="students.html"><i class="fa-solid fa-user-graduate"></i> <span>Manage Admissions</span></a>
                        </li>
                        <li class="admin-nav-item ${currentFile === 'enquiries.html' ? 'active' : ''}">
                            <a href="enquiries.html"><i class="fa-solid fa-envelope-open-text"></i> <span>Enquiries</span></a>
                        </li>
                        <li class="admin-nav-item ${currentFile === 'gallery.html' ? 'active' : ''}">
                            <a href="gallery.html"><i class="fa-solid fa-images"></i> <span>Manage Gallery</span></a>
                        </li>
                        <li class="admin-nav-item ${currentFile === 'news.html' ? 'active' : ''}">
                            <a href="news.html"><i class="fa-solid fa-newspaper"></i> <span>Manage News</span></a>
                        </li>
                        <li class="admin-nav-item ${currentFile === 'testimonials.html' ? 'active' : ''}">
                            <a href="testimonials.html"><i class="fa-solid fa-comment-dots"></i> <span>Testimonials</span></a>
                        </li>
                        <li class="admin-nav-item ${currentFile === 'settings.html' ? 'active' : ''}">
                            <a href="settings.html"><i class="fa-solid fa-gears"></i> <span>Site Settings</span></a>
                        </li>
                        <li class="admin-nav-item mt-4">
                            <a href="../index.html" target="_blank"><i class="fa-solid fa-arrow-up-right-from-square text-info"></i> <span>Visit Live Website</span></a>
                        </li>
                    </ul>
                </aside>
            `;
        }

        // Inject Header
        const headerPlaceholder = document.getElementById('admin-header-placeholder');
        if (headerPlaceholder) {
            headerPlaceholder.innerHTML = `
                <header class="admin-header">
                    <h4 class="fw-bold mb-0 text-primary-dark d-none d-md-block">Admin Portal Dashboard</h4>
                    <div class="d-flex align-items-center gap-3 ms-auto">
                        <span class="text-muted small"><i class="fa-solid fa-circle text-success me-1 fs-9"></i> Active Session</span>
                        <span class="fw-semibold text-dark"><i class="fa-solid fa-user-tie me-2 text-primary"></i>${adminName}</span>
                        <button id="admin-logout-btn" class="btn btn-outline-danger btn-sm"><i class="fa-solid fa-right-from-bracket me-1"></i>Logout</button>
                    </div>
                </header>
            `;
            
            // Bind logout
            document.getElementById('admin-logout-btn').addEventListener('click', function () {
                sessionStorage.removeItem('sa_admin_logged_in');
                sessionStorage.removeItem('sa_admin_name');
                window.location.href = 'login.html';
            });
        }

        // Inject Footer
        const footerPlaceholder = document.getElementById('admin-footer-placeholder');
        if (footerPlaceholder) {
            footerPlaceholder.innerHTML = `
                <footer class="bg-white border-top py-3 text-center text-muted small mt-auto">
                    &copy; ${new Date().getFullYear()} Success Academy Coaching Institute Admin Portal (Demo). All Rights Reserved.
                </footer>
            `;
        }
    });
})();
