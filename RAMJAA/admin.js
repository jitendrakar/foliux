// RAMJAA Administration Panel Controller
// Manage notice uploads, gallery uploads, and registered alumni rosters.

// Check Admin Authentication Status
function checkAdminLogin() {
    const isLogged = sessionStorage.getItem('ramjaa_admin_logged') === 'true';
    const loginCard = document.getElementById('admin-login-card');
    const dashboard = document.getElementById('admin-dashboard');

    if (isLogged) {
        if (loginCard) loginCard.style.style = 'none';
        if (loginCard) loginCard.style.display = 'none';
        if (dashboard) dashboard.style.display = 'block';
        renderAdminDashboard();
    } else {
        if (loginCard) loginCard.style.display = 'block';
        if (dashboard) dashboard.style.display = 'none';
    }
}

// Render the entire Admin Dashboard data based on selected tab
function renderAdminDashboard() {
    const lang = window.appState.currentLanguage;
    
    // Render Admin Notices Table
    renderAdminNotices();

    // Render Admin Gallery Table
    renderAdminGallery();

    // Render Admin Alumni Roster Table
    renderAdminRoster();

    // Populate Roster Batch filter list
    populateAdminRosterBatches();
}

// 1. NOTICE MANAGEMENT IN ADMIN
function renderAdminNotices() {
    const tableBody = document.getElementById('admin-notices-table-body');
    if (!tableBody) return;

    tableBody.innerHTML = '';
    
    // Sort notices by date descending
    const notices = [...window.appState.notices].sort((a, b) => new Date(b.date) - new Date(a.date));

    if (notices.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="4" class="text-center" style="color: var(--text-muted);">${window.appState.currentLanguage === 'or' ? "କୌଣସି ବିଜ୍ଞପ୍ତି ନାହିଁ।" : "No notices found."}</td></tr>`;
        return;
    }

    notices.forEach(notice => {
        const title = window.appState.currentLanguage === 'or' ? notice.title_or : notice.title_en;
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${notice.date}</td>
            <td style="font-weight: 600; color: var(--primary);">${title}</td>
            <td><span class="notice-category ${notice.category.toLowerCase() === 'urgent' ? 'urgent' : (notice.category.toLowerCase() === 'academic' ? 'academic' : 'event')}" style="padding: 2px 8px; font-size: 0.7rem;">${notice.category}</span></td>
            <td>
                <button class="action-badge delete" data-id="${notice.id}">${window.appState.currentLanguage === 'or' ? "ଡିଲିଟ୍" : "Delete"}</button>
            </td>
        `;

        row.querySelector('.delete').addEventListener('click', () => {
            if (confirm(window.appState.currentLanguage === 'or' ? "ଆପଣ ଏହି ବିଜ୍ଞପ୍ତିକୁ ଡିଲିଟ୍ କରିବାକୁ ଚାହାଁନ୍ତି କି?" : "Are you sure you want to delete this notice?")) {
                deleteNotice(notice.id);
            }
        });

        tableBody.appendChild(row);
    });
}

function deleteNotice(id) {
    window.appState.notices = window.appState.notices.filter(n => n.id !== id);
    localStorage.setItem('ramjaa_notices', JSON.stringify(window.appState.notices));
    
    renderAdminNotices();
    window.showToast(window.appState.currentLanguage === 'or' ? "ବିଜ୍ଞପ୍ତି ଡିଲିଟ୍ ହେଲା" : "Notice deleted successfully", "success");
}

function handleAddNotice(e) {
    e.preventDefault();

    const title = document.getElementById('an-title').value.trim();
    const category = document.getElementById('an-category').value;
    const desc = document.getElementById('an-desc').value.trim();
    const dateToday = new Date().toISOString().split('T')[0];

    const newNotice = {
        id: 'n_' + Date.now(),
        date: dateToday,
        title_en: title,
        title_or: title, // Store same text for Odia fallback
        desc_en: desc,
        desc_or: desc,
        category: category
    };

    window.appState.notices.push(newNotice);
    localStorage.setItem('ramjaa_notices', JSON.stringify(window.appState.notices));

    document.getElementById('admin-add-notice-form').reset();
    renderAdminNotices();
    
    window.showToast(window.appState.currentLanguage === 'or' ? "ବିଜ୍ଞପ୍ତି ସଫଳତାର ସହ ପ୍ରକାଶିତ ହେଲା!" : "Notice published successfully!", "success");
}

