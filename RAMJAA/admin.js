// RAMJAA Administration Panel Controller - Backend Integrated
// Manage notice uploads, gallery uploads, and registered alumni rosters via REST APIs.

// Local appState configuration for admin view
const appState = {
    currentLanguage: localStorage.getItem('ramjaa_lang') || 'or',
    notices: [],
    gallery: [],
    alumni: []
};
window.appState = appState;

// Simple custom toast alert function
function showToast(message, type = "success") {
    const alertBox = document.getElementById('custom-alert');
    if (!alertBox) return;
    alertBox.textContent = message;
    alertBox.className = "custom-alert show";
    if (type === "error") {
        alertBox.style.background = "#e74c3c";
    } else {
        alertBox.style.background = "var(--secondary)";
    }
    setTimeout(() => {
        alertBox.classList.remove('show');
    }, 3500);
}
window.showToast = showToast;

// Enforce language on text tags
function translateAdminPage(lang) {
    appState.currentLanguage = lang;
    localStorage.setItem('ramjaa_lang', lang);
    document.documentElement.setAttribute('lang', lang);
    
    // Toggle active switch btn CSS
    const orBtn = document.getElementById('lang-or-btn');
    const enBtn = document.getElementById('lang-en-btn');
    if (orBtn && enBtn) {
        if (lang === 'or') {
            orBtn.classList.add('active');
            enBtn.classList.remove('active');
        } else {
            enBtn.classList.add('active');
            orBtn.classList.remove('active');
        }
    }

    // Translate tagged contents
    document.querySelectorAll('[data-en][data-or]').forEach(el => {
        const text = el.getAttribute(`data-${lang}`);
        if (text) {
            el.textContent = text;
        }
    });

    document.querySelectorAll('[data-en-placeholder][data-or-placeholder]').forEach(el => {
        const placeholder = el.getAttribute(`data-${lang}-placeholder`);
        if (placeholder) {
            el.setAttribute('placeholder', placeholder);
        }
    });
}

// Helper to get authorization headers
function getAdminHeaders() {
    const password = sessionStorage.getItem('ramjaa_admin_password') || 'admin_ramjaa';
    return {
        'Authorization': password
    };
}

// Check Admin Authentication Status
async function checkAdminLogin() {
    const isLogged = sessionStorage.getItem('ramjaa_admin_logged') === 'true';
    const loginCard = document.getElementById('admin-login-card');
    const dashboard = document.getElementById('admin-dashboard');

    if (isLogged) {
        if (loginCard) loginCard.style.display = 'none';
        if (dashboard) dashboard.style.display = 'block';
        
        // Fetch notice and gallery data before rendering
        try {
            const noticesRes = await fetch('../../api/notices');
            if (noticesRes.ok) {
                appState.notices = await noticesRes.json();
            }
            const galleryRes = await fetch('../../api/gallery');
            if (galleryRes.ok) {
                appState.gallery = await galleryRes.json();
            }
        } catch (e) {
            console.error('Failed to load notices/gallery:', e);
        }
        
        renderAdminDashboard();
    } else {
        if (loginCard) loginCard.style.display = 'block';
        if (dashboard) dashboard.style.display = 'none';
    }
}

// Render the entire Admin Dashboard data based on selected tab
function renderAdminDashboard() {
    // Render Admin Notices Table
    renderAdminNotices();

    // Render Admin Gallery Table
    renderAdminGallery();

    // Fetch and Render Admin Alumni Roster Table
    fetchAdminRoster();
}

// ==========================================
// 1. NOTICE MANAGEMENT IN ADMIN
// ==========================================
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
    fetch(`../../api/notices/${id}`, {
        method: 'DELETE',
        headers: getAdminHeaders()
    })
    .then(res => {
        if (!res.ok) throw new Error('Delete failed');
        return res.json();
    })
    .then(data => {
        window.appState.notices = window.appState.notices.filter(n => n.id !== id);
        renderAdminNotices();
        window.showToast(window.appState.currentLanguage === 'or' ? "ବିଜ୍ଞପ୍ତି ଡିଲିଟ୍ ହେଲା" : "Notice deleted successfully", "success");
    })
    .catch(err => {
        console.error(err);
        window.showToast("Failed to delete notice", "error");
    });
}

