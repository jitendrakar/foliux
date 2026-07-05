/**
 * LocalStorage Database Engine
 * Success Academy Coaching Institute
 */

const SEED_SETTINGS = {
    site_name: 'Success Academy Coaching Institute',
    contact_phone: '+91 98718 08718',
    contact_whatsapp: '+91 98718 08718',
    contact_email: 'jitendra.kar@gmail.com',
    office_address: 'Building No. 45, Vidya Nagar, Near Central Library, Jaipur, Rajasthan - 302015',
    working_hours: 'Monday - Saturday: 8:00 AM - 8:00 PM (Sunday Closed)',
    maps_embed: '<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3557.842792873138!2d75.78726581504445!3d26.907727983129598!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x396db406697bb3cb%3A0xe54d24177fe7753e!2sJaipur%20Central%20Library!5e0!3m2!1sen!2sin!4v1625482937210!5m2!1sen!2sin" width="100%" height="350" style="border:0;" allowfullscreen="" loading="lazy"></iframe>',
    admission_status: 1,
    facebook_url: 'https://facebook.com/successacademy',
    instagram_url: 'https://instagram.com/successacademy',
    youtube_url: 'https://youtube.com/successacademy',
    meta_title: 'Success Academy - Best Coaching Institute for IIT-JEE, NEET & School Foundation',
    meta_description: 'Success Academy is a premium coaching institute in Jaipur offering courses for IIT-JEE, NEET, CUET, UPSC, NDA, SSC, and school foundations. Join today for admissions 2026-27.'
};