// 2. GALLERY MANAGEMENT IN ADMIN
function renderAdminGallery() {
    const tableBody = document.getElementById('admin-gallery-table-body');
    if (!tableBody) return;

    tableBody.innerHTML = '';
    const gallery = [...window.appState.gallery].sort((a, b) => new Date(b.date) - new Date(a.date));

    if (gallery.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="4" class="text-center" style="color: var(--text-muted);">${window.appState.currentLanguage === 'or' ? "କୌଣସି ଫଟୋ ନାହିଁ।" : "No gallery images found."}</td></tr>`;
        return;
    }

    gallery.forEach(item => {
        const caption = window.appState.currentLanguage === 'or' ? item.caption_or : item.caption_en;
        const row = document.createElement('tr');

        row.innerHTML = `
            <td><img src="${item.path}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px; border: 1px solid var(--border-color);"></td>
            <td style="font-weight: 500;">${caption}</td>
            <td>${item.category}</td>
            <td>
                <button class="action-badge delete" data-id="${item.id}">${window.appState.currentLanguage === 'or' ? "ଡିଲିଟ୍" : "Delete"}</button>
            </td>
        `;

        row.querySelector('.delete').addEventListener('click', () => {
            if (confirm(window.appState.currentLanguage === 'or' ? "ଆପଣ ଏହି ଫଟୋକୁ ଡିଲିଟ୍ କରିବାକୁ ଚାହାଁନ୍ତି କି?" : "Are you sure you want to delete this photo from the gallery?")) {
                deleteGalleryItem(item.id);
            }
        });

        tableBody.appendChild(row);
    });
}

function deleteGalleryItem(id) {
    window.appState.gallery = window.appState.gallery.filter(g => g.id !== id);
    localStorage.setItem('ramjaa_gallery', JSON.stringify(window.appState.gallery));
    
    renderAdminGallery();
    window.showToast(window.appState.currentLanguage === 'or' ? "ଫଟୋ ଗ୍ୟାଲେରୀରୁ ହଟାଗଲା" : "Photo removed from gallery", "success");
}

function handleAddGallery(e) {
    e.preventDefault();

    const caption = document.getElementById('ag-title').value.trim();
    const category = document.getElementById('ag-category').value;
    const photoInput = document.getElementById('ag-photo');
    const dateToday = new Date().toISOString().split('T')[0];

    if (!photoInput.files || !photoInput.files[0]) {
        window.showToast("Please select a file first", "error");
        return;
    }

    const reader = new FileReader();
    reader.onload = function(event) {
        const base64Image = event.target.result;

        const newGalleryItem = {
            id: 'g_' + Date.now(),
            path: base64Image,
            caption_en: caption,
            caption_or: caption,
            category: category,
            date: dateToday
        };

        window.appState.gallery.push(newGalleryItem);
        localStorage.setItem('ramjaa_gallery', JSON.stringify(window.appState.gallery));

        document.getElementById('admin-add-gallery-form').reset();
        document.getElementById('ag-photo-preview').style.display = 'none';
        
        renderAdminGallery();
        window.showToast(window.appState.currentLanguage === 'or' ? "ଫଟୋ ଗ୍ୟାଲେରୀରେ ସଫଳତାର ସହ ଯୋଡ଼ାଗଲା!" : "Photo added to gallery successfully!", "success");
    };

    reader.readAsDataURL(photoInput.files[0]);
}

// 3. ROSTER MANAGEMENT IN ADMIN
function renderAdminRoster() {
    const tableBody = document.getElementById('admin-roster-table-body');
    if (!tableBody) return;

    tableBody.innerHTML = '';

    const searchTerm = document.getElementById('admin-roster-search').value.toLowerCase();
    const filterBatch = document.getElementById('admin-roster-filter-batch').value;

    const filtered = window.appState.alumni.filter(member => {
        const matchesSearch = member.name.toLowerCase().includes(searchTerm) || 
                              member.profession.toLowerCase().includes(searchTerm) || 
                              member.location.toLowerCase().includes(searchTerm) || 
                              member.id.toLowerCase().includes(searchTerm);
                              
        const matchesBatch = filterBatch === '' || member.batch === filterBatch;

        return matchesSearch && matchesBatch;
    });

    if (filtered.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="7" class="text-center" style="color: var(--text-muted);">${window.appState.currentLanguage === 'or' ? "କୌଣସି ଛାତ୍ରଛାତ୍ରୀ ମିଳିଲେ ନାହିଁ।" : "No registered alumni found matching filters."}</td></tr>`;
        return;
    }

    filtered.forEach(member => {
        const row = document.createElement('tr');

        row.innerHTML = `
            <td><img src="${member.photo}" class="admin-avatar" alt="${member.name}"></td>
            <td>
                <div style="font-weight: 700; color: var(--primary);">${member.name}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">${member.id}</div>
            </td>
            <td style="font-weight: 600;">${member.batch}</td>
            <td>
                <div>${member.mobile}</div>
                <div style="font-size: 0.8rem; color: var(--text-muted);">${member.email}</div>
            </td>
            <td>${member.profession}</td>
            <td>${member.location}</td>
            <td>
                <button class="action-badge delete" data-id="${member.id}">${window.appState.currentLanguage === 'or' ? "ଡିଲିଟ୍" : "Delete"}</button>
            </td>
        `;

        row.querySelector('.delete').addEventListener('click', () => {
            if (confirm(window.appState.currentLanguage === 'or' ? `ଆପଣ ${member.name} ଙ୍କ ପଞ୍ଜୀକରଣ ରଦ୍ଦ କରିବାକୁ ଚାହାଁନ୍ତି କି?` : `Are you sure you want to delete registration for ${member.name}?`)) {
                deleteAlumni(member.id);
            }
        });

        tableBody.appendChild(row);
    });
}

