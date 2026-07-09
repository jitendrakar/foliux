// RAMJAA Web Application Core Logic
// Handle client-side routing, English/Odia translations, public board views, and local storage operations.

// Localization Content Map
const LOCALIZATION = {
    // English content mapping
    en: {
        aboutText: `
            <h3>RAMJAA (Radha Mohan Jew Alumni Association)</h3>
            <h4>Radha Mohan Jew High School, Sindhia Alumni Organization</h4>
            <blockquote style="font-style: italic; border-left: 4px solid var(--secondary); padding-left: 15px; margin: 15px 0; color: var(--primary-light); font-weight: 600;">
                "Our School – Our Pride, Our Identity, Our Responsibility."
            </blockquote>
            <p>
                RAMJAA is not just an organization; it is a symbol of emotions, memories, and responsibilities of every alumnus connected with Radha Mohan Jew High School, Sindhia. The purpose of this association is to safeguard the glorious tradition of the school, cooperate with current students, and build an ideal educational environment for the coming generations.
            </p>
            <p>
                Radha Mohan Jew High School was established in 1966 and is recognized as a leading government co-educational institution in Balasore district. Countless students who completed their education here are now working successfully across various fields in India and abroad. Reconnecting them to their school and strengthening their sense of responsibility toward society is the core objective of RAMJAA.
            </p>
            <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 25px 0;">
            <h3 style="margin-bottom: 12px; color: var(--primary);">Diamond Jubilee – A Historical Chapter</h3>
            <p>
                The Diamond Jubilee of Radha Mohan Jew High School is not just a celebration; it is a symbol of the school's glorious history, the teachers' invaluable contribution, the success of the alumni, and a new resolution for the future. On this occasion, RAMJAA has undertaken several long-term development plans for the school.
            </p>
            <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 25px 0;">
            <h3 style="margin-bottom: 12px; color: var(--primary);">Let us all unite!</h3>
            <p>
                The foundation of where we stand today is our school. This debt can never be fully repaid, but through our cooperation, time, experience, and support, we can definitely contribute to its growth.
            </p>
            <p style="font-weight: 700; color: var(--primary-light);">
                Come, connect with RAMJAA. Let your experience, time, and cooperation build the foundation for the bright future of our school.
            </p>
            <h4 style="color: var(--secondary-dark); margin-top: 10px; font-weight: 800;">
                "The school made us – now it is our time to build its future."
            </h4>
        `,
        vision: "To transform Radha Mohan Jew High School into a modern, eco-friendly, technology-rich, and value-based educational institution that is recognized as one of the model schools in Odisha.",
        missionList: `
            <li>Bring all alumni together on a common platform.</li>
            <li>Cooperate in the improvement of school infrastructure.</li>
            <li>Support meritorious and financially underprivileged students.</li>
            <li>Promote digital education, smart classrooms, library, and science education.</li>
            <li>Organize career guidance, personality development, and competitive exam preparation programs.</li>
            <li>Preserve the heritage, tradition, and culture of the school.</li>
        `,
        activities: [
            {
                title: "Educational Field",
                items: ["Honoring meritorious students", "Career counseling seminars", "Competitive exam guidance", "Book and stationery distribution"]
            },
            {
                title: "School Development",
                items: ["Classroom renovations", "Providing benches, desks and furniture", "Campus and auditorium beautification", "Tree plantation and green environment creation"]
            },
            {
                title: "Social Service",
                items: ["Blood donation camps", "Health awareness programs", "Environmental protection campaigns", "Campus cleanliness drives"]
            }
        ],
        values: [
            { name: "Service", desc: "Developing the school is our foremost duty." },
            { name: "Unity", desc: "Every alumnus is a member of our family." },
            { name: "Transparency", desc: "Accountability and transparency in all financial matters." },
            { name: "Dedication", desc: "Unwavering commitment to the progress of our school." }
        ]
    },
    // Odia content mapping
    or: {
        aboutText: `
            <h3>ରାମଜା (RAMJAA)</h3>
            <h4>ରାଧା ମୋହନ ଜ୍ୟୁ ହାଇ ସ୍କୁଲ, ସିନ୍ଧିଆର ପୂର୍ବତନ ଛାତ୍ରଛାତ୍ରୀଙ୍କ ସଂଗଠନ</h4>
            <blockquote style="font-style: italic; border-left: 4px solid var(--secondary); padding-left: 15px; margin: 15px 0; color: var(--primary-light); font-weight: 600;">
                "ଆମ ବିଦ୍ୟାଳୟ – ଆମର ଗର୍ବ, ଆମର ପରିଚୟ, ଆମର ଦାୟିତ୍ୱ।"
            </blockquote>
            <p>
                ରାମଜା (RAMJAA) କେବଳ ଏକ ସଂଗଠନ ନୁହେଁ, ଏହା ରାଧା ମୋହନ ଜ୍ୟୁ ହାଇ ସ୍କୁଲ, ସିନ୍ଧିଆ ସହ ଜଡିତ ପ୍ରତ୍ୟେକ ପୂର୍ବତନ ଛାତ୍ରଛାତ୍ରୀଙ୍କ ଭାବନା, ସ୍ମୃତି ଓ ଦାୟିତ୍ୱର ପ୍ରତୀକ। ଏହି ସଂଗଠନ ଗଠନର ଉଦ୍ଦେଶ୍ୟ ହେଉଛି ବିଦ୍ୟାଳୟର ଗୌରବମୟ ପରମ୍ପରାକୁ ସୁରକ୍ଷିତ ରଖିବା, ବର୍ତ୍ତମାନର ଛାତ୍ରଛାତ୍ରୀଙ୍କୁ ସହଯୋଗ କରିବା ଏବଂ ଆଗାମୀ ପିଢ଼ି ପାଇଁ ଏକ ଆଦର୍ଶ ଶିକ୍ଷା ପରିବେଶ ସୃଷ୍ଟି କରିବା।
            </p>
            <p>
                ରାଧା ମୋହନ ଜ୍ୟୁ ହାଇ ସ୍କୁଲ ୧୯୬୬ ମସିହାରେ ସ୍ଥାପିତ ହୋଇ ବାଲେଶ୍ୱର ଜିଲ୍ଲାର ଏକ ଅଗ୍ରଣୀ ସରକାରୀ ସହ-ଶିକ୍ଷା ଅନୁଷ୍ଠାନ ଭାବେ ପରିଚିତ। ଏହି ବିଦ୍ୟାଳୟରୁ ଶିକ୍ଷା ଗ୍ରହଣ କରି ଅନେକ ଛାତ୍ରଛାତ୍ରୀ ଦେଶ ଓ ବିଦେଶରେ ବିଭିନ୍ନ କ୍ଷେତ୍ରରେ ସଫଳତାର ସହ କାର୍ଯ୍ୟ କରୁଛନ୍ତି। ସେମାନଙ୍କୁ ପୁଣିଥରେ ନିଜ ବିଦ୍ୟାଳୟ ସହ ଯୋଡ଼ିବା ଏବଂ ସମାଜ ପ୍ରତି ସେମାନଙ୍କର ଦାୟିତ୍ୱବୋଧକୁ ସୁଦୃଢ଼ କରିବା ହେଉଛି ରାମଜାର ମୂଳ ଉଦ୍ଦେଶ୍ୟ।
            </p>
            <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 25px 0;">
            <h3 style="margin-bottom: 12px; color: var(--primary);">ଡାଇମଣ୍ଡ ଜୁବିଲି – ଏକ ଐତିହାସିକ ଅଧ୍ୟାୟ</h3>
            <p>
                ରାଧା ମୋହନ ଜ୍ୟୁ ହାଇ ସ୍କୁଲର ଡାଇମଣ୍ଡ ଜୁବିଲି କେବଳ ଏକ ଉତ୍ସବ ନୁହେଁ, ଏହା ବିଦ୍ୟାଳୟର ଗୌରବମୟ ଇତିହାସ, ଶିକ୍ଷକମାନଙ୍କ ଅବଦାନ, ପୂର୍ବତନ ଛାତ୍ରଛାତ୍ରୀଙ୍କ ସଫଳତା ଏବଂ ଭବିଷ୍ୟତ ପାଇଁ ଏକ ନୂତନ ସଙ୍କଳ୍ପର ପ୍ରତୀକ। ଏହି ଅବସରରେ ରାମଜା ବିଦ୍ୟାଳୟର ଦୀର୍ଘମିଆଦି ବିକାଶ ପାଇଁ ଅନେକ ଯୋଜନା ହାତକୁ ନେଇଛି।
            </p>
            <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 25px 0;">
            <h3 style="margin-bottom: 12px; color: var(--primary);">ଆସନ୍ତୁ, ଆମେ ସମସ୍ତେ ମିଶିବା</h3>
            <p>
                ଆଜି ଆମେ ଯେଉଁ ସ୍ଥାନରେ ଅଛୁ, ତାହାର ମୂଳଦୁଆର ହେଉଛି ଆମ ବିଦ୍ୟାଳୟ। ଏହି ଋଣ କେବେ ଶୋଧ ହୋଇପାରିବ ନାହିଁ, କିନ୍ତୁ ଆମର ସହଯୋଗ, ସମୟ, ଅନୁଭବ ଓ ସମର୍ଥନ ମାଧ୍ୟମରେ ଆମେ ଏହାର ଉନ୍ନତିରେ ନିଶ୍ଚିତ ଭାବେ ଅବଦାନ ରଖିପାରିବା।
            </p>
            <p style="font-weight: 700; color: var(--primary-light);">
                ଆସନ୍ତୁ, ରାମଜା ସହ ଯୋଡ଼ନ୍ତୁ। ଆପଣଙ୍କ ଅନୁଭବ, ଆପଣଙ୍କ ସମୟ ଓ ଆପଣଙ୍କ ସହଯୋଗ ହେଉ ଆମ ବିଦ୍ୟାଳୟର ଉଜ୍ଜ୍ୱଳ ଭବିଷ୍ୟତର ଭିତ୍ତି।
            </p>
            <h4 style="color: var(--secondary-dark); margin-top: 10px; font-weight: 800;">
                "ବିଦ୍ୟାଳୟ ଆମକୁ ଗଢ଼ିଛି – ଏବେ ତାହାର ଭବିଷ୍ୟତ ଗଢ଼ିବାର ସମୟ ଆମର।"
            </h4>
        `,
        vision: "ରାଧା ମୋହନ ଜ୍ୟୁ ହାଇ ସ୍କୁଲକୁ ଏକ ଆଧୁନିକ, ପରିବେଶବନ୍ଧବ, ପ୍ରଯୁକ୍ତି-ସମୃଦ୍ଧ ଏବଂ ମୂଲ୍ୟବୋଧ ଭିତ୍ତିକ ଶିକ୍ଷାନୁଷ୍ଠାନରେ ପରିଣତ କରିବା, ଯାହା ଓଡ଼ିଶାର ଅନ୍ୟତମ ଆଦର୍ଶ ବିଦ୍ୟାଳୟ ଭାବେ ପରିଚିତ ହେବ।",
        missionList: `
            <li>ପୂର୍ବତନ ଛାତ୍ରଛାତ୍ରୀଙ୍କୁ ଏକ ସାଧାରଣ ମଞ୍ଚରେ ଏକତ୍ର କରିବା।</li>
            <li>비ଦ୍ୟାଳୟର ଭିତ୍ତିଭୂମିର ଉନ୍ନତିରେ ସହଯୋଗ କରିବା।</li>
            <li>ମେଧାବୀ ଏବଂ ଆର୍ଥିକ ଭାବେ ଦୁର୍ବଳ ଛାତ୍ରଛାତ୍ରୀଙ୍କୁ ସହାୟତା କରିବା।</li>
            <li>ଡିଜିଟାଲ ଶିକ୍ଷା, ସ୍ମାର୍ଟ କ୍ଲାସରୁମ୍, ପୁସ୍ତକାଳୟ ଓ ବିଜ୍ଞାନ ଶିକ୍ଷାକୁ ପ୍ରୋତ୍ସାହନ ଦେବା।</li>
            <li>କ୍ୟାରିୟର ମାର୍ଗଦର୍ଶନ, ବ୍ୟକ୍ତିତ୍ୱ ବିକାଶ ଓ ପ୍ରତିଯୋଗିତାମୂଳକ ପରୀକ୍ଷା ପାଇଁ ବିଶେଷ କାର୍ଯ୍ୟକ୍ରମ ଆୟୋଜନ କରିବା।</li>
            <li>비ଦ୍ୟାଳୟର ଐତିହ୍ୟ, ପରମ୍ପରା ଓ ସଂସ୍କୃତିକୁ ସଂରକ୍ଷଣ କରିବା।</li>
        `,
        activities: [
            {
                title: "ଶିକ୍ଷା କ୍ଷେତ୍ରରେ",
                items: ["ମେଧାବୀ ଛାତ୍ରଛାତ୍ରୀଙ୍କୁ ସମ୍ମାନ", "କ୍ୟାରିୟର କାଉନସେଲିଂ ଶିବିର", "ପ୍ରତିଯୋଗିତାମୂଳକ ପରୀକ୍ଷା ପାଇଁ ମାର୍ଗଦର୍ଶନ", "ପୁସ୍ତକ ଓ ଶିକ୍ଷା ସାମଗ୍ରୀ ବଣ୍ଟନ"]
            },
            {
                title: "ବିଦ୍ୟାଳୟର ଉନ୍ନତି",
                items: ["ଶ୍ରେଣୀଗୃହର ନବୀକରଣ", "ଚେୟାର, ଡେସ୍କ, ବେଞ୍ଚ ଓ ଅନ୍ୟାନ୍ୟ ଆସବାବପତ୍ର ପ୍ରଦାନ", "ସଭାଗୃହ ଓ କ୍ୟାମ୍ପସର ସୌନ୍ଦର୍ଯ୍ୟକରଣ", "ବୃକ୍ଷରୋପଣ ଓ ସବୁଜ ପରିବେଶ ସୃଷ୍ଟି"]
            },
            {
                title: "ସମାଜସେବା",
                items: ["ରକ୍ତଦାନ ଶିବିର", "ସ୍ୱାସ୍ଥ୍ୟ ସଚେତନତା କାର୍ଯ୍ୟକ୍ରମ", "ପରିବେଶ ସୁରକ୍ଷା ଅଭିଯାନ", "ସ୍ୱଚ୍ଛତା କାର୍ଯ୍ୟକ୍ରମ"]
            }
        ],
        values: [
            { name: "ସେବା", desc: "ବିଦ୍ୟାଳୟର ଉନ୍ନତି ହେଉଛି ଆମର ପ୍ରଥମ କର୍ତ୍ତବ୍ୟ।" },
            { name: "ଏକତା", desc: "ପ୍ରତ୍ୟେକ ପୂର୍ବତନ ଛାତ୍ରଛାତ୍ରୀ ଆମର ପରିବାରର ସଦସ୍ୟ।" },
            { name: "ସ୍ୱଚ୍ଛତା", desc: "ସମସ୍ତ କାର୍ଯ୍ୟ ଓ ଆର୍ଥିକ ପରିଚାଳନାରେ ସ୍ୱଚ୍ଛତା ଓ ଜବାବଦେହିତା।" },
            { name: "ସମର୍ପଣ", desc: "ବିଦ୍ୟାଳୟର ଉନ୍ନତି ପାଇଁ ନିରନ୍ତର ପ୍ରୟାସ।" }
        ]
    }
};

