// Restaurant Website JavaScript Actions

document.addEventListener('DOMContentLoaded', function() {
    
    // 1. Header Scroll Effect
    const header = document.querySelector('.header-nav');
    if (header) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        });
        
        // Trigger scroll once on load in case page is refreshed while scrolled down
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
        }
    }
    
    // 2. Mobile Drawer Navigation Menu Controls
    const mobileMenuOpenBtn = document.getElementById('mobileMenuOpen');
    const mobileMenuCloseBtn = document.getElementById('mobileMenuClose');
    const drawerOverlay = document.getElementById('drawerOverlay');
    const mobileDrawer = document.getElementById('mobileDrawer');
    
    if (mobileMenuOpenBtn && mobileDrawer && drawerOverlay) {
        mobileMenuOpenBtn.addEventListener('click', function() {
            mobileDrawer.classList.add('open');
            drawerOverlay.classList.add('active');
            document.body.style.overflow = 'hidden'; // Disable background scroll
        });
    }
    
    function closeDrawer() {
        if (mobileDrawer && drawerOverlay) {
            mobileDrawer.classList.remove('open');
            drawerOverlay.classList.remove('active');
            document.body.style.overflow = ''; // Enable background scroll
        }
    }
    
    if (mobileMenuCloseBtn) {
        mobileMenuCloseBtn.addEventListener('click', closeDrawer);
    }
    
    if (drawerOverlay) {
        drawerOverlay.addEventListener('click', closeDrawer);
    }
    
    // 3. Client-Side Reservation Date Restriction (No past dates)
    const dateInputs = document.querySelectorAll('input[type="date"]');
    if (dateInputs.length > 0) {
        const today = new Date().toISOString().split('T')[0];
        dateInputs.forEach(input => {
            input.setAttribute('min', today);
        });
    }
});