function deleteAlumni(id) {
    window.appState.alumni = window.appState.alumni.filter(a => a.id !== id);
    localStorage.setItem('ramjaa_alumni', JSON.stringify(window.appState.alumni));
    
    // Update count stat in Home view
    const counter = document.getElementById('stat-alumni-count');
    if (counter) counter.textContent = `${window.appState.alumni.length}+`;

    renderAdminRoster();
    populateAdminRosterBatches();
    window.showToast(window.appState.currentLanguage === 'or' ? "ପଞ୍ଜୀକରଣ ଡିଲିଟ୍ ହେଲା" : "Alumni registration deleted", "success");
}

function populateAdminRosterBatches() {
    const dropdown = document.getElementById('admin-roster-filter-batch');
    if (!dropdown) return;

    // Keep the first item "All Batches"
    const currentSelVal = dropdown.value;
    dropdown.innerHTML = `<option value="" data-en="All Batches" data-or="ସମସ୍ତ ବ୍ୟାଚ୍">${window.appState.currentLanguage === 'or' ? "ସମସ୍ତ ବ୍ୟାଚ୍" : "All Batches"}</option>`;

    // Get unique sorted batches
    const batches = [...new Set(window.appState.alumni.map(a => a.batch))];
    batches.sort((a, b) => b - a);

    batches.forEach(batch => {
        const opt = document.createElement('option');
        opt.value = batch;
        opt.textContent = batch;
        dropdown.appendChild(opt);
    });

    // Reapply selected value if it still exists
    if (batches.includes(currentSelVal)) {
        dropdown.value = currentSelVal;
    }
}