// Global Application State
let appState = {
    currentLanguage: localStorage.getItem('ramjaa_lang') || 'or',
    notices: [],
    gallery: [],
    alumni: [],
    activeNoticeFilter: 'all',
    activeGalleryFilter: 'all',
    sliderInterval: null
};

// ==========================================
// SEED DEFAULT DATABASE (LOCAL STORAGE)
// ==========================================
function initDatabase() {
    loadDataFromServer();
}

async function loadDataFromServer() {
    try {
        const noticesRes = await fetch('api/notices');
        if (noticesRes.ok) {
            appState.notices = await noticesRes.json();
        }
        const galleryRes = await fetch('api/gallery');
        if (galleryRes.ok) {
            appState.gallery = await galleryRes.json();
        }
        
        // Update stats
        const countStat = document.getElementById('stat-alumni-count');
        if (countStat) {
            const countRes = await fetch('api/alumni/count');
            if (countRes.ok) {
                const countData = await countRes.json();
                countStat.textContent = `${countData.count}+`;
            }
        }
        
        // Refresh display
        if (document.getElementById('home-view').classList.contains('active')) {
            renderHomeNotices();
            startGallerySlider();
        } else if (document.getElementById('notices-view').classList.contains('active')) {
            renderNoticesPage();
        } else if (document.getElementById('gallery-view').classList.contains('active')) {
            renderGalleryPage();
        }
    } catch (err) {
        console.error('Error loading data from server:', err);
    }
}