const SEED_COURSES = [
    { id: 1, title: 'IIT-JEE (Main + Advanced) 2-Year Program', category: 'JEE', duration: '2 Years', fees: 120000, batch_timing: '08:00 AM - 12:00 PM', features: 'Daily Practice Papers (DPP), Weekly Part-Tests, Personal Mentorship, Study Material', description: 'Comprehensive program for Class 11 students aiming for engineering entrance examinations. Focuses deeply on Physics, Chemistry, and Mathematics from fundamentals to advanced JEE level.', image_path: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=400', status: 1 },
    { id: 2, title: 'NEET (Medical Entrance) Achievers Course', category: 'NEET', duration: '2 Years', fees: 130000, batch_timing: '01:00 PM - 05:00 PM', features: 'NCERT-focused sessions, Regular Biology Diagrams practice, All-India Mock Tests, Doubt Clinics', description: 'Designed for medical aspirants in Class 11 and 12. Complete coverage of NEET syllabus with expert faculty members from premier medical coaching ecosystems.', image_path: 'https://images.unsplash.com/photo-1576091160550-2173dba999ef?q=80&w=400', status: 1 },
    { id: 3, title: 'UPSC Foundation Course', category: 'UPSC', duration: '1 Year', fees: 85000, batch_timing: '09:00 AM - 01:00 PM', features: 'Daily Current Affairs Analysis, GS Prelims & Mains Modules, CSAT Prep, Weekly Essay Writing', description: 'Perfect foundation course for graduation students and civil services aspirants. Develops conceptual clarity on History, Geography, Polity, Economy, and Ethics.', image_path: 'https://images.unsplash.com/photo-1427504494785-3a9ca7044f45?q=80&w=400', status: 1 },
    { id: 4, title: 'CUET (UG) Crash Course', category: 'CUET', duration: '6 Months', fees: 25000, batch_timing: '03:00 PM - 06:00 PM', features: 'General Test Preparation, English Language Classes, Major Domain Subject Coaching, Computer Based Mock Tests', description: 'Targeted course to secure admissions in prestigious central universities like DU, BHU, and JNU. Features intensive mock examinations mimicking the actual NTA format.', image_path: 'https://images.unsplash.com/photo-1523050854058-8df90110c9f1?q=80&w=400', status: 1 },
    { id: 5, title: 'NDA Written & SSB Prep', category: 'NDA', duration: '1 Year', fees: 45000, batch_timing: '06:00 AM - 10:00 AM', features: 'Mathematics & General Ability Test prep, Physical Fitness Guidance, SSB Mock Interviews, English Communication', description: 'Preparation program for the National Defence Academy entrance exam. Incorporates personality development, physical standard checks, and SSB board mock sessions.', image_path: 'https://images.unsplash.com/photo-1524178232363-1fb2b075b655?q=80&w=400', status: 1 },
    { id: 6, title: 'SSC CGL Master Batch', category: 'SSC', duration: '6 Months', fees: 18000, batch_timing: '10:00 AM - 01:00 PM', features: 'Advanced Quantitative Aptitude shortcuts, Reasoning Tricks, Comprehensive General Studies, Descriptive English guidance', description: 'Rigorous coaching for Staff Selection Commission Combined Graduate Level exams. Covers Tier-I and Tier-II syllabus with high-speed computation techniques.', image_path: 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?q=80&w=400', status: 1 },
    { id: 7, title: 'Banking (IBPS/SBI PO & Clerk)', category: 'Banking', duration: '6 Months', fees: 15000, batch_timing: '02:00 PM - 05:00 PM', features: 'Daily Speed Maths drills, Banking Awareness modules, Reading Comprehension tactics, Weekly Online Mock Exams', description: 'Structured course focusing on banking sector recruitments. Designed to build speed, accuracy, and clear banking aptitude sections.', image_path: 'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?q=80&w=400', status: 1 },
    { id: 8, title: 'Railway NTPC & Group D', category: 'Railway', duration: '6 Months', fees: 12000, batch_timing: '08:00 AM - 11:00 AM', features: 'General Science specialty, Mock Tests, Mathematics basics, Previous Year Question solving', description: 'A specialized coaching course for various positions under Indian Railways (RRB NTPC, Group D, ALP).', image_path: 'https://images.unsplash.com/photo-1474487548417-781cb71495f3?q=80&w=400', status: 1 },
    { id: 9, title: 'Class 6 - 10 Foundation (CBSE/ICSE)', category: 'Foundation', duration: '1 Year', fees: 30000, batch_timing: '04:00 PM - 07:00 PM', features: 'Mental Ability & Logical Reasoning, Science & Maths Olympiad prep, NTSE Stage-I training, School Board Syllabus', description: 'Pre-foundation course targeting early academic excellence. Prepares students for NTSE, JSTSE, and Olympiads alongside school board curriculums.', image_path: 'https://images.unsplash.com/photo-1509062522246-3755977927d7?q=80&w=400', status: 1 },
    { id: 10, title: 'Class 11 - 12 (Science Board + CET)', category: 'School', duration: '1 Year', fees: 50000, batch_timing: '02:00 PM - 06:00 PM', features: 'Physics, Chemistry, Maths/Biology Board preps, Laboratory guidance, Chapter-wise notes, Board format mocks', description: 'Tailored coaching for scoring 95%+ in Board examinations. Focuses on CBSE/State board theory writing and numerical solving.', image_path: 'https://images.unsplash.com/photo-1497633762265-9d179a990aa6?q=80&w=400', status: 1 },
    { id: 11, title: 'Class 11 - 12 (Commerce Board)', category: 'School', duration: '1 Year', fees: 45000, batch_timing: '03:00 PM - 06:00 PM', features: 'Double Entry Book-keeping drills, Economics graphs mastery, Business Studies case studies, Board Mock Papers', description: 'Commerce coaching covering Accountancy, Economics, Business Studies, and Applied Mathematics.', image_path: 'https://images.unsplash.com/photo-1542435503-956c469947f6?q=80&w=400', status: 1 },
    { id: 12, title: 'Olympiad Preparation (NTSE / IMO / NSO)', category: 'Olympiad', duration: '6 Months', fees: 15000, batch_timing: '05:00 PM - 07:00 PM', features: 'National & International Level curriculum, Logical Reasoning booster, High-Order Thinking Skills (HOTS) questions', description: 'Special course for students aiming to clear science, math, and cyber olympiads.', image_path: 'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?q=80&w=400', status: 1 }
];

const SEED_FACULTY = [
    { id: 1, name: 'Dr. R. K. Verma', qualification: 'Ph.D. in Physics (IIT Delhi)', experience: '15+ Years', subject: 'Physics', photo_path: 'https://images.unsplash.com/photo-1560250097-0b93528c311a?q=80&w=300', status: 1 },
    { id: 2, name: 'Prof. S. N. Mukherjee', qualification: 'M.Sc. in Organic Chemistry (IIT Kharagpur)', experience: '12+ Years', subject: 'Chemistry', photo_path: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=300', status: 1 },
    { id: 3, name: 'Mrs. Priya Sharma', qualification: 'M.Tech in Mathematics (NIT Warangal)', experience: '8+ Years', subject: 'Mathematics', photo_path: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=300', status: 1 },
    { id: 4, name: 'Dr. Amit Patel', qualification: 'MBBS, MD (AIIMS New Delhi)', experience: '10+ Years', subject: 'Biology (Botany & Zoology)', photo_path: 'https://images.unsplash.com/photo-1537368910025-700350fe46c7?q=80&w=300', status: 1 },
    { id: 5, name: 'Col. V. K. Singh (Retd.)', qualification: 'M.A. in Defence & Strategic Studies', experience: '20+ Years', subject: 'SSB Interview & NDA Prep', photo_path: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=300', status: 1 },
    { id: 6, name: 'Mr. Rajesh Dwivedi', qualification: 'M.A. in History, Cleared UPSC Mains 3 times', experience: '9+ Years', subject: 'UPSC General Studies', photo_path: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=300', status: 1 }
];

const SEED_RESULTS = [
    { id: 1, student_name: 'Amit Kumar', exam_name: 'JEE Advanced', air_rank: 14, score: '342 / 360', year: 2025, success_story: 'Amit joined our 2-Year Classroom Program in Class 11. Through rigorous test series and consistent doubt solving by our experts, he secured AIR 14.', photo_path: 'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?q=80&w=300', status: 1 },
    { id: 2, student_name: 'Priya Patel', exam_name: 'NEET UG', air_rank: 42, score: '712 / 720', year: 2025, success_story: 'Priya credited her top score to the AIIMS-focused faculty members and NCERT-centered test drills. Her dedication and Success Academy\'s mentorship helped her reach AIIMS New Delhi.', photo_path: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?q=80&w=300', status: 1 },
    { id: 3, student_name: 'Rahul Verma', exam_name: 'UPSC Civil Services', air_rank: 89, score: 'Cleared', year: 2024, success_story: 'Rahul was a part of our UPSC Foundation Batch. He achieved AIR 89 in his second attempt with History Optional. "The weekly answer writing evaluation was the key to my success," says Rahul.', photo_path: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=300', status: 1 },
    { id: 4, student_name: 'Sneha Gupta', exam_name: 'JEE Main', air_rank: 105, score: '99.99 Percentile', year: 2025, success_story: 'Sneha topped Jaipur city in JEE Main with a perfect score in Physics and Chemistry. Her discipline and our topic-wise analysis helped her achieve her dream.', photo_path: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=300', status: 1 },
    { id: 5, student_name: 'Vikram Rathore', exam_name: 'NDA', air_rank: 22, score: 'SSB Cleared', year: 2025, success_story: 'Vikram prepared for NDA written and SSB interview guidance under Col. V. K. Singh (Retd.). His physical conditioning and mental agility helped him secure an AIR 22.', photo_path: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=300', status: 1 }
];

const SEED_GALLERY = [
    { id: 1, title: 'Modern Physics Laboratory', category: 'campus', image_path: 'https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?q=80&w=400', status: 1 },
    { id: 2, title: 'Interactive Classroom Session', category: 'classroom', image_path: 'https://images.unsplash.com/photo-1580582932707-520aed937b7b?q=80&w=400', status: 1 },
    { id: 3, title: 'Independence Day Celebration 2025', category: 'events', image_path: 'https://images.unsplash.com/photo-1532375810709-75b1da00537c?q=80&w=400', status: 1 },
    { id: 4, title: 'Annual Sports Meet 2025', category: 'annual', image_path: 'https://images.unsplash.com/photo-1517649763962-0c623066013b?q=80&w=400', status: 1 },
    { id: 5, title: 'Felicitation Ceremony of JEE & NEET Rankers', category: 'awards', image_path: 'https://images.unsplash.com/photo-1511578314322-379afb476865?q=80&w=400', status: 1 },
    { id: 6, title: 'Well-Stocked Reference Library', category: 'campus', image_path: 'https://images.unsplash.com/photo-1497633762265-9d179a990aa6?q=80&w=400', status: 1 }
];

const SEED_TESTIMONIALS = [
    { id: 1, student_name: 'Aditya Sen', course_name: 'IIT-JEE Program', review: 'The teachers here are extremely supportive. The personal doubt-clearing sessions helped me clear core physics concepts. I highly recommend Success Academy to all engineering aspirants!', rating: 5, photo_path: 'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?q=80&w=150', status: 1 },
    { id: 2, student_name: 'Divya Nair', course_name: 'NEET Achievers Batch', review: 'Excellent study environment. The topic-wise NEET tests are very close to the actual NTA paper. The biology diagrams and Mnemonics notes were very helpful.', rating: 5, photo_path: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?q=80&w=150', status: 1 },
    { id: 3, student_name: 'Manish Choudhary', course_name: 'UPSC Foundation', review: 'As a beginner, I was lost in the vast syllabus of UPSC. The foundation batch structured my preparation perfectly. The faculty explains complex economy topics with absolute ease.', rating: 5, photo_path: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=150', status: 1 }
];

const SEED_NEWS = [
    {
        id: 1,
        title: 'How to Prepare for JEE Main 2027: A Comprehensive Guide',
        slug: 'how-to-prepare-jee-main-2027',
        excerpt: 'Read the study plan, recommended reference books, and preparation strategy from our top rankers and senior physics faculty.',
        content: `<h3>1. Concept Clarity Over Rote Learning</h3><p>Rather than memorizing formulas, understand the derivation. Physics topics like Mechanics and Electrostatics require high logical deduction.</p><h3>2. Quality Study Material</h3><p>Ensure you solve NCERT for chemistry, and HC Verma for introductory physics. Refrain from buying too many reference books.</p><h3>3. Regular Mock Exams</h3><p>Weekly tests are non-negotiable. They build your stamina for the 3-hour computer-based test (CBT) format.</p>`,
        category: 'articles',
        image_path: 'https://images.unsplash.com/photo-1434030216411-0b793f4b4173?q=80&w=400',
        published_date: '2026-06-25',
        status: 1
    },
    {
        id: 2,
        title: 'NEET 2027 Registration Dates and Exam Pattern Changes',
        slug: 'neet-2027-registration-dates-changes',
        excerpt: 'Get the latest official announcements regarding the NEET exam schedule, Eligibility details, and NTA updates.',
        content: `<h3>Key Dates:</h3><ul><li>Online Registration Begins: First week of January 2027</li><li>Last Date of Fee Payment: Second week of February 2027</li><li>Exam Date: First Sunday of May 2027</li></ul><p>Ensure your documents (Class 10 mark sheet, Aadhar Card) are updated and match exactly.</p>`,
        category: 'exam_updates',
        image_path: 'https://images.unsplash.com/photo-1576091160550-2173dba999ef?q=80&w=400',
        published_date: '2026-07-02',
        status: 1
    },
    {
        id: 3,
        title: 'Scholarship Entrance Test (SET) 2027 announced: Win up to 100% Scholarship',
        slug: 'scholarship-entrance-test-set-2027',
        excerpt: 'Success Academy announces SET 2027 for admissions to JEE, NEET, and Foundation courses. Register online now!',
        content: `<h3>Who Can Apply?</h3><p>Students currently studying in Classes 5 to 11 can register.</p><h3>Scholarship Slab:</h3><ul><li>Rank 1-5: 100% Tuition Fee Waiver</li><li>Rank 6-20: 75% Tuition Fee Waiver</li></ul>`,
        category: 'scholarship',
        image_path: 'https://images.unsplash.com/photo-1523050854058-8df90110c9f1?q=80&w=400',
        published_date: '2026-07-04',
        status: 1
    }
];

// Initialize Database if empty
function initDatabase() {
    if (!localStorage.getItem('sa_db_initialized_v2')) {
        localStorage.setItem('sa_settings', JSON.stringify(SEED_SETTINGS));
        localStorage.setItem('sa_courses', JSON.stringify(SEED_COURSES));
        localStorage.setItem('sa_faculty', JSON.stringify(SEED_FACULTY));
        localStorage.setItem('sa_results', JSON.stringify(SEED_RESULTS));
        localStorage.setItem('sa_gallery', JSON.stringify(SEED_GALLERY));
        localStorage.setItem('sa_testimonials', JSON.stringify(SEED_TESTIMONIALS));
        localStorage.setItem('sa_news', JSON.stringify(SEED_NEWS));
        localStorage.setItem('sa_admissions', JSON.stringify([]));
        localStorage.setItem('sa_enquiries', JSON.stringify([]));
        localStorage.setItem('sa_db_initialized_v2', 'true');
    }
}

// Call init immediately
initDatabase();

// DB Actions Helper API
const DB = {
    // Settings
    getSettings() {
        return JSON.parse(localStorage.getItem('sa_settings'));
    },
    saveSettings(settings) {
        localStorage.setItem('sa_settings', JSON.stringify(settings));
        return true;
    },

    // Courses
    getCourses(category = null) {
        let list = JSON.parse(localStorage.getItem('sa_courses')) || [];
        list = list.filter(c => c.status === 1 || c.status === '1');
        if (category && category !== 'all') {
            list = list.filter(c => c.category === category);
        }
        return list;
    },
    getAllCoursesAdmin() {
        return JSON.parse(localStorage.getItem('sa_courses')) || [];
    },
    getCourseById(id) {
        const list = this.getAllCoursesAdmin();
        return list.find(c => c.id === parseInt(id));
    },
    saveCourse(course) {
        const list = this.getAllCoursesAdmin();
        course.id = parseInt(course.id);
        course.fees = parseFloat(course.fees);
        course.status = course.status ? 1 : 0;
        
        if (course.id > 0) {
            // Edit
            const idx = list.findIndex(c => c.id === course.id);
            if (idx !== -1) list[idx] = course;
        } else {
            // Add
            course.id = list.length > 0 ? Math.max(...list.map(c => c.id)) + 1 : 1;
            if (!course.image_path) course.image_path = 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=400';
            list.push(course);
        }
        localStorage.setItem('sa_courses', JSON.stringify(list));
        return true;
    },
    deleteCourse(id) {
        let list = this.getAllCoursesAdmin();
        list = list.filter(c => c.id !== parseInt(id));
        localStorage.setItem('sa_courses', JSON.stringify(list));
        return true;
    },

    // Faculty
    getFaculty() {
        let list = JSON.parse(localStorage.getItem('sa_faculty')) || [];
        return list.filter(f => f.status === 1 || f.status === '1');
    },
    getAllFacultyAdmin() {
        return JSON.parse(localStorage.getItem('sa_faculty')) || [];
    },
    getFacultyById(id) {
        return this.getAllFacultyAdmin().find(f => f.id === parseInt(id));
    },
    saveFaculty(fac) {
        const list = this.getAllFacultyAdmin();
        fac.id = parseInt(fac.id);
        fac.status = fac.status ? 1 : 0;
        
        if (fac.id > 0) {
            const idx = list.findIndex(f => f.id === fac.id);
            if (idx !== -1) list[idx] = fac;
        } else {
            fac.id = list.length > 0 ? Math.max(...list.map(f => f.id)) + 1 : 1;
            if (!fac.photo_path) fac.photo_path = 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=300';
            list.push(fac);
        }
        localStorage.setItem('sa_faculty', JSON.stringify(list));
        return true;
    },
    deleteFaculty(id) {
        let list = this.getAllFacultyAdmin();
        list = list.filter(f => f.id !== parseInt(id));
        localStorage.setItem('sa_faculty', JSON.stringify(list));
        return true;
    },

    // Results
    getResults() {
        let list = JSON.parse(localStorage.getItem('sa_results')) || [];
        return list.filter(r => r.status === 1 || r.status === '1').sort((a,b) => a.air_rank - b.air_rank);
    },

    // Testimonials
    getTestimonials() {
        let list = JSON.parse(localStorage.getItem('sa_testimonials')) || [];
        return list.filter(t => t.status === 1 || t.status === '1');
    },
    getAllTestimonialsAdmin() {
        return JSON.parse(localStorage.getItem('sa_testimonials')) || [];
    },
    getTestimonialById(id) {
        return this.getAllTestimonialsAdmin().find(t => t.id === parseInt(id));
    },
    saveTestimonial(test) {
        const list = this.getAllTestimonialsAdmin();
        test.id = parseInt(test.id);
        test.rating = parseInt(test.rating);
        test.status = test.status ? 1 : 0;
        
        if (test.id > 0) {
            const idx = list.findIndex(t => t.id === test.id);
            if (idx !== -1) list[idx] = test;
        } else {
            test.id = list.length > 0 ? Math.max(...list.map(t => t.id)) + 1 : 1;
            test.photo_path = 'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?q=80&w=150';
            list.push(test);
        }
        localStorage.setItem('sa_testimonials', JSON.stringify(list));
        return true;
    },
    deleteTestimonial(id) {
        let list = this.getAllTestimonialsAdmin();
        list = list.filter(t => t.id !== parseInt(id));
        localStorage.setItem('sa_testimonials', JSON.stringify(list));
        return true;
    },

    // Gallery
    getGallery(cat = 'all') {
        let list = JSON.parse(localStorage.getItem('sa_gallery')) || [];
        list = list.filter(g => g.status === 1 || g.status === '1');
        if (cat && cat !== 'all') {
            list = list.filter(g => g.category === cat);
        }
        return list;
    },
    getAllGalleryAdmin() {
        return JSON.parse(localStorage.getItem('sa_gallery')) || [];
    },
    saveGalleryItem(item) {
        const list = this.getAllGalleryAdmin();
        item.id = list.length > 0 ? Math.max(...list.map(g => g.id)) + 1 : 1;
        item.status = 1;
        list.push(item);
        localStorage.setItem('sa_gallery', JSON.stringify(list));
        return true;
    },
    deleteGalleryItem(id) {
        let list = this.getAllGalleryAdmin();
        list = list.filter(g => g.id !== parseInt(id));
        localStorage.setItem('sa_gallery', JSON.stringify(list));
        return true;
    },

    // News/Blogs
    getNews(cat = null) {
        let list = JSON.parse(localStorage.getItem('sa_news')) || [];
        list = list.filter(n => n.status === 1 || n.status === '1');
        if (cat && cat !== 'all') {
            list = list.filter(n => n.category === cat);
        }
        return list.sort((a,b) => new Date(b.published_date) - new Date(a.published_date));
    },
    getNewsBySlug(slug) {
        const list = this.getNews();
        return list.find(n => n.slug === slug);
    },
    getAllNewsAdmin() {
        return JSON.parse(localStorage.getItem('sa_news')) || [];
    },
    getNewsById(id) {
        return this.getAllNewsAdmin().find(n => n.id === parseInt(id));
    },
    saveNews(article) {
        const list = this.getAllNewsAdmin();
        article.id = parseInt(article.id);
        article.status = article.status ? 1 : 0;
        article.slug = article.title.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)+/g, '');
        
        if (article.id > 0) {
            const idx = list.findIndex(n => n.id === article.id);
            if (idx !== -1) list[idx] = article;
        } else {
            article.id = list.length > 0 ? Math.max(...list.map(n => n.id)) + 1 : 1;
            article.image_path = 'https://images.unsplash.com/photo-1506784983877-45594efa4cbe?q=80&w=400';
            list.push(article);
        }
        localStorage.setItem('sa_news', JSON.stringify(list));
        return true;
    },
    deleteNews(id) {
        let list = this.getAllNewsAdmin();
        list = list.filter(n => n.id !== parseInt(id));
        localStorage.setItem('sa_news', JSON.stringify(list));
        return true;
    },

    // Admissions
    getAdmissions() {
        return JSON.parse(localStorage.getItem('sa_admissions')) || [];
    },
    getAdmissionById(id) {
        return this.getAdmissions().find(a => a.id === parseInt(id));
    },
    addAdmission(data) {
        const list = this.getAdmissions();
        data.id = list.length > 0 ? Math.max(...list.map(a => a.id)) + 1 : 1001;
        data.status = 'Pending';
        data.created_at = new Date().toISOString();
        list.push(data);
        localStorage.setItem('sa_admissions', JSON.stringify(list));
        return data.id;
    },
    updateAdmissionStatus(id, status) {
        const list = this.getAdmissions();
        const idx = list.findIndex(a => a.id === parseInt(id));
        if (idx !== -1) {
            list[idx].status = status;
            localStorage.setItem('sa_admissions', JSON.stringify(list));
            return true;
        }
        return false;
    },
    deleteAdmission(id) {
        let list = this.getAdmissions();
        list = list.filter(a => a.id !== parseInt(id));
        localStorage.setItem('sa_admissions', JSON.stringify(list));
        return true;
    },

    // Enquiries
    getEnquiries() {
        return JSON.parse(localStorage.getItem('sa_enquiries')) || [];
    },
    getEnquiryById(id) {
        return this.getEnquiries().find(e => e.id === parseInt(id));
    },
    addEnquiry(data) {
        const list = this.getEnquiries();
        data.id = list.length > 0 ? Math.max(...list.map(e => e.id)) + 1 : 1;
        data.created_at = new Date().toISOString();
        list.push(data);
        localStorage.setItem('sa_enquiries', JSON.stringify(list));
        return true;
    },
    deleteEnquiry(id) {
        let list = this.getEnquiries();
        list = list.filter(e => e.id !== parseInt(id));
        localStorage.setItem('sa_enquiries', JSON.stringify(list));
        return true;
    }
};

window.DB = DB;