// 4. CSV & JSON EXPORTERS
function exportRosterCSV() {
    if (window.appState.alumni.length === 0) {
        window.showToast("No alumni data to export", "error");
        return;
    }

    // CSV header columns
    const headers = ["MemberID", "Name", "BatchYear", "Mobile", "Email", "Profession", "Location", "Memories"];
    
    // Convert rows
    const rows = window.appState.alumni.map(a => {
        return [
            a.id,
            `"${a.name.replace(/"/g, '""')}"`,
            a.batch,
            a.mobile,
            a.email,
            `"${(a.profession || '').replace(/"/g, '""')}"`,
            `"${a.location.replace(/"/g, '""')}"`,
            `"${(a.message || '').replace(/\r?\n|\r/g, ' ').replace(/"/g, '""')}"`
        ];
    });

    const csvContent = "data:text/csv;charset=utf-8," 
                     + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `ramjaa_alumni_roster_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    window.showToast("CSV exported successfully", "success");
}

function exportRosterJSON() {
    if (window.appState.alumni.length === 0) {
        window.showToast("No alumni data to export", "error");
        return;
    }

    const jsonString = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(window.appState.alumni, null, 2));
    const link = document.createElement("a");
    link.setAttribute("href", jsonString);
    link.setAttribute("download", `ramjaa_alumni_roster_${new Date().toISOString().split('T')[0]}.json`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    window.showToast("JSON exported successfully", "success");
}

// 5. EVENT LISTENERS INITIALIZATION FOR ADMIN
document.addEventListener('DOMContentLoaded', () => {
    
    // Admin Login form submit
    const loginForm = document.getElementById('admin-login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const passVal = document.getElementById('admin-pass').value;
            
            if (passVal === 'admin_ramjaa') {
                sessionStorage.setItem('ramjaa_admin_logged', 'true');
                document.getElementById('admin-pass').value = '';
                checkAdminLogin();
                window.showToast(window.appState.currentLanguage === 'or' ? "ଲଗ୍-ଇନ୍ ସଫଳ ହେଲା!" : "Login successful!", "success");
            } else {
                window.showToast(window.appState.currentLanguage === 'or' ? "ভୁଲ୍ ପାସୱାର୍ଡ!" : "Invalid admin password!", "error");
            }
        });
    }

    // Admin Logout button
    const logoutBtn = document.getElementById('admin-logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            sessionStorage.removeItem('ramjaa_admin_logged');
            checkAdminLogin();
            window.showToast("Logged out successfully", "success");
        });
    }

    // Sidebar tab selection controls
    document.querySelectorAll('.admin-menu-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active classes
            document.querySelectorAll('.admin-menu-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.admin-tab-view').forEach(tab => tab.classList.remove('active'));

            // Set active class
            btn.classList.add('active');
            
            const tabId = btn.getAttribute('data-tab');
            const targetTab = document.getElementById(tabId);
            if (targetTab) targetTab.classList.add('active');
        });
    });

    // Notice publishing form submit hook
    const addNoticeForm = document.getElementById('admin-add-notice-form');
    if (addNoticeForm) {
        addNoticeForm.addEventListener('submit', handleAddNotice);
    }

    // Photo gallery publishing form submit hook
    const addGalleryForm = document.getElementById('admin-add-gallery-form');
    if (addGalleryForm) {
        addGalleryForm.addEventListener('submit', handleAddGallery);
    }

    // Photo file preview in Admin uploader
    const agPhotoInput = document.getElementById('ag-photo');
    const agPhotoPreview = document.getElementById('ag-photo-preview');
    if (agPhotoInput && agPhotoPreview) {
        agPhotoInput.addEventListener('change', () => {
            if (agPhotoInput.files && agPhotoInput.files[0]) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    agPhotoPreview.src = event.target.result;
                    agPhotoPreview.style.display = 'block';
                    agPhotoPreview.style.margin = '10px auto';
                    agPhotoPreview.style.maxHeight = '120px';
                };
                reader.readAsDataURL(agPhotoInput.files[0]);
            }
        });
    }

    // Roster search and filters listeners
    const rosterSearchInput = document.getElementById('admin-roster-search');
    if (rosterSearchInput) {
        rosterSearchInput.addEventListener('input', renderAdminRoster);
    }

    const rosterFilterBatchDropdown = document.getElementById('admin-roster-filter-batch');
    if (rosterFilterBatchDropdown) {
        rosterFilterBatchDropdown.addEventListener('change', renderAdminRoster);
    }

    // Exporter buttons listeners
    const csvBtn = document.getElementById('export-csv-btn');
    if (csvBtn) csvBtn.addEventListener('click', exportRosterCSV);

    const jsonBtn = document.getElementById('export-json-btn');
    if (jsonBtn) jsonBtn.addEventListener('click', exportRosterJSON);
});

// Attach helper functions to window for SPA routers
window.checkAdminLogin = checkAdminLogin;
window.renderAdminDashboard = renderAdminDashboard;