// ==========================================
// CLIENT-SIDE ROUTER
// ==========================================
function handleRouting() {
    const rawHash = window.location.hash || '#/home';
    const cleanHash = rawHash.replace(/^#/, '');
    
    // Deactivate all views and nav items
    document.querySelectorAll('.page-view').forEach(view => view.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    
    // Close mobile nav menu
    document.getElementById('nav-menu').classList.remove('open');

    // Route matching
    let targetViewId = 'home-view';
    let targetLinkId = 'link-home';

    if (cleanHash.startsWith('/about')) {
        targetViewId = 'about-view';
        targetLinkId = 'link-about';
    } else if (cleanHash.startsWith('/notices')) {
        targetViewId = 'notices-view';
        targetLinkId = 'link-notices';
        renderNoticesPage();
    } else if (cleanHash.startsWith('/gallery')) {
        targetViewId = 'gallery-view';
        targetLinkId = 'link-gallery';
        renderGalleryPage();
    } else if (cleanHash.startsWith('/register')) {
        targetViewId = 'register-view';
        targetLinkId = 'link-register';
    } else if (cleanHash.startsWith('/admin')) {
        targetViewId = 'admin-view';
        targetLinkId = 'link-admin';
        // Admin layout rendering is handled by admin.js
        if (typeof window.checkAdminLogin === 'function') {
            window.checkAdminLogin();
        }
    }

    // Activate the view and matching link
    const targetView = document.getElementById(targetViewId);
    if (targetView) targetView.classList.add('active');
    
    const targetLink = document.getElementById(targetLinkId);
    if (targetLink) targetLink.classList.add('active');

    // Special view triggers
    if (targetViewId === 'home-view') {
        renderHomeNotices();
        startGallerySlider();
    } else {
        stopGallerySlider();
    }

    if (targetViewId === 'about-view') {
        renderAboutPageDynamic();
    }

    window.scrollTo(0, 0);
}

// ==========================================
// TRANSLATION AND LOCALIZATION ENGINE
// ==========================================
function setLanguage(lang) {
    appState.currentLanguage = lang;
    localStorage.setItem('ramjaa_lang', lang);
    document.documentElement.setAttribute('lang', lang);

    // Toggle active classes on language buttons
    if (lang === 'or') {
        document.getElementById('lang-or-btn').classList.add('active');
        document.getElementById('lang-en-btn').classList.remove('active');
    } else {
        document.getElementById('lang-en-btn').classList.add('active');
        document.getElementById('lang-or-btn').classList.remove('active');
    }

    // Translate all standard text elements with data tags
    document.querySelectorAll('[data-en][data-or]').forEach(el => {
        const text = el.getAttribute(`data-${lang}`);
        if (text) {
            el.textContent = text;
        }
    });

    // Translate placeholder attributes
    document.querySelectorAll('[data-en-placeholder][data-or-placeholder]').forEach(el => {
        const placeholder = el.getAttribute(`data-${lang}-placeholder`);
        if (placeholder) {
            el.setAttribute('placeholder', placeholder);
        }
    });

    // Refresh dynamic content for active pages
    if (document.getElementById('home-view').classList.contains('active')) {
        renderHomeNotices();
    } else if (document.getElementById('about-view').classList.contains('active')) {
        renderAboutPageDynamic();
    } else if (document.getElementById('notices-view').classList.contains('active')) {
        renderNoticesPage();
    } else if (document.getElementById('gallery-view').classList.contains('active')) {
        renderGalleryPage();
    }

    // Rerender admin if active and initialized
    const adminView = document.getElementById('admin-view');
    if (adminView && adminView.classList.contains('active') && typeof window.renderAdminDashboard === 'function') {
        window.renderAdminDashboard();
    }

    showToast(lang === 'or' ? "ଭାଷା ବଦଳାଗଲା: ଓଡ଼ିଆ" : "Language switched to: English", "success");
}

// Render dynamic sections of the About Us page
function renderAboutPageDynamic() {
    const lang = appState.currentLanguage;
    const content = LOCALIZATION[lang];

    // Main description body
    document.getElementById('about-content-body').innerHTML = content.aboutText;

    // Vision
    document.getElementById('vision-text-body').textContent = content.vision;

    // Mission Bullet list
    document.getElementById('mission-list-body').innerHTML = content.missionList;

    // Activities Columns
    const activitiesContainer = document.getElementById('activities-body');
    activitiesContainer.innerHTML = '';
    content.activities.forEach(activity => {
        const card = document.createElement('div');
        card.className = 'activity-card';
        
        let listItemsHtml = '';
        activity.items.forEach(item => {
            listItemsHtml += `<li>${item}</li>`;
        });

        card.innerHTML = `
            <h3>${activity.title}</h3>
            <ul>${listItemsHtml}</ul>
        `;
        activitiesContainer.appendChild(card);
    });

    // Core Values Grid
    const valuesContainer = document.getElementById('values-body');
    valuesContainer.innerHTML = '';
    content.values.forEach(val => {
        const valBox = document.createElement('div');
        valBox.className = 'value-item';
        valBox.innerHTML = `
            <h3>${val.name}</h3>
            <p>${val.desc}</p>
        `;
        valuesContainer.appendChild(valBox);
    });
}

// ==========================================
// PUBLIC HOME VIEW CONTROLLERS
// ==========================================
function renderHomeNotices() {
    const feed = document.getElementById('mini-notice-feed');
    feed.innerHTML = '';

    // Take top 3 latest notices (sort by date descending)
    const sorted = [...appState.notices].sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 3);
    
    if (sorted.length === 0) {
        feed.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;" data-en="No notices published yet." data-or="କୌଣସି ବିଜ୍ଞପ୍ତି ପ୍ରକାଶିତ ହୋଇନାହିଁ।">${appState.currentLanguage === 'or' ? "କୌଣସି ବିଜ୍ଞପ୍ତି ପ୍ରକାଶିତ ହୋଇନାହିଁ।" : "No notices published yet."}</p>`;
        return;
    }

    sorted.forEach(notice => {
        const block = document.createElement('a');
        block.href = `#/notices`;
        block.className = 'mini-notice';
        block.style.textDecoration = 'none';
        block.style.display = 'block';

        const title = appState.currentLanguage === 'or' ? notice.title_or : notice.title_en;
        const dateObj = new Date(notice.date);
        const formattedDate = dateObj.toLocaleDateString(appState.currentLanguage === 'or' ? 'or-IN' : 'en-US', {
            year: 'numeric', month: 'short', day: 'numeric'
        });

        block.innerHTML = `
            <h4>${title}</h4>
            <span>${formattedDate}</span>
        `;
        block.addEventListener('click', (e) => {
            // Prevent going to route immediately, open details modal instead
            e.preventDefault();
            openNoticeModal(notice);
        });

        feed.appendChild(block);
    });
}

// Automate slide transitions on Home view
function startGallerySlider() {
    stopGallerySlider();
    const sliderContainer = document.getElementById('gallery-slider');
    if (!sliderContainer) return;

    sliderContainer.innerHTML = '';
    const slides = appState.gallery.slice(0, 4); // Limit to top 4 for slider
    
    if (slides.length === 0) return;

    slides.forEach((item, index) => {
        const slide = document.createElement('div');
        slide.className = `showcase-slide ${index === 0 ? 'active' : ''}`;
        slide.style.backgroundImage = `url('${item.path}')`;
        
        const caption = appState.currentLanguage === 'or' ? item.caption_or : item.caption_en;
        const catLabel = appState.currentLanguage === 'or' ? 'ଗ୍ୟାଲେରୀ' : 'Gallery';

        slide.innerHTML = `
            <div class="slide-caption">
                <h3>${caption}</h3>
                <p>${catLabel} | ${item.category}</p>
            </div>
        `;
        sliderContainer.appendChild(slide);
    });

    let currentSlide = 0;
    appState.sliderInterval = setInterval(() => {
        const activeSlides = sliderContainer.querySelectorAll('.showcase-slide');
        if (activeSlides.length <= 1) return;

        activeSlides[currentSlide].classList.remove('active');
        currentSlide = (currentSlide + 1) % activeSlides.length;
        activeSlides[currentSlide].classList.add('active');
    }, 4500);
}

function stopGallerySlider() {
    if (appState.sliderInterval) {
        clearInterval(appState.sliderInterval);
        appState.sliderInterval = null;
    }
}

// ==========================================
// PUBLIC NOTICE BOARD CONTROLLERS
// ==========================================
function renderNoticesPage() {
    const listContainer = document.getElementById('notice-list');
    listContainer.innerHTML = '';

    const searchTerm = document.getElementById('notice-search').value.toLowerCase();
    const activeCategory = appState.activeNoticeFilter;

    // Filter notices
    const filtered = appState.notices.filter(notice => {
        const title = (appState.currentLanguage === 'or' ? notice.title_or : notice.title_en).toLowerCase();
        const desc = (appState.currentLanguage === 'or' ? notice.desc_or : notice.desc_en).toLowerCase();
        
        const matchesSearch = title.includes(searchTerm) || desc.includes(searchTerm);
        const matchesCategory = activeCategory === 'all' || notice.category.toLowerCase() === activeCategory.toLowerCase();

        return matchesSearch && matchesCategory;
    });

    // Sort by date (descending)
    filtered.sort((a, b) => new Date(b.date) - new Date(a.date));

    if (filtered.length === 0) {
        listContainer.innerHTML = `
            <div class="text-center py-5" style="background: white; border-radius: var(--radius-md); box-shadow: var(--shadow-sm);">
                <p style="color: var(--text-muted); font-size: 1.1rem;">
                    ${appState.currentLanguage === 'or' ? "କୌଣସି ବିଜ୍ଞପ୍ତି ମିଳିଲା ନାହିଁ।" : "No notices match your criteria."}
                </p>
            </div>
        `;
        return;
    }

    filtered.forEach(notice => {
        const card = document.createElement('div');
        card.className = 'notice-box';
        
        const catClass = notice.category.toLowerCase() === 'urgent' ? 'urgent' : (notice.category.toLowerCase() === 'academic' ? 'academic' : 'event');
        const catLabel = appState.currentLanguage === 'or' ? 
            (notice.category === 'Urgent' ? 'ଜରୁରୀ' : (notice.category === 'Academic' ? 'ଶିକ୍ଷାଗତ' : 'କାର୍ଯ୍ୟକ୍ରମ')) : 
            notice.category;

        const dateObj = new Date(notice.date);
        const formattedDate = dateObj.toLocaleDateString(appState.currentLanguage === 'or' ? 'or-IN' : 'en-US', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        });

        const title = appState.currentLanguage === 'or' ? notice.title_or : notice.title_en;
        const desc = appState.currentLanguage === 'or' ? notice.desc_or : notice.desc_en;
        const shortDesc = desc.length > 180 ? desc.substring(0, 180) + '...' : desc;

        card.innerHTML = `
            <span class="notice-category ${catClass}">${catLabel}</span>
            <span class="notice-date">${formattedDate}</span>
            <h3 class="notice-title">${title}</h3>
            <p class="notice-desc">${shortDesc}</p>
            <a href="#" class="notice-link">
                <span data-en="Read Full Details" data-or="ବିସ୍ତୃତ ବିବରଣୀ ପଢ଼ନ୍ତୁ">Read Full Details</span>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
            </a>
        `;

        card.querySelector('.notice-link').addEventListener('click', (e) => {
            e.preventDefault();
            openNoticeModal(notice);
        });

        listContainer.appendChild(card);
    });
}