function handleAddNotice(e) {
    e.preventDefault();

    const title = document.getElementById('an-title').value.trim();
    const category = document.getElementById('an-category').value;
    const desc = document.getElementById('an-desc').value.trim();

    fetch('../../api/notices', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...getAdminHeaders()
        },
        body: JSON.stringify({ title, category, desc })
    })
    .then(res => {
        if (!res.ok) throw new Error('Create notice failed');
        return res.json();
    })
    .then(newNotice => {
        window.appState.notices.push(newNotice);
        document.getElementById('admin-add-notice-form').reset();
        renderAdminNotices();
        window.showToast(window.appState.currentLanguage === 'or' ? "ବିଜ୍ଞପ୍ତି ସଫଳତାର ସହ ପ୍ରକାଶିତ ହେଲା!" : "Notice published successfully!", "success");
    })
    .catch(err => {
        console.error(err);
        window.showToast("Failed to publish notice", "error");
    });
}

// ==========================================
// 2. GALLERY MANAGEMENT IN ADMIN
// ==========================================
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
            <td><img src="${item.path}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px; border: 1px solid var(--border-color);" onerror="this.onerror=null; this.src='../../1.jpeg';"></td>
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
    fetch(`../../api/gallery/${id}`, {
        method: 'DELETE',
        headers: getAdminHeaders()
    })
    .then(res => {
        if (!res.ok) throw new Error('Delete gallery item failed');
        return res.json();
    })
    .then(data => {
        window.appState.gallery = window.appState.gallery.filter(g => g.id !== id);
        renderAdminGallery();
        window.showToast(window.appState.currentLanguage === 'or' ? "ଫଟୋ ଗ୍ୟାଲେରୀରୁ ହଟାଗଲା" : "Photo removed from gallery", "success");
    })
    .catch(err => {
        console.error(err);
        window.showToast("Failed to remove photo from gallery", "error");
    });
}

function handleAddGallery(e) {
    e.preventDefault();

    const caption = document.getElementById('ag-title').value.trim();
    const category = document.getElementById('ag-category').value;
    const photoInput = document.getElementById('ag-photo');

    if (!photoInput.files || !photoInput.files[0]) {
        window.showToast("Please select a file first", "error");
        return;
    }

    const formData = new FormData();
    formData.append('caption', caption);
    formData.append('category', category);
    formData.append('photo', photoInput.files[0]);

    // Submit loading state
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = "Uploading...";

    fetch('../../api/gallery', {
        method: 'POST',
        headers: getAdminHeaders(),
        body: formData
    })
    .then(res => {
        if (!res.ok) throw new Error('Upload photo failed');
        return res.json();
    })
    .then(newItem => {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;

        window.appState.gallery.push(newItem);
        document.getElementById('admin-add-gallery-form').reset();
        document.getElementById('ag-photo-preview').style.display = 'none';
        
        renderAdminGallery();
        window.showToast(window.appState.currentLanguage === 'or' ? "ଫଟୋ ଗ୍ୟାଲେରୀରେ ସଫଳତାର ସହ ଯୋଡ଼ାଗଲା!" : "Photo added to gallery successfully!", "success");
    })
    .catch(err => {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
        console.error(err);
        window.showToast("Failed to add photo to gallery", "error");
    });
}

