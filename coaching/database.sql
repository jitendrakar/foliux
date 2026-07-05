-- Database Schema for Success Academy Coaching Institute

-- 1. Settings Table
CREATE TABLE IF NOT EXISTS `settings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `site_name` VARCHAR(150) NOT NULL,
    `contact_phone` VARCHAR(20) NOT NULL,
    `contact_whatsapp` VARCHAR(20) NOT NULL,
    `contact_email` VARCHAR(100) NOT NULL,
    `office_address` TEXT NOT NULL,
    `working_hours` VARCHAR(100) NOT NULL,
    `maps_embed` TEXT,
    `admission_status` TINYINT(1) DEFAULT 1,
    `facebook_url` VARCHAR(255),
    `instagram_url` VARCHAR(255),
    `youtube_url` VARCHAR(255),
    `meta_title` VARCHAR(150),
    `meta_description` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Courses Table
CREATE TABLE IF NOT EXISTS `courses` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(100) NOT NULL,
    `category` VARCHAR(50) NOT NULL,
    `duration` VARCHAR(50) NOT NULL,
    `fees` DECIMAL(10,2) NOT NULL,
    `batch_timing` VARCHAR(100) NOT NULL,
    `features` TEXT NOT NULL,
    `description` TEXT,
    `image_path` VARCHAR(255) DEFAULT 'assets/images/courses/default.jpg',
    `status` TINYINT(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Faculty Table
CREATE TABLE IF NOT EXISTS `faculty` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `qualification` VARCHAR(150) NOT NULL,
    `experience` VARCHAR(50) NOT NULL,
    `subject` VARCHAR(100) NOT NULL,
    `photo_path` VARCHAR(255) DEFAULT 'assets/images/faculty/default.jpg',
    `status` TINYINT(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Results Table
CREATE TABLE IF NOT EXISTS `results` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_name` VARCHAR(100) NOT NULL,
    `exam_name` VARCHAR(50) NOT NULL,
    `air_rank` INT NOT NULL,
    `score` VARCHAR(50) NOT NULL,
    `year` INT NOT NULL,
    `success_story` TEXT,
    `photo_path` VARCHAR(255) DEFAULT 'assets/images/results/default.jpg',
    `status` TINYINT(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Gallery Table
CREATE TABLE IF NOT EXISTS `gallery` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(150) NOT NULL,
    `category` VARCHAR(50) NOT NULL,
    `image_path` VARCHAR(255) NOT NULL,
    `status` TINYINT(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. News Table
CREATE TABLE IF NOT EXISTS `news` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(255) NOT NULL,
    `slug` VARCHAR(255) UNIQUE NOT NULL,
    `excerpt` TEXT NOT NULL,
    `content` LONGTEXT NOT NULL,
    `category` VARCHAR(50) NOT NULL,
    `image_path` VARCHAR(255) DEFAULT 'assets/images/news/default.jpg',
    `published_date` DATE NOT NULL,
    `status` TINYINT(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Testimonials Table
CREATE TABLE IF NOT EXISTS `testimonials` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_name` VARCHAR(100) NOT NULL,
    `course_name` VARCHAR(100) NOT NULL,
    `review` TEXT NOT NULL,
    `rating` INT DEFAULT 5,
    `photo_path` VARCHAR(255) DEFAULT 'assets/images/testimonials/default.jpg',
    `status` TINYINT(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Admissions Table
CREATE TABLE IF NOT EXISTS `admissions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_name` VARCHAR(100) NOT NULL,
    `father_name` VARCHAR(100) NOT NULL,
    `mobile` VARCHAR(15) NOT NULL,
    `email` VARCHAR(100) NOT NULL,
    `address` TEXT NOT NULL,
    `course_id` INT,
    `class_name` VARCHAR(50) NOT NULL,
    `photo_path` VARCHAR(255),
    `status` VARCHAR(20) DEFAULT 'Pending',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Enquiries Table
CREATE TABLE IF NOT EXISTS `enquiries` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(100) NOT NULL,
    `phone` VARCHAR(15) NOT NULL,
    `subject` VARCHAR(150),
    `message` TEXT NOT NULL,
    `type` VARCHAR(30) DEFAULT 'General Enquiry',
    `course_id` INT DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Admin Users Table
CREATE TABLE IF NOT EXISTS `admin_users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) UNIQUE NOT NULL,
    `password` VARCHAR(255) NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `role` VARCHAR(20) DEFAULT 'admin'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Seed Data

-- Settings
INSERT INTO `settings` (`id`, `site_name`, `contact_phone`, `contact_whatsapp`, `contact_email`, `office_address`, `working_hours`, `maps_embed`, `admission_status`, `facebook_url`, `instagram_url`, `youtube_url`, `meta_title`, `meta_description`) VALUES
(1, 'Success Academy Coaching Institute', '+91 98765 43210', '+91 98765 43210', 'info@successacademy.co.in', 'Building No. 45, Vidya Nagar, Near Central Library, Jaipur, Rajasthan - 302015', 'Monday - Saturday: 8:00 AM - 8:00 PM (Sunday Closed)', '<iframe src=\"https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3557.842792873138!2d75.78726581504445!3d26.907727983129598!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x396db406697bb3cb%3A0xe54d24177fe7753e!2sJaipur%20Central%20Library!5e0!3m2!1sen!2sin!4v1625482937210!5m2!1sen!2sin\" width=\"100%\" height=\"350\" style=\"border:0;\" allowfullscreen=\"\" loading=\"lazy\"></iframe>', 1, 'https://facebook.com/successacademy', 'https://instagram.com/successacademy', 'https://youtube.com/successacademy', 'Success Academy - Best Coaching Institute for IIT-JEE, NEET & School Foundation', 'Success Academy is a premium coaching institute in Jaipur offering courses for IIT-JEE, NEET, CUET, UPSC, NDA, SSC, and school foundations. Join today for admissions 2026-27.');

-- Admin Login: admin / admin123 (hashed using bcrypt)
INSERT INTO `admin_users` (`id`, `username`, `password`, `name`, `role`) VALUES
(1, 'admin', '$2y$10$wE16L3iMv2G32nFv94RkOuJ9b17.fGis492XmXn22XfH22gWd15rO', 'Director Sir', 'admin');

-- Courses
INSERT INTO `courses` (`id`, `title`, `category`, `duration`, `fees`, `batch_timing`, `features`, `description`, `image_path`, `status`) VALUES
(1, 'IIT-JEE (Main + Advanced) 2-Year Program', 'JEE', '2 Years', 120000.00, '08:00 AM - 12:00 PM', 'Daily Practice Papers (DPP), Weekly Part-Tests, Personal Mentorship, Study Material', 'Comprehensive program for Class 11 students aiming for engineering entrance examinations. Focuses deeply on Physics, Chemistry, and Mathematics from fundamentals to advanced JEE level.', 'assets/images/courses/jee.jpg', 1),
(2, 'NEET (Medical Entrance) Achievers Course', 'NEET', '2 Years', 130000.00, '01:00 PM - 05:00 PM', 'NCERT-focused sessions, Regular Biology Diagrams practice, All-India Mock Tests, Doubt Clinics', 'Designed for medical aspirants in Class 11 and 12. Complete coverage of NEET syllabus with expert faculty members from premier medical coaching ecosystems.', 'assets/images/courses/neet.jpg', 1),
(3, 'UPSC Foundation Course', 'UPSC', '1 Year', 85000.00, '09:00 AM - 01:00 PM', 'Daily Current Affairs Analysis, GS Prelims & Mains Modules, CSAT Prep, Weekly Essay Writing', 'Perfect foundation course for graduation students and civil services aspirants. Develops conceptual clarity on History, Geography, Polity, Economy, and Ethics.', 'assets/images/courses/upsc.jpg', 1),
(4, 'CUET (UG) Crash Course', 'CUET', '6 Months', 25000.00, '03:00 PM - 06:00 PM', 'General Test Preparation, English Language Classes, Major Domain Subject Coaching, Computer Based Mock Tests', 'Targeted course to secure admissions in prestigious central universities like DU, BHU, and JNU. Features intensive mock examinations mimicking the actual NTA format.', 'assets/images/courses/cuet.jpg', 1),
(5, 'NDA Written & SSB Prep', 'NDA', '1 Year', 45000.00, '06:00 AM - 10:00 AM', 'Mathematics & General Ability Test prep, Physical Fitness Guidance, SSB Mock Interviews, English Communication', 'Preparation program for the National Defence Academy entrance exam. Incorporates personality development, physical standard checks, and SSB board mock sessions.', 'assets/images/courses/nda.jpg', 1),
(6, 'SSC CGL Master Batch', 'SSC', '6 Months', 18000.00, '10:00 AM - 01:00 PM', 'Advanced Quantitative Aptitude shortcuts, Reasoning Tricks, Comprehensive General Studies, Descriptive English guidance', 'Rigorous coaching for Staff Selection Commission Combined Graduate Level exams. Covers Tier-I and Tier-II syllabus with high-speed computation techniques.', 'assets/images/courses/ssc.jpg', 1),
(7, 'Banking (IBPS/SBI PO & Clerk)', 'Banking', '6 Months', 15000.00, '02:00 PM - 05:00 PM', 'Daily Speed Maths drills, Banking Awareness modules, Reading Comprehension tactics, Weekly Online Mock Exams', 'Structured course focusing on banking sector recruitments. Designed to build speed, accuracy, and clear banking aptitude sections.', 'assets/images/courses/banking.jpg', 1),
(8, 'Railway NTPC & Group D', 'Railway', '6 Months', 12000.00, '08:00 AM - 11:00 AM', 'General Science specialty, Mock Tests, Mathematics basics, Previous Year Question solving', 'A specialized coaching course for various positions under Indian Railways (RRB NTPC, Group D, ALP).', 'assets/images/courses/railway.jpg', 1),
(9, 'Class 6 - 10 Foundation (CBSE/ICSE)', 'Foundation', '1 Year', 30000.00, '04:00 PM - 07:00 PM', 'Mental Ability & Logical Reasoning, Science & Maths Olympiad prep, NTSE Stage-I training, School Board Syllabus', 'Pre-foundation course targeting early academic excellence. Prepares students for NTSE, JSTSE, and Olympiads alongside school board curriculums.', 'assets/images/courses/foundation.jpg', 1),
(10, 'Class 11 - 12 (Science Board + CET)', 'School', '1 Year', 50000.00, '02:00 PM - 06:00 PM', 'Physics, Chemistry, Maths/Biology Board preps, Laboratory guidance, Chapter-wise notes, Board format mocks', 'Tailored coaching for scoring 95%+ in Board examinations. Focuses on CBSE/State board theory writing and numerical solving.', 'assets/images/courses/science.jpg', 1),
(11, 'Class 11 - 12 (Commerce Board)', 'School', '1 Year', 45000.00, '03:00 PM - 06:00 PM', 'Double Entry Book-keeping drills, Economics graphs mastery, Business Studies case studies, Board Mock Papers', 'Commerce coaching covering Accountancy, Economics, Business Studies, and Applied Mathematics.', 'assets/images/courses/commerce.jpg', 1),
(12, 'Olympiad Preparation (NTSE / IMO / NSO)', 'Olympiad', '6 Months', 15000.00, '05:00 PM - 07:00 PM', 'National & International Level curriculum, Logical Reasoning booster, High-Order Thinking Skills (HOTS) questions', 'Special course for students aiming to clear science, math, and cyber olympiads.', 'assets/images/courses/olympiad.jpg', 1);

-- Faculty
INSERT INTO `faculty` (`id`, `name`, `qualification`, `experience`, `subject`, `photo_path`, `status`) VALUES
(1, 'Dr. R. K. Verma', 'Ph.D. in Physics (IIT Delhi)', '15+ Years', 'Physics', 'assets/images/faculty/verma.jpg', 1),
(2, 'Prof. S. N. Mukherjee', 'M.Sc. in Organic Chemistry (IIT Kharagpur)', '12+ Years', 'Chemistry', 'assets/images/faculty/mukherjee.jpg', 1),
(3, 'Mrs. Priya Sharma', 'M.Tech in Mathematics (NIT Warangal)', '8+ Years', 'Mathematics', 'assets/images/faculty/priya.jpg', 1),
(4, 'Dr. Amit Patel', 'MBBS, MD (AIIMS New Delhi)', '10+ Years', 'Biology (Botany & Zoology)', 'assets/images/faculty/patel.jpg', 1),
(5, 'Col. V. K. Singh (Retd.)', 'M.A. in Defence & Strategic Studies', '20+ Years', 'SSB Interview & NDA Prep', 'assets/images/faculty/singh.jpg', 1),
(6, 'Mr. Rajesh Dwivedi', 'M.A. in History, Cleared UPSC Mains 3 times', '9+ Years', 'UPSC General Studies', 'assets/images/faculty/dwivedi.jpg', 1);

-- Results
INSERT INTO `results` (`id`, `student_name`, `exam_name`, `air_rank`, `score`, `year`, `success_story`, `photo_path`, `status`) VALUES
(1, 'Amit Kumar', 'JEE Advanced', 14, '342 / 360', 2025, 'Amit joined our 2-Year Classroom Program in Class 11. Through rigorous test series and consistent doubt solving by our experts, he secured AIR 14.', 'assets/images/results/amit.jpg', 1),
(2, 'Priya Patel', 'NEET UG', 42, '712 / 720', 2025, 'Priya credited her top score to the AIIMS-focused faculty members and NCERT-centered test drills. Her dedication and Success Academy\'s mentorship helped her reach AIIMS New Delhi.', 'assets/images/results/priya_result.jpg', 1),
(3, 'Rahul Verma', 'UPSC Civil Services', 89, 'Cleared', 2024, 'Rahul was a part of our UPSC Foundation Batch. He achieved AIR 89 in his second attempt with History Optional. \"The weekly answer writing evaluation was the key to my success,\" says Rahul.', 'assets/images/results/rahul.jpg', 1),
(4, 'Sneha Gupta', 'JEE Main', 105, '99.99 Percentile', 2025, 'Sneha topped Jaipur city in JEE Main with a perfect score in Physics and Chemistry. Her discipline and our topic-wise analysis helped her achieve her dream.', 'assets/images/results/sneha.jpg', 1),
(5, 'Vikram Rathore', 'NDA', 22, 'SSB Cleared', 2025, 'Vikram prepared for NDA written and SSB interview guidance under Col. V. K. Singh (Retd.). His physical conditioning and mental agility helped him secure an AIR 22.', 'assets/images/results/vikram.jpg', 1);

-- Gallery
INSERT INTO `gallery` (`id`, `title`, `category`, `image_path`, `status`) VALUES
(1, 'Modern Physics Laboratory', 'campus', 'assets/images/gallery/campus1.jpg', 1),
(2, 'Interactive Classroom Session', 'classroom', 'assets/images/gallery/class1.jpg', 1),
(3, 'Independence Day Celebration 2025', 'events', 'assets/images/gallery/event1.jpg', 1),
(4, 'Annual Sports Meet 2025', 'annual', 'assets/images/gallery/annual1.jpg', 1),
(5, 'Felicitation Ceremony of JEE & NEET Rankers', 'awards', 'assets/images/gallery/awards1.jpg', 1),
(6, 'Well-Stocked Reference Library', 'campus', 'assets/images/gallery/campus2.jpg', 1);

-- Testimonials
INSERT INTO `testimonials` (`id`, `student_name`, `course_name`, `review`, `rating`, `photo_path`, `status`) VALUES
(1, 'Aditya Sen', 'IIT-JEE Program', 'The teachers here are extremely supportive. The personal doubt-clearing sessions helped me clear core physics concepts. I highly recommend Success Academy to all engineering aspirants!', 5, 'assets/images/testimonials/aditya.jpg', 1),
(2, 'Divya Nair', 'NEET Achievers Batch', 'Excellent study environment. The topic-wise NEET tests are very close to the actual NTA paper. The biology diagrams and Mnemonics notes were very helpful.', 5, 'assets/images/testimonials/divya.jpg', 1),
(3, 'Manish Choudhary', 'UPSC Foundation', 'As a beginner, I was lost in the vast syllabus of UPSC. The foundation batch structured my preparation perfectly. The faculty explains complex economy topics with absolute ease.', 5, 'assets/images/testimonials/manish.jpg', 1);

-- News
INSERT INTO `news` (`id`, `title`, `slug`, `excerpt`, `content`, `category`, `image_path`, `published_date`, `status`) VALUES
(1, 'How to Prepare for JEE Main 2027: A Comprehensive Guide', 'how-to-prepare-jee-main-2027', 'Read the study plan, recommended reference books, and preparation strategy from our top rankers and senior physics faculty.', '<p>Preparing for JEE Main requires a balanced approach between concepts and time-bound practice. Here are the core pillars of a solid JEE preparation strategy:</p><h3>1. Concept Clarity Over Rote Learning</h3><p>Rather than memorizing formulas, understand the derivation. Physics topics like Mechanics and Electrostatics, and Math topics like Calculus require high logical deduction. Chemistry demands a dual approach: understanding physical chemistry concepts while memorizing inorganic trends.</p><h3>2. Quality Study Material</h3><p>Success Academy provides comprehensive sheets. Ensure you solve NCERT for chemistry and physics, and HC Verma for introductory physics. Refrain from buying too many reference books.</p><h3>3. Regular Mock Exams</h3><p>Weekly tests are non-negotiable. They build your stamina for the 3-hour computer-based test (CBT) format. Analyze every mistake and maintain a \"Mistake Log Book\".</p>', 'articles', 'assets/images/news/jee-prep.jpg', '2026-06-25', 1),
(2, 'NEET 2027 Registration Dates and Exam Pattern Changes', 'neet-2027-registration-dates-changes', 'Get the latest official announcements regarding the NEET exam schedule, Eligibility details, and NTA updates.', '<p>The National Testing Agency (NTA) has released notifications outlining the schedule for NEET-UG 2027. Aspirants can register starting January 2027 on the official portal.</p><h3>Key Dates:</h3><ul><li>Online Registration Begins: First week of January 2027</li><li>Last Date of Fee Payment: Second week of February 2027</li><li>Admit Card Release: April 2027</li><li>Exam Date: First Sunday of May 2027</li></ul><p>Our NEET batches are already aligning with the latest mock exam trends. Ensure your documents (Class 10 mark sheet, Aadhar Card, category certificate) are updated and match exactly.</p>', 'exam_updates', 'assets/images/news/neet-news.jpg', '2026-07-02', 1),
(3, 'Scholarship Entrance Test (SET) 2027 announced: Win up to 100% Scholarship', 'scholarship-entrance-test-set-2027', 'Success Academy announces SET 2027 for admissions to JEE, NEET, and Foundation courses. Register online now!', '<p>Success Academy is proud to announce its annual Scholarship Entrance Test (SET) 2027, scheduled for October 12, 2026 and November 16, 2026. This test aims to recognize and nurture talented students by offering them tuition fee waivers up to 100%.</p><h3>Who Can Apply?</h3><p>Students currently studying in Classes 5, 6, 7, 8, 9, 10, and 11 can register. Test papers will comprise Mental Ability, Mathematics, and General Science questions suited to the respective grade.</p><h3>Scholarship Slab:</h3><ul><li>Rank 1-5: 100% Tuition Fee Waiver</li><li>Rank 6-20: 75% Tuition Fee Waiver</li><li>Rank 21-50: 50% Tuition Fee Waiver</li><li>Rank 51-200: 25% Tuition Fee Waiver</li></ul><p>Online registration is open. Form fee is only ₹100. Visit the nearest Success Academy center or register on our website under the Admissions tab.</p>', 'scholarship', 'assets/images/news/scholarship.jpg', '2026-07-04', 1);