function openNoticeModal(notice) {
    const modal = document.getElementById('notice-modal');
    const category = document.getElementById('modal-notice-category');
    const date = document.getElementById('modal-notice-date');
    const title = document.getElementById('modal-notice-title');
    const content = document.getElementById('modal-notice-content');

    const catClass = notice.category.toLowerCase() === 'urgent' ? 'urgent' : (notice.category.toLowerCase() === 'academic' ? 'academic' : 'event');
    const catLabel = appState.currentLanguage === 'or' ? 
        (notice.category === 'Urgent' ? 'ଜରୁରୀ' : (notice.category === 'Academic' ? 'ଶିକ୍ଷାଗତ' : 'କାର୍ଯ୍ୟକ୍ରମ')) : 
        notice.category;

    const dateObj = new Date(notice.date);
    const formattedDate = dateObj.toLocaleDateString(appState.currentLanguage === 'or' ? 'or-IN' : 'en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });

    category.textContent = catLabel;
    category.className = `notice-category ${catClass}`;
    date.textContent = formattedDate;
    title.textContent = appState.currentLanguage === 'or' ? notice.title_or : notice.title_en;
    content.textContent = appState.currentLanguage === 'or' ? notice.desc_or : notice.desc_en;

    modal.style.display = 'flex';
    modal.classList.add('active');
}

// ==========================================
// PUBLIC PHOTO GALLERY CONTROLLERS
// ==========================================
function renderGalleryPage() {
    const grid = document.getElementById('gallery-grid');
    grid.innerHTML = '';

    const activeFilter = appState.activeGalleryFilter;
    const filtered = appState.gallery.filter(item => {
        return activeFilter === 'all' || item.category.toLowerCase() === activeFilter.toLowerCase();
    });

    if (filtered.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1 / -1;" class="text-center py-5">
                <p style="color: var(--text-muted); font-size: 1.1rem;">
                    ${appState.currentLanguage === 'or' ? "କୌଣସି ଫଟୋ ମିଳିଲା ନାହିଁ।" : "No images found in this category."}
                </p>
            </div>
        `;
        return;
    }

    filtered.forEach(item => {
        const card = document.createElement('div');
        card.className = 'gallery-item';
        
        const caption = appState.currentLanguage === 'or' ? item.caption_or : item.caption_en;
        const categoryLabel = appState.currentLanguage === 'or' ? 
            (item.category === 'Campus' ? 'କ୍ୟାମ୍ପସ' : (item.category === 'Alumni' ? 'ସମ୍ମିଳନୀ' : 'କାର୍ଯ୍ୟକ୍ରମ')) : 
            item.category;

        card.innerHTML = `
            <div class="gallery-img-wrapper">
                <img src="${item.path}" alt="${caption}">
                <div class="gallery-overlay">
                    <div class="gallery-zoom-icon">+</div>
                </div>
            </div>
            <div class="gallery-details">
                <h4>${caption}</h4>
                <span>${categoryLabel}</span>
            </div>
        `;

        card.addEventListener('click', () => {
            openLightbox(item);
        });

        grid.appendChild(card);
    });
}

function openLightbox(item) {
    const lightbox = document.getElementById('lightbox-modal');
    const img = document.getElementById('lightbox-img');
    const title = document.getElementById('lightbox-caption-title');
    const meta = document.getElementById('lightbox-caption-meta');

    img.src = item.path;
    title.textContent = appState.currentLanguage === 'or' ? item.caption_or : item.caption_en;
    meta.textContent = `${appState.currentLanguage === 'or' ? 'ଶ୍ରେଣୀ' : 'Category'}: ${item.category} | ${item.date}`;

    lightbox.style.display = 'flex';
    lightbox.classList.add('active');
}

// ==========================================
// TOAST NOTIFICATIONS & ALERTS
// ==========================================
function showToast(message, type = 'success') {
    const alertBox = document.getElementById('custom-alert');
    alertBox.textContent = message;
    alertBox.className = `custom-alert ${type}`;
    alertBox.style.display = 'block';

    setTimeout(() => {
        alertBox.style.display = 'none';
    }, 4000);
}

// ==========================================
// ALUMNI SUBSCRIPTION FORM HANDLER
// ==========================================
function handleAlumniRegistration(e) {
    e.preventDefault();

    const name = document.getElementById('reg-name').value.trim();
    const batch = document.getElementById('reg-batch').value.trim();
    const mobile = document.getElementById('reg-mobile').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const profession = document.getElementById('reg-profession').value.trim();
    const location = document.getElementById('reg-location').value.trim();
    const message = document.getElementById('reg-message').value.trim();
    const photoInput = document.getElementById('reg-photo');

    const formData = new FormData();
    formData.append('name', name);
    formData.append('batch', batch);
    formData.append('mobile', mobile);
    formData.append('email', email);
    formData.append('profession', profession || '');
    formData.append('location', location);
    formData.append('message', message || '');

    if (photoInput.files && photoInput.files[0]) {
        formData.append('photo', photoInput.files[0]);
    }

    const submitBtn = document.getElementById('reg-submit-btn');
    const originalBtnText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = appState.currentLanguage === 'or' ? "ସବମିଟ୍ ହେଉଛି..." : "Submitting...";

    fetch('api/alumni', {
        method: 'POST',
        body: formData
    })
    .then(res => {
        if (!res.ok) throw new Error('Registration failed');
        return res.json();
    })
    .then(data => {
        submitBtn.disabled = false;
        submitBtn.textContent = originalBtnText;

        // Toggle success screens
        document.getElementById('registration-form-card').style.display = 'none';
        document.getElementById('registration-success-card').style.display = 'block';

        const badgeContainer = document.getElementById('success-badge-container');
        const pendingContainer = document.getElementById('success-pending-container');

        if (data.status === 'approved') {
            if (badgeContainer) badgeContainer.style.display = 'block';
            if (pendingContainer) pendingContainer.style.display = 'none';

            // Populate Badge Modal fields
            document.getElementById('badge-name').textContent = data.name;
            document.getElementById('badge-batch').textContent = data.batch;
            document.getElementById('badge-location').textContent = data.location;
            document.getElementById('badge-id').textContent = data.id;
            document.getElementById('badge-photo').src = data.photo;
        } else {
            if (badgeContainer) badgeContainer.style.display = 'none';
            if (pendingContainer) pendingContainer.style.display = 'block';
        }

        loadDataFromServer();
        showToast(appState.currentLanguage === 'or' ? "ପଞ୍କୀକରଣ ସଫଳ ହେଲା!" : "Registration submitted successfully!", "success");
    })
    .catch(err => {
        submitBtn.disabled = false;
        submitBtn.textContent = originalBtnText;
        console.error(err);
        showToast(appState.currentLanguage === 'or' ? "ସମସ୍ୟା ଦେଖାଦେଲା, ଦୟାକରି ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।" : "An error occurred, please try again.", "error");
    });
}

// Reset the registration form
function resetRegistrationForm() {
    document.getElementById('alumni-register-form').reset();
    document.getElementById('reg-photo-preview').style.display = 'none';
    document.getElementById('registration-success-card').style.display = 'none';
    document.getElementById('registration-form-card').style.display = 'block';
}

// ==========================================
// EVENT LISTENERS INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    // 1. Database Init
    initDatabase();

    // 2. Language Switcher Buttons
    document.getElementById('lang-en-btn').addEventListener('click', () => setLanguage('en'));
    document.getElementById('lang-or-btn').addEventListener('click', () => setLanguage('or'));

    // Apply saved language or default to en
    setLanguage(appState.currentLanguage);

    // 3. Navbar Mobile Toggle
    document.getElementById('nav-toggle').addEventListener('click', () => {
        document.getElementById('nav-menu').classList.toggle('open');
    });

    // 4. Client Router hooks
    window.addEventListener('hashchange', handleRouting);
    handleRouting(); // trigger initial route

    // 5. Lightbox Close hooks
    document.getElementById('lightbox-close').addEventListener('click', () => {
        document.getElementById('lightbox-modal').style.display = 'none';
        document.getElementById('lightbox-modal').classList.remove('active');
    });
    
    // Close on click outside
    document.getElementById('lightbox-modal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('lightbox-modal')) {
            document.getElementById('lightbox-modal').style.display = 'none';
            document.getElementById('lightbox-modal').classList.remove('active');
        }
    });

    // Notice Modal Close
    document.getElementById('notice-modal-close').addEventListener('click', () => {
        document.getElementById('notice-modal').style.display = 'none';
        document.getElementById('notice-modal').classList.remove('active');
    });
    
    document.getElementById('notice-modal').addEventListener('click', (e) => {
        if (e.target === document.getElementById('notice-modal')) {
            document.getElementById('notice-modal').style.display = 'none';
            document.getElementById('notice-modal').classList.remove('active');
        }
    });

    // 6. Notice Board Filter Toggles
    const filterContainer = document.getElementById('notice-filter-tags');
    if (filterContainer) {
        filterContainer.querySelectorAll('.tag-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                filterContainer.querySelectorAll('.tag-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                appState.activeNoticeFilter = btn.getAttribute('data-category');
                renderNoticesPage();
            });
        });
    }

    // Search bar event
    const searchBar = document.getElementById('notice-search');
    if (searchBar) {
        searchBar.addEventListener('input', renderNoticesPage);
    }

    // 7. Gallery Filter Toggles
    const galleryFilterContainer = document.getElementById('gallery-filter-tags');
    if (galleryFilterContainer) {
        galleryFilterContainer.querySelectorAll('.tag-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                galleryFilterContainer.querySelectorAll('.tag-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                appState.activeGalleryFilter = btn.getAttribute('data-category');
                renderGalleryPage();
            });
        });
    }

    // 8. Alumni Photo Upload Preview
    const regPhotoInput = document.getElementById('reg-photo');
    const regPhotoPreview = document.getElementById('reg-photo-preview');
    if (regPhotoInput && regPhotoPreview) {
        regPhotoInput.addEventListener('change', (e) => {
            if (regPhotoInput.files && regPhotoInput.files[0]) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    regPhotoPreview.src = event.target.result;
                    regPhotoPreview.style.display = 'block';
                    regPhotoPreview.style.margin = '10px auto';
                };
                reader.readAsDataURL(regPhotoInput.files[0]);
            }
        });
    }

    // 9. Alumni Form Submit
    const registerForm = document.getElementById('alumni-register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', handleAlumniRegistration);
    }

    // 10. Register Another button
    const regAnotherBtn = document.getElementById('reg-another-btn');
    if (regAnotherBtn) {
        regAnotherBtn.addEventListener('click', resetRegistrationForm);
    }
    
    // Set dynamic current year in footer
    const yearSpan = document.getElementById('footer-year');
    if (yearSpan) {
        yearSpan.textContent = new Date().getFullYear();
    }
});

// Attach helper functions to window for other scripts to access
window.appState = appState;
window.showToast = showToast;