// ==========================================
// 3. ROSTER MANAGEMENT IN ADMIN
// ==========================================
async function fetchAdminRoster() {
    try {
        const res = await fetch('../../api/alumni', {
            headers: getAdminHeaders()
        });
        if (res.ok) {
            window.appState.alumni = await res.json();
            renderAdminRoster();
            populateAdminRosterBatches();
        } else {
            window.showToast("Failed to fetch alumni roster", "error");
        }
    } catch (err) {
        console.error('Error fetching roster:', err);
    }
}

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
                              
        const matchesBatch = filterBatch === '' || member.batch.toString() === filterBatch.toString();

        return matchesSearch && matchesBatch;
    });

    if (filtered.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="8" class="text-center" style="color: var(--text-muted);">${window.appState.currentLanguage === 'or' ? "କୌଣସି ଛାତ୍ରଛାତ୍ରୀ ମିଳିଲେ ନାହିଁ।" : "No registered alumni found matching filters."}</td></tr>`;
        return;
    }

    filtered.forEach(member => {
        const row = document.createElement('tr');

        // Status Badge styling
        const isPending = member.status === 'pending';
        const statusBadge = isPending ? 
            `<span class="notice-category urgent" style="padding: 4px 8px; font-size: 0.75rem; border-radius: 4px; display: inline-block;">${window.appState.currentLanguage === 'or' ? "ଅପେକ୍ଷା" : "Pending"}</span>` :
            `<span class="notice-category academic" style="padding: 4px 8px; font-size: 0.75rem; border-radius: 4px; display: inline-block; background-color: #2ec4b6;">${window.appState.currentLanguage === 'or' ? "ଅନୁମୋଦିତ" : "Approved"}</span>`;

        // Action Buttons based on status
        let actionButtons = '';
        if (isPending) {
            actionButtons = `
                <button class="action-badge edit approve-btn" data-id="${member.id}" style="background-color: #2ec4b6; color: white; border: none; margin-right: 5px; cursor: pointer;">${window.appState.currentLanguage === 'or' ? "ଅନୁମୋଦନ" : "Approve"}</button>
                <button class="action-badge delete delete-btn" data-id="${member.id}">${window.appState.currentLanguage === 'or' ? "ଡିଲିଟ୍" : "Delete"}</button>
            `;
        } else {
            // Include Direct dynamic PDF print download link
            actionButtons = `
                <a href="../../api/alumni/${member.id}/pdf" target="_blank" class="action-badge edit download-pdf-btn" style="background-color: #0f3057; color: white; border: none; text-decoration: none; display: inline-block; text-align: center; margin-right: 5px;">${window.appState.currentLanguage === 'or' ? "PDF ଡାଉନଲୋଡ଼" : "PDF"}</a>
                <button class="action-badge delete delete-btn" data-id="${member.id}">${window.appState.currentLanguage === 'or' ? "ଡିଲିଟ୍" : "Delete"}</button>
            `;
        }

        row.innerHTML = `
            <td><img src="${member.photo}" class="admin-avatar" alt="${member.name}" onerror="this.onerror=null; this.src='../../1.jpeg';"></td>
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
            <td>${statusBadge}</td>
            <td>${actionButtons}</td>
        `;

        // Bind delete action
        row.querySelector('.delete-btn').addEventListener('click', () => {
            if (confirm(window.appState.currentLanguage === 'or' ? `ଆପଣ ${member.name} ଙ୍କ ପଞ୍ଜୀକରଣ ରଦ୍ଦ କରିବାକୁ ଚାହାଁନ୍ତି କି?` : `Are you sure you want to delete registration for ${member.name}?`)) {
                deleteAlumni(member.id);
            }
        });

        // Bind approve action
        if (isPending) {
            row.querySelector('.approve-btn').addEventListener('click', (e) => {
                approveAlumni(member.id, e.target);
            });
        }

        tableBody.appendChild(row);
    });
}

function approveAlumni(id, button) {
    button.disabled = true;
    button.textContent = window.appState.currentLanguage === 'or' ? "ଅնୁମୋଦନ ହେଉଛି..." : "Approving...";

    fetch(`../../api/alumni/${id}/approve`, {
        method: 'POST',
        headers: getAdminHeaders()
    })
    .then(res => {
        if (!res.ok) throw new Error('Approval process failed');
        return res.json();
    })
    .then(data => {
        window.showToast(window.appState.currentLanguage === 'or' ? "ପଞ୍ଜୀକରଣ ସଫଳତାର ସହ ଅନୁମୋଦିତ ହେଲା ଏବଂ ଇମେଲ୍ ପଠାଗଲା!" : "Alumni approved successfully and email sent!", "success");
        fetchAdminRoster();
    })
    .catch(err => {
        button.disabled = false;
        button.textContent = window.appState.currentLanguage === 'or' ? "ଅନୁମୋଦନ" : "Approve";
        console.error(err);
        window.showToast("Failed to approve alumnus", "error");
    });
}

function deleteAlumni(id) {
    fetch(`../../api/alumni/${id}`, {
        method: 'DELETE',
        headers: getAdminHeaders()
    })
    .then(res => {
        if (!res.ok) throw new Error('Delete registration failed');
        return res.json();
    })
    .then(data => {
        window.appState.alumni = window.appState.alumni.filter(a => a.id !== id);
        renderAdminRoster();
        populateAdminRosterBatches();
        
        // Update count stat on home page
        const counter = document.getElementById('stat-alumni-count');
        if (counter) {
            fetch('../../api/alumni/count')
            .then(res => res.json())
            .then(countData => {
                counter.textContent = `${countData.count}+`;
            })
            .catch(err => console.error(err));
        }

        window.showToast(window.appState.currentLanguage === 'or' ? "ପଞ୍ଜୀକରଣ ଡିଲିଟ୍ ହେଲା" : "Alumni registration deleted", "success");
    })
    .catch(err => {
        console.error(err);
        window.showToast("Failed to delete alumnus registration", "error");
    });
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
    if (batches.includes(parseInt(currentSelVal)) || batches.includes(currentSelVal)) {
        dropdown.value = currentSelVal;
    }
}

// ==========================================
// 4. CSV & JSON EXPORTERS
// ==========================================
function exportRosterCSV() {
    if (window.appState.alumni.length === 0) {
        window.showToast("No alumni data to export", "error");
        return;
    }

    // CSV header columns
    const headers = ["MemberID", "Name", "BatchYear", "Mobile", "Email", "Profession", "Location", "Status", "Memories"];
    
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
            a.status,
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

// ==========================================
// 5. EVENT LISTENERS INITIALIZATION FOR ADMIN
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    
    // Admin Login form submit
    const loginForm = document.getElementById('admin-login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const passVal = document.getElementById('admin-pass').value;
            
            // Validate via a quick request to see if password works
            fetch('../../api/admin/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: passVal })
            })
            .then(res => {
                if (res.ok) {
                    sessionStorage.setItem('ramjaa_admin_logged', 'true');
                    sessionStorage.setItem('ramjaa_admin_password', passVal);
                    document.getElementById('admin-pass').value = '';
                    checkAdminLogin();
                    window.showToast(window.appState.currentLanguage === 'or' ? "ଲଗ୍-ଇନ୍ ସଫଳ ହେଲା!" : "Login successful!", "success");
                } else {
                    window.showToast(window.appState.currentLanguage === 'or' ? "ଭୁଲ୍ ପାସୱାର୍ଡ!" : "Invalid admin password!", "error");
                }
            })
            .catch(err => {
                console.error(err);
                window.showToast("Server connection error", "error");
            });
        });
    }

    // Admin Logout button
    const logoutBtn = document.getElementById('admin-logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            sessionStorage.removeItem('ramjaa_admin_logged');
            sessionStorage.removeItem('ramjaa_admin_password');
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

    // Language switcher buttons listeners
    const orBtn = document.getElementById('lang-or-btn');
    const enBtn = document.getElementById('lang-en-btn');
    if (orBtn) {
        orBtn.addEventListener('click', () => {
            translateAdminPage('or');
        });
    }
    if (enBtn) {
        enBtn.addEventListener('click', () => {
            translateAdminPage('en');
        });
    }

    // Translate page to initial language on load
    translateAdminPage(appState.currentLanguage);
    
    // Check login state
    checkAdminLogin();
});

// Attach helper functions to window for SPA routers
window.checkAdminLogin = checkAdminLogin;
window.renderAdminDashboard = renderAdminDashboard;
