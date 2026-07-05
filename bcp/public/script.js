// ==========================================
// CLIENT-SIDE STATE & TRANSLATIONS
// ==========================================
let menuData = [];
let cart = [];
let currentCategory = 'all';
let activeOrderId = null;
let currentLang = 'en'; // default language
let isAdminAuthenticated = false; // admin auth state

const translations = {
  en: {
    "nav-sub": "Chicken & Mutton Shop",
    "nav-menu": "Menu",
    "nav-about": "Our Shop",
    "nav-contact": "Contact",
    "nav-admin": " Vendor Portal",
    
    "hero-tagline": "🔥 Authentic Halal Meat Since 1998",
    "hero-title": "Taste the Royalty of Spiced Kababs & Fresh Cut Meats",
    "hero-desc": "Order online for free delivery in Sriniwaspuri. Choose from our premium fresh meats or ready-to-eat spiced kababs made with handpicked ingredients.",
    "hero-order-btn": "Order Now",
    "hero-shop-btn": "View Shop",
    "hero-badge-open": "🟢 Shop Open (9 AM - 10 PM)",
    "hero-badge-delivery": "🛵 Free Home Delivery",
    "hero-badge-upi": "💳 UPI Scan & Pay Enabled",
    
    "caption-front": "Shop Front",
    "caption-kitchen": "Fresh Kitchen",
    
    "menu-subtitle": "Fresh & Prepared",
    "menu-title": "Explore Our Menu",
    "menu-desc": "We serve fresh cut chicken and mutton along with marinated ready-to-fry kababs and piping hot specials.",
    "tab-all": "All Items",
    "tab-raw": "🍗 Raw Chicken & Mutton",
    "tab-ready": "🍢 Ready to Eat Kababs",
    "tab-specials": "🌶️ Prepared Specials",
    "menu-loading": "Loading fresh menu items...",
    
    "about-subtitle": "Hygiene & Trust",
    "about-title": "Welcome to Bharat Chicken & Mutton Shop",
    "about-desc1": "Owned and managed by Sarfaraj (Guddu), Bharat Chicken Point has been serving New Delhi with the finest quality Halal meats and culinary creations for over two decades.",
    "about-desc2": "Our kitchen and meat storage display cases are kept in sterile, temperature-controlled environments to ensure the highest standards of hygiene and food safety. We pride ourselves on transparent pricing (directly displayed in our store) and excellent customer service.",
    "feat1-title": "100% Halal Certified",
    "feat1-desc": "All our chicken and mutton are processed and cut strictly according to Halal guidelines.",
    "feat2-title": "Sterile Cold Display Cases",
    "feat2-desc": "Our raw meats are stored in dust-free, chilled glass display shelves to prevent contamination.",
    "feat3-title": "Superfast Delivery",
    "feat3-desc": "Get quick delivery straight to your doorstep in Sriniwaspuri and nearby areas.",
    
    "contact-title": "Visit or Contact Us",
    "contact-desc": "Have bulk requirements for a wedding, party, or restaurant? Reach out to us directly!",
    "contact-timing": "Open Daily: 9:00 AM to 10:00 PM",
    "map-pin-title": "Bharat Chicken & Mutton Shop",
    "map-pin-subtitle": "Sriniwaspuri, Private Colony",
    
    "footer-copyright": "© 2026 Bharat Chicken Point. All rights reserved. Managed by Sarfaraj (Guddu).",
    
    // Admin Login Screen
    "admin-login-title": "Vendor Portal Login",
    "admin-login-desc": "Enter your administrative username and password to manage orders.",
    "label-username": "Username",
    "label-password": "Password",
    "error-invalid-credentials": "⚠️ Invalid admin credentials. Please try again.",
    "btn-login": "Login",
    "btn-return-store": "Return to Storefront",
    
    // Admin Dashboard Header
    "admin-dash-title": "Vendor Management Dashboard",
    "admin-dash-desc": "Manage incoming orders, update status, view SMTP logs, and configure email servers.",
    "btn-logout": "Logout",
    "tab-orders": "📦 Active Orders",
    "tab-emails": "📧 Simulated Email Logs",
    "tab-settings": "⚙️ SMTP Configuration",
    
    // Admin Dashboard Stats & Table
    "stat-lbl-total": "Total Orders",
    "stat-lbl-pending": "Pending Payment",
    "stat-lbl-kitchen": "Paid / In Kitchen",
    "stat-lbl-delivered": "Delivered",
    "tbl-title-recent": "Recent Orders",
    "btn-refresh": "🔄 Refresh",
    "th-orderid": "Order ID",
    "th-custinfo": "Customer Info",
    "th-address": "Delivery Address",
    "th-items": "Items (Qty)",
    "th-total": "Total Amount",
    "th-payment": "Payment Details",
    "th-status": "Status",
    "th-actions": "Actions",
    
    // Admin simulated email empty pane
    "email-pane-empty-title": "Select an email to view",
    "email-pane-empty-desc": "Click on any message in the inbox to view the simulated HTML output sent to the customer or vendor.",
    
    // SMTP panel
    "smtp-title": "Email Server Settings",
    "smtp-desc": "By default, email notifications are simulated and logged to the 'Simulated Email Logs' database because no mail server credentials are set. Toggle SMTP below to use real email routing via a Gmail account.",
    "smtp-toggle-lbl": "Enable Real Email Delivery (SMTP)",
    "smtp-pass-hint": "For Gmail, generate a 16-character App Password. Never use your main account password.",
    "smtp-vendor-lbl": "Vendor Notification Email (Recipient)",
    "smtp-vendor-hint": "This email will receive notifications containing complete customer orders and payment receipts.",
    "smtp-save-btn": "Save Configuration",
    
    // Cart Drawer
    "cart-title": "Your Basket",
    "cart-empty-msg": "Your basket is currently empty.",
    "cart-start-shopping": "Start Shopping",
    "cart-form-header": "Delivery Details",
    "label-name": "Full Name *",
    "label-phone": "Mobile Phone *",
    "label-email": "Email Address (Optional)",
    "label-address": "Delivery Address *",
    "summary-subtotal": "Items Subtotal",
    "summary-delivery": "Delivery Charges",
    "free": "FREE",
    "summary-total": "Total Amount",
    "btn-checkout": "Proceed to Pay (UPI)",
    
    // UPI Modal
    "upi-modal-title": "UPI Safe Checkout",
    "upi-payee-badge": "Amount to Pay",
    "upi-instructions": "Scan this QR code using any UPI App (GPay, PhonePe, Paytm, BHIM) to make instant secure payment.",
    "upi-instructions-static": "Scan this official shop QR code using any UPI App and manually enter the exact amount.",
    "qr-toggle-dynamic": "Auto-Fill QR (Recommended)",
    "qr-toggle-static": "Official GPay QR",
    "upi-mobile-pay-text": " Pay directly via UPI App",
    "upi-mobile-pay-hint": "Click above if ordering on your mobile phone.",
    "upi-confirm-header": "Confirm Your Payment",
    "upi-utr-info": "After completing the transaction, paste the 12-digit transaction UTR / Reference ID from your UPI app below to verify.",
    "mock-utr-btn": "Mock UTR",
    "mock-utr-hint": "Example: 304212589064. Click 'Mock UTR' for instant sandbox testing.",
    "upi-verify-btn": " Verify & Complete Order",
    
    // Success Screen
    "success-header": "Payment Successful!",
    "success-kitchen-note": "Your order has been placed and is being prepared in the kitchen.",
    "success-receipt-title": "Order Details",
    "receipt-label-name": "Customer Name:",
    "receipt-label-phone": "Contact Phone:",
    "receipt-label-address": "Delivery Address:",
    "receipt-label-method": "Payment Method:",
    "upi-payment-method": "UPI Scan & Pay",
    "receipt-label-utr": "Transaction UTR:",
    "receipt-label-amount": "Amount Paid:",
    "receipt-notice-note": "📨 A confirmation receipt has been logged to your email. The vendor has received this order and is preparing it for delivery.",
    "btn-continue-shopping": "Continue Shopping",
    "btn-view-dashboard": "View in Vendor Dashboard",
    
    // Placeholders
    "placeholder-name": "Enter your name",
    "placeholder-phone": "Enter 10-digit mobile number",
    "placeholder-email": "For receiving receipt",
    "placeholder-address": "Enter complete house address, street, and landmarks in Sriniwaspuri",
    "placeholder-utr": "Enter 12-digit UPI UTR Number",
    "placeholder-username": "Enter username",
    "placeholder-password": "Enter password"
  },
  hi: {
    "nav-sub": "चिकन और मटन शॉप",
    "nav-menu": "मेनू",
    "nav-about": "हमारी दुकान",
    "nav-contact": "संपर्क",
    "nav-admin": " विक्रेता पोर्टल",
    
    "hero-tagline": "🔥 1998 से असली हलाल मीट",
    "hero-title": "मसालेदार कबाब और ताज़ा कटे मीट के शाही स्वाद का आनंद लें",
    "hero-desc": "श्रीनिवासपुरी में मुफ्त डिलीवरी के लिए ऑनलाइन ऑर्डर करें। हमारे प्रीमियम ताज़ा मीट या हमारे हाथ से चुने गए मसालों से बने तैयार कबाबों में से चुनें।",
    "hero-order-btn": "अभी ऑर्डर करें",
    "hero-shop-btn": "दुकान देखें",
    "hero-badge-open": "🟢 दुकान खुली है (9 AM - 10 PM)",
    "hero-badge-delivery": "🛵 मुफ्त होम डिलीवरी",
    "hero-badge-upi": "💳 यूपीआई स्कैन और भुगतान सक्षम",
    
    "caption-front": "दुकान का सामने का हिस्सा",
    "caption-kitchen": "ताजा रसोईघर",
    
    "menu-subtitle": "ताज़ा और तैयार व्यंजन",
    "menu-title": "हमारे मेनू की खोज करें",
    "menu-desc": "हम ताज़ा कटा हुआ चिकन और मटन के साथ-साथ मसालेदार कबाब और गरमा-गरम विशेष व्यंजन परोसते हैं।",
    "tab-all": "सभी आइटम",
    "tab-raw": "🍗 ताज़ा चिकन और मटन",
    "tab-ready": "🍢 तैयार सीख कबाब",
    "tab-specials": "🌶️ तैयार गरमा-गरम व्यंजन",
    "menu-loading": "ताज़ा मेनू लोड हो रहा है...",
    
    "about-subtitle": "स्वच्छता और विश्वास",
    "about-title": "भारत चिकन और मटन शॉप में आपका स्वागत है",
    "about-desc1": "सरफराज (गुड्डू) के स्वामित्व और प्रबंधन में, भारत चिकन पॉइंट दो दशकों से अधिक समय से नई दिल्ली को बेहतरीन गुणवत्ता वाले हलाल मीट और स्वादिष्ट व्यंजन परोस रहा है।",
    "about-desc2": "हाइजीन और खाद्य सुरक्षा के उच्चतम मानकों को सुनिश्चित करने के लिए हमारे रसोईघर और मीट स्टोरेज डिस्प्ले केस को पूरी तरह स्वच्छ, तापमान-नियंत्रित वातावरण में रखा जाता है। हम पारदर्शी मूल्य निर्धारण और उत्कृष्ट ग्राहक सेवा पर गर्व करते हैं।",
    "feat1-title": "100% हलाल प्रमाणित",
    "feat1-desc": "हमारे सभी चिकन और मटन को कड़ाई से हलाल दिशानिर्देशों के अनुसार संसाधित और काटा जाता है।",
    "feat2-title": "स्वच्छ कोल्ड डिस्प्ले केस",
    "feat2-desc": "हमारे कच्चे मीट को संदूषण से बचाने के लिए धूल-मुक्त, ठंडे शीशे के डिस्प्ले सेल्फ में रखा जाता है।",
    "feat3-title": "सुपरफास्ट डिलीवरी",
    "feat3-desc": "श्रीनिवासपुरी और आसपास के क्षेत्रों में सीधे अपने दरवाजे पर त्वरित डिलीवरी प्राप्त करें।",
    
    "contact-title": "हमसे संपर्क करें",
    "contact-desc": "शादी, पार्टी या रेस्तरां के लिए थोक में मीट चाहिए? हमसे सीधे संपर्क करें!",
    "contact-timing": "रोजाना खुला: सुबह 9:00 बजे से रात 10:00 बजे तक",
    "map-pin-title": "भारत चिकन और मटन शॉप",
    "map-pin-subtitle": "श्रीनिवासपुरी, प्राइवेट कॉलोनी",
    
    "footer-copyright": "© 2026 भारत चिकन पॉइंट। सर्वाधिकार सुरक्षित। संचालक: सरफराज (गुड्डू)।",
    
    // Admin Login Screen
    "admin-login-title": "विक्रेता पोर्टल लॉगिन",
    "admin-login-desc": "ऑर्डर प्रबंधित करने के लिए अपना प्रशासनिक उपयोगकर्ता नाम और पासवर्ड दर्ज करें।",
    "label-username": "उपयोगकर्ता नाम",
    "label-password": "पासवर्ड",
    "error-invalid-credentials": "⚠️ अमान्य प्रशासनिक क्रेडेंशियल। कृपया पुनः प्रयास करें।",
    "btn-login": "लॉगिन करें",
    "btn-return-store": "स्टोरफ्रंट पर वापस जाएं",
    
    // Admin Dashboard Header
    "admin-dash-title": "विक्रेता प्रबंधन डैशबोर्ड",
    "admin-dash-desc": "आने वाले ऑर्डरों का प्रबंधन करें, स्थिति अपडेट करें, ईमेल लॉग देखें और ईमेल सर्वर कॉन्फ़िगर करें।",
    "btn-logout": "लॉगआउट",
    "tab-orders": "📦 सक्रिय ऑर्डर",
    "tab-emails": "📧 ईमेल लॉग्स",
    "tab-settings": "⚙️ एसएमटीपी कॉन्फ़िगरेशन",
    
    // Admin Dashboard Stats & Table
    "stat-lbl-total": "कुल ऑर्डर",
    "stat-lbl-pending": "लंबित भुगतान",
    "stat-lbl-kitchen": "भुगतान किया / रसोई में",
    "stat-lbl-delivered": "डिलीवर किया",
    "tbl-title-recent": "हाल के ऑर्डर",
    "btn-refresh": "🔄 रीफ्रेश",
    "th-orderid": "ऑर्डर आईडी",
    "th-custinfo": "ग्राहक विवरण",
    "th-address": "डिलीवरी का पता",
    "th-items": "सामग्री (मात्रा)",
    "th-total": "कुल राशि",
    "th-payment": "भुगतान विवरण",
    "th-status": "स्थिति",
    "th-actions": "कार्रवाई",
    
    // Admin simulated email empty pane
    "email-pane-empty-title": "देखने के लिए ईमेल चुनें",
    "email-pane-empty-desc": "ग्राहक या विक्रेता को भेजे गए ईमेल को देखने के लिए इनबॉक्स में किसी भी संदेश पर क्लिक करें।",
    
    // SMTP panel
    "smtp-title": "ईमेल सर्वर सेटिंग्स",
    "smtp-desc": "डिफ़ॉल्ट रूप से, ईमेल सूचनाएं नकली (सिम्युलेटेड) होती हैं क्योंकि कोई क्रेडेंशियल सेट नहीं है। वास्तविक ईमेल भेजने के लिए नीचे एसएमटीपी चालू करें।",
    "smtp-toggle-lbl": "वास्तविक ईमेल डिलीवरी (SMTP) सक्षम करें",
    "smtp-pass-hint": "जीमेल के लिए, 16-अक्षरों का ऐप पासवर्ड बनाएं। अपने मुख्य पासवर्ड का उपयोग न करें।",
    "smtp-vendor-lbl": "विक्रेता अधिसूचना ईमेल (प्राप्तकर्ता)",
    "smtp-vendor-hint": "इस ईमेल पर नए ऑर्डर और रसीद विवरण प्राप्त होंगे।",
    "smtp-save-btn": "कॉन्फ़िगरेशन सहेजें",
    
    // Cart Drawer
    "cart-title": "आपकी टोकरी",
    "cart-empty-msg": "आपकी टोकरी वर्तमान में खाली है।",
    "cart-start-shopping": "खरीदारी शुरू करें",
    "cart-form-header": "डिलीवरी का पता और जानकारी",
    "label-name": "पूरा नाम *",
    "label-phone": "मोबाइल नंबर *",
    "label-email": "ईमेल पता (वैकल्पिक)",
    "label-address": "डिलीवरी का पता *",
    "summary-subtotal": "आइटम उप-योग",
    "summary-delivery": "डिलीवरी शुल्क",
    "free": "मुफ़्त",
    "summary-total": "कुल देय राशि",
    "btn-checkout": "भुगतान करें (यूपीआई)",
    
    // UPI Modal
    "upi-modal-title": "यूपीआई सुरक्षित चेकआउट",
    "upi-payee-badge": "भुगतान की जाने वाली राशि",
    "upi-instructions": "तत्काल सुरक्षित भुगतान करने के लिए किसी भी यूपीआई ऐप (GPay, PhonePe, Paytm, BHIM) का उपयोग करके इस क्यूआर कोड को स्कैन करें।",
    "upi-instructions-static": "किसी भी यूपीआई ऐप का उपयोग करके इस आधिकारिक दुकान क्यूआर कोड को स्कैन करें और मैन्युअल रूप से सटीक राशि दर्ज करें।",
    "qr-toggle-dynamic": "ऑटो-फिल QR (अनुशंसित)",
    "qr-toggle-static": "आधिकारिक GPay QR",
    "upi-mobile-pay-text": " यूपीआई ऐप से सीधे भुगतान करें",
    "upi-mobile-pay-hint": "यदि आप अपने मोबाइल फोन से ऑर्डर कर रहे हैं तो ऊपर क्लिक करें।",
    "upi-confirm-header": "अपने भुगतान की पुष्टि करें",
    "upi-utr-info": "लेन-देन पूरा करने के बाद, सत्यापन के लिए नीचे अपने यूपीआई ऐप से प्राप्त 12-अंकों का ट्रांजेक्शन यूटीआर दर्ज करें।",
    "mock-utr-btn": "मॉक यूटीआर",
    "mock-utr-hint": "उदाहरण: 304212589064. तत्काल सैंडबॉक्स परीक्षण के लिए 'मॉक यूटीआर' पर क्लिक करें।",
    "upi-verify-btn": " सत्यापित करें और ऑर्डर पूरा करें",
    
    // Success Screen
    "success-header": "भुगतान सफल रहा!",
    "success-kitchen-note": "आपका ऑर्डर स्वीकार कर लिया गया है और रसोई में तैयार किया जा रहा है।",
    "success-receipt-title": "ऑर्डर का विवरण",
    "receipt-label-name": "ग्राहक का नाम:",
    "receipt-label-phone": "संपर्क मोबाइल:",
    "receipt-label-address": "डिलीवरी का पता:",
    "receipt-label-method": "भुगतान का प्रकार:",
    "upi-payment-method": "यूपीआई स्कैन और पे",
    "receipt-label-utr": "ट्रांजेक्शन यूटीआर नंबर:",
    "receipt-label-amount": "भुगतान की गई राशि:",
    "receipt-notice-note": "📨 एक पुष्टिकरण रसीद आपके ईमेल पर लॉग कर दी गई है। विक्रेता को यह ऑर्डर प्राप्त हो गया है और वह इसे डिलीवरी के लिए तैयार कर रहा है।",
    "btn-continue-shopping": "खरीदारी जारी रखें",
    "btn-view-dashboard": "विक्रेता डैशबोर्ड में देखें",
    
    // Placeholders
    "placeholder-name": "अपना नाम दर्ज करें",
    "placeholder-phone": "10-अंकों का मोबाइल नंबर दर्ज करें",
    "placeholder-email": "रसीद प्राप्त करने के लिए",
    "placeholder-address": "श्रीनिवासपुरी में मकान नंबर, गली और लैंडमार्क दर्ज करें",
    "placeholder-utr": "12-अंकों का यूपीआई यूटीआर दर्ज करें",
    "placeholder-username": "उपयोगकर्ता नाम दर्ज करें",
    "placeholder-password": "पासवर्ड दर्ज करें"
  }
};

// DOM Elements
const menuGrid = document.getElementById('menuGrid');
const cartBtn = document.getElementById('cartBtn');
const cartDrawer = document.getElementById('cartDrawer');
const cartBackdrop = document.getElementById('cartBackdrop');
const closeCartBtn = document.getElementById('closeCartBtn');
const cartItemsContainer = document.getElementById('cartItemsContainer');
const checkoutForm = document.getElementById('checkoutForm');
const cartFooter = document.getElementById('cartFooter');
const billSubtotal = document.getElementById('billSubtotal');
const billTotal = document.getElementById('billTotal');
const submitCheckoutBtn = document.getElementById('submitCheckoutBtn');
const cartCount = document.getElementById('cartCount');

// UPI Modal DOM
const upiModal = document.getElementById('upiModal');
const closeUpiBtn = document.getElementById('closeUpiBtn');
const upiModalAmount = document.getElementById('upiModalAmount');
const upiQrCodeImg = document.getElementById('upiQrCodeImg');
const upiStaticQrImg = document.getElementById('upiStaticQrImg');
const qrCodeWrapper = document.getElementById('qrCodeWrapper');
const qrLoader = document.getElementById('qrLoader');
const upiMobileLink = document.getElementById('upiMobileLink');
const upiUtr = document.getElementById('upiUtr');
const mockUtrBtn = document.getElementById('mockUtrBtn');
const verifyPaymentBtn = document.getElementById('verifyPaymentBtn');
const verifyBtnText = document.getElementById('verifyBtnText');
const verifyBtnSpinner = document.getElementById('verifyBtnSpinner');
const qrToggleDynamic = document.getElementById('qrToggleDynamic');
const qrToggleStatic = document.getElementById('qrToggleStatic');
const upiInstructions = document.getElementById('upiInstructions');

// Success Screen DOM
const successScreen = document.getElementById('successScreen');
const successOrderId = document.getElementById('successOrderId');
const successCustName = document.getElementById('successCustName');
const successCustPhone = document.getElementById('successCustPhone');
const successCustAddress = document.getElementById('successCustAddress');
const successUtr = document.getElementById('successUtr');
const successAmount = document.getElementById('successAmount');
const successHomeBtn = document.getElementById('successHomeBtn');
const successAdminBtn = document.getElementById('successAdminBtn');

// Navigation DOM
const customerView = document.getElementById('customerView');
const adminView = document.getElementById('adminView');
const navLinks = document.querySelectorAll('.nav-link');

// Admin DOM
const adminOrdersTableBody = document.getElementById('adminOrdersTableBody');
const refreshOrdersBtn = document.getElementById('refreshOrdersBtn');
const emailInboxList = document.getElementById('emailInboxList');
const emailReadingPane = document.getElementById('emailReadingPane');
const smtpSettingsForm = document.getElementById('smtpSettingsForm');

// Stats DOM
const statTotal = document.getElementById('statTotal');
const statPending = document.getElementById('statPending');
const statPaid = document.getElementById('statPaid');
const statDelivered = document.getElementById('statDelivered');

// Global Loader DOM
const globalLoader = document.getElementById('globalLoader');
const globalLoaderText = document.getElementById('globalLoaderText');

// ==========================================
// BOOTSTRAP / INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
  loadCartFromStorage();
  checkViewFromHash();
  fetchMenu();
  setupEventListeners();

  // Load Admin Authentication State
  isAdminAuthenticated = sessionStorage.getItem('bcp_admin_auth') === 'true';

  // Initialize Language from local storage or default to English
  const savedLang = localStorage.getItem('bcp_lang') || 'en';
  setLanguage(savedLang);
});

// Watch URL changes for Routing
window.addEventListener('hashchange', checkViewFromHash);

function checkViewFromHash() {
  const hash = window.location.hash;
  
  // Reset active classes
  navLinks.forEach(link => link.classList.remove('active'));

  if (hash === '#admin') {
    // Show Admin Panel container
    customerView.classList.add('hidden');
    adminView.classList.remove('hidden');
    document.getElementById('nav-admin').classList.add('active');

    // Authenticated check
    if (isAdminAuthenticated) {
      document.getElementById('adminLoginView').classList.add('hidden');
      document.getElementById('adminDashboardContent').classList.remove('hidden');
      loadAdminDashboard();
    } else {
      document.getElementById('adminLoginView').classList.remove('hidden');
      document.getElementById('adminDashboardContent').classList.add('hidden');
    }
  } else {
    // Show Customer Storefront
    customerView.classList.remove('hidden');
    adminView.classList.add('hidden');
    
    // Highlight relevant header link
    if (hash === '#about') {
      document.getElementById('nav-about').classList.add('active');
    } else if (hash === '#contact') {
      document.getElementById('nav-contact').classList.add('active');
    } else {
      document.getElementById('nav-menu').classList.add('active');
    }
  }
  
  // Close cart drawer just in case
  closeCart();
}

function showGlobalLoader(text) {
  globalLoaderText.textContent = text || 'Loading...';
  globalLoader.classList.remove('hidden');
}

function hideGlobalLoader() {
  globalLoader.classList.add('hidden');
}

// ==========================================
// TRANSLATION CONTROLS
// ==========================================
function setLanguage(lang) {
  currentLang = lang;
  localStorage.setItem('bcp_lang', lang);

  // Apply translations to data-translate selectors
  document.querySelectorAll('[data-translate]').forEach(el => {
    const key = el.getAttribute('data-translate');
    if (translations[lang] && translations[lang][key]) {
      // For elements holding icons inside, preserve structural elements and swap only text nodes
      if (key === 'nav-admin' || key === 'upi-mobile-pay-text' || key === 'upi-verify-btn') {
        const textNode = Array.from(el.childNodes).find(node => node.nodeType === Node.TEXT_NODE);
        if (textNode) {
          textNode.textContent = translations[lang][key];
        } else {
          el.textContent = translations[lang][key];
        }
      } else {
        el.textContent = translations[lang][key];
      }
    }
  });

  // Apply placeholders translations
  const nameInp = document.getElementById('cust-name');
  const phoneInp = document.getElementById('cust-phone');
  const emailInp = document.getElementById('cust-email');
  const addressInp = document.getElementById('cust-address');
  const utrInp = document.getElementById('upiUtr') || document.getElementById('upi-utr');
  const adminUserInp = document.getElementById('admin-user');
  const adminPassInp = document.getElementById('admin-pass');

  if (nameInp) nameInp.placeholder = translations[lang]['placeholder-name'];
  if (phoneInp) phoneInp.placeholder = translations[lang]['placeholder-phone'];
  if (emailInp) emailInp.placeholder = translations[lang]['placeholder-email'];
  if (addressInp) addressInp.placeholder = translations[lang]['placeholder-address'];
  if (utrInp) utrInp.placeholder = translations[lang]['placeholder-utr'];
  if (adminUserInp) adminUserInp.placeholder = translations[lang]['placeholder-username'];
  if (adminPassInp) adminPassInp.placeholder = translations[lang]['placeholder-password'];

  // Toggle label value in language button
  const langTextEl = document.getElementById('langToggleText');
  if (langTextEl) {
    langTextEl.textContent = lang === 'en' ? 'English' : 'हिंदी';
  }

  // Refresh dynamic containers
  renderMenuGrid();
  renderCartDrawer();
}

function translateUnit(unit) {
  if (currentLang === 'hi') {
    if (unit === 'Per Kg') return 'प्रति किलोग्राम';
    if (unit === 'Per Pkt') return 'प्रति पैकेट';
    if (unit === '250 Grams') return '२५० ग्राम';
    if (unit === 'Full Plate') return 'फुल प्लेट';
  }
  return unit;
}

// ==========================================
// MENU OPERATIONS
// ==========================================
async function fetchMenu() {
  try {
    const res = await fetch('/api/menu');
    if (!res.ok) throw new Error('Failed to fetch menu');
    menuData = await res.json();
    renderMenuGrid();
  } catch (error) {
    console.error('Menu load error:', error);
    menuGrid.innerHTML = `
      <div class="loading-state text-primary">
        <p>⚠️ Failed to load chicken menu. Please refresh the page or run node server.js.</p>
      </div>
    `;
  }
}

function renderMenuGrid() {
  if (!menuData.length) return;

  const filtered = currentCategory === 'all' 
    ? menuData 
    : menuData.filter(item => item.category === currentCategory);

  if (!filtered.length) {
    menuGrid.innerHTML = '<p class="text-center pad-20">No items available in this category.</p>';
    return;
  }

  menuGrid.innerHTML = filtered.map(item => {
    const cartItem = cart.find(c => c.id === item.id);
    const qty = cartItem ? cartItem.quantity : 0;
    
    const itemName = currentLang === 'hi' ? (item.nameHi || item.name) : item.name;
    const itemDesc = currentLang === 'hi' ? (item.descriptionHi || item.description) : item.description;
    const itemUnit = translateUnit(item.unit);
    
    const fallbackImage = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24"><rect width="100%" height="100%" fill="%23c8102e"/><text x="50%" y="55%" font-family="sans-serif" font-size="12" font-weight="bold" fill="white" text-anchor="middle">BCP MEAT</text></svg>`;

    return `
      <div class="menu-card" data-id="${item.id}">
        <div class="card-img-wrapper">
          <img src="${item.image}" alt="${itemName}" class="card-img" onerror="this.onerror=null; this.src='${fallbackImage}';">
          ${item.category === 'specials' ? `<span class="card-tag">${currentLang === 'hi' ? 'विशेष व्यंजन' : 'Chef Special'}</span>` : ''}
          ${item.category === 'raw' && item.id.includes('mutton') ? `<span class="card-tag" style="background:#8d6e63; color:white;">${currentLang === 'hi' ? 'मटन' : 'Mutton'}</span>` : ''}
        </div>
        <div class="card-info">
          <h3>${itemName}</h3>
          <p class="desc">${itemDesc}</p>
          <div class="card-footer">
            <div class="card-price">
              <span class="amt">₹${item.price}</span>
              <span class="unit">${itemUnit}</span>
            </div>
            
            <div class="card-actions">
              ${qty > 0 ? `
                <div class="qty-selector">
                  <button class="qty-btn minus" onclick="updateQty('${item.id}', -1)">-</button>
                  <span class="qty-val">${qty}</span>
                  <button class="qty-btn plus" onclick="updateQty('${item.id}', 1)">+</button>
                </div>
              ` : `
                <button class="btn btn-primary btn-small" onclick="addToCart('${item.id}')">🛒 ${currentLang === 'hi' ? 'जोड़ें' : 'Add to Basket'}</button>
              `}
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ==========================================
// CART OPERATIONS
// ==========================================
function addToCart(itemId) {
  const item = menuData.find(m => m.id === itemId);
  if (!item) return;

  const existing = cart.find(c => c.id === itemId);
  if (existing) {
    existing.quantity += 1;
  } else {
    cart.push({
      id: item.id,
      name: item.name,
      nameHi: item.nameHi || item.name,
      price: item.price,
      unit: item.unit,
      quantity: 1
    });
  }

  saveCartToStorage();
  renderMenuGrid();
  renderCartDrawer();
  updateCartBadge();
  
  cartBtn.style.transform = 'scale(1.2)';
  setTimeout(() => cartBtn.style.transform = '', 200);
}

function updateQty(itemId, change) {
  const cartItem = cart.find(c => c.id === itemId);
  if (!cartItem) return;

  cartItem.quantity += change;
  if (cartItem.quantity <= 0) {
    cart = cart.filter(c => c.id !== itemId);
  }

  saveCartToStorage();
  renderMenuGrid();
  renderCartDrawer();
  updateCartBadge();
}

function removeFromCart(itemId) {
  cart = cart.filter(c => c.id !== itemId);
  saveCartToStorage();
  renderMenuGrid();
  renderCartDrawer();
  updateCartBadge();
}

function updateCartBadge() {
  const count = cart.reduce((sum, item) => sum + item.quantity, 0);
  cartCount.textContent = count;
  if (count > 0) {
    cartCount.classList.remove('hidden');
  } else {
    cartCount.classList.add('hidden');
  }
}

function renderCartDrawer() {
  if (cart.length === 0) {
    cartItemsContainer.innerHTML = `
      <div class="empty-cart-state">
        <span>🛒</span>
        <p data-translate="cart-empty-msg">${translations[currentLang]["cart-empty-msg"]}</p>
        <button class="btn btn-primary" onclick="closeCart()" data-translate="cart-start-shopping">${translations[currentLang]["cart-start-shopping"]}</button>
      </div>
    `;
    checkoutForm.classList.add('hidden');
    cartFooter.classList.add('hidden');
    return;
  }

  // Populate items
  cartItemsContainer.innerHTML = cart.map(item => {
    const displayName = currentLang === 'hi' ? (item.nameHi || item.name) : item.name;
    const displayUnit = translateUnit(item.unit);
    
    return `
      <div class="cart-item">
        <div class="cart-item-info">
          <h4>${displayName}</h4>
          <span>₹${item.price} ${displayUnit} x ${item.quantity}</span>
        </div>
        <div class="qty-selector">
          <button class="qty-btn minus" onclick="updateQty('${item.id}', -1)">-</button>
          <span class="qty-val">${item.quantity}</span>
          <button class="qty-btn plus" onclick="updateQty('${item.id}', 1)">+</button>
        </div>
        <div class="cart-item-price">₹${item.price * item.quantity}</div>
        <button class="remove-item-btn" onclick="removeFromCart('${item.id}')">&times;</button>
      </div>
    `;
  }).join('');

  // Update total
  const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  billSubtotal.textContent = `₹${subtotal}`;
  billTotal.textContent = `₹${subtotal}`;

  checkoutForm.classList.remove('hidden');
  cartFooter.classList.remove('hidden');
}

function openCart() {
  cartDrawer.classList.add('open');
  cartBackdrop.classList.add('open');
}

function closeCart() {
  cartDrawer.classList.remove('open');
  cartBackdrop.classList.remove('open');
}

function saveCartToStorage() {
  localStorage.setItem('bcp_cart', JSON.stringify(cart));
}

function loadCartFromStorage() {
  const stored = localStorage.getItem('bcp_cart');
  if (stored) {
    try {
      cart = JSON.parse(stored);
      updateCartBadge();
    } catch (e) {
      cart = [];
    }
  }
}

// ==========================================
// CHECKOUT & UPI PAYMENTS
// ==========================================
async function submitCheckout(e) {
  e.preventDefault();
  
  if (!cart.length) return;

  const name = document.getElementById('cust-name').value.trim();
  const phone = document.getElementById('cust-phone').value.trim();
  const email = document.getElementById('cust-email').value.trim();
  const address = document.getElementById('cust-address').value.trim();

  if (!name || !phone || !address) {
    alert(currentLang === 'hi' ? 'कृपया सभी आवश्यक फ़ील्ड भरें।' : 'Please fill out all required fields.');
    return;
  }

  showGlobalLoader(currentLang === 'hi' ? 'ऑर्डर बनाया जा रहा है...' : 'Creating order...');

  try {
    const response = await fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        customerName: name,
        customerPhone: phone,
        customerEmail: email,
        deliveryAddress: address,
        items: cart.map(c => ({ id: c.id, quantity: c.quantity }))
      })
    });

    const data = await response.json();
    hideGlobalLoader();

    if (!response.ok) {
      alert(data.error || 'Failed to submit order.');
      return;
    }

    // Launch UPI Payment Modal
    openUpiPaymentModal(data);
  } catch (error) {
    hideGlobalLoader();
    console.error('Order creation error:', error);
    alert('Failed to connect to order server. Make sure node backend is running.');
  }
}

function openUpiPaymentModal(orderData) {
  activeOrderId = orderData.orderId;
  upiModalAmount.textContent = `₹${orderData.totalAmount.toFixed(2)}`;
  
  // Reset QR toggle view states
  if (qrToggleDynamic) qrToggleDynamic.classList.add('active');
  if (qrToggleStatic) qrToggleStatic.classList.remove('active');
  if (upiQrCodeImg) upiQrCodeImg.classList.remove('hidden');
  if (upiStaticQrImg) upiStaticQrImg.classList.add('hidden');
  if (qrCodeWrapper) qrCodeWrapper.classList.remove('static-view');
  if (upiInstructions) {
    upiInstructions.setAttribute('data-translate', 'upi-instructions');
    upiInstructions.textContent = translations[currentLang]['upi-instructions'];
  }
  
  // Set QR code link via free qrserver API
  upiQrCodeImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&margin=10&data=${encodeURIComponent(orderData.upiPaymentLink)}`;
  qrLoader.classList.remove('hidden');

  upiQrCodeImg.onload = () => {
    qrLoader.classList.add('hidden');
  };

  // Set mobile deep link
  upiMobileLink.href = orderData.upiPaymentLink;

  // Reset verification input
  upiUtr.value = '';
  verifyPaymentBtn.disabled = false;
  verifyBtnText.textContent = translations[currentLang]["upi-verify-btn"];
  verifyBtnSpinner.classList.add('hidden');

  // Open modal
  upiModal.classList.add('open');
  closeCart();
}

function generateMockUtr() {
  const timestamp = Date.now().toString().slice(-4);
  const random = Math.floor(10000000 + Math.random() * 90000000).toString();
  upiUtr.value = timestamp + random;
}

async function verifyPayment() {
  const utr = upiUtr.value.trim();

  if (!utr || utr.length !== 12 || isNaN(utr)) {
    alert(currentLang === 'hi' ? 'कृपया एक मान्य 12-अंकीय ट्रांजेक्शन यूटीआर दर्ज करें।' : 'Please enter a valid 12-digit transaction UTR reference number.');
    return;
  }

  verifyPaymentBtn.disabled = true;
  verifyBtnText.textContent = currentLang === 'hi' ? 'भुगतान सत्यापित किया जा रहा है...' : 'Verifying Payment...';
  verifyBtnSpinner.classList.remove('hidden');

  try {
    const res = await fetch(`/api/orders/${activeOrderId}/verify-payment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        utr: utr,
        paymentMethod: 'UPI'
      })
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || 'Payment verification failed.');
    }

    // Success! Clear Cart and Close Modal
    cart = [];
    saveCartToStorage();
    updateCartBadge();
    renderMenuGrid();
    
    upiModal.classList.remove('open');
    showSuccessScreen(data.order);
  } catch (error) {
    alert(error.message);
    verifyPaymentBtn.disabled = false;
    verifyBtnText.textContent = translations[currentLang]["upi-verify-btn"];
    verifyBtnSpinner.classList.add('hidden');
  }
}

function showSuccessScreen(order) {
  successOrderId.textContent = order.id;
  successCustName.textContent = order.customerName;
  successCustPhone.textContent = order.customerPhone;
  successCustAddress.textContent = order.deliveryAddress;
  successUtr.textContent = order.paymentDetails.utr;
  successAmount.textContent = `₹${order.totalAmount}`;
  
  successScreen.classList.remove('hidden');
}

// ==========================================
// VENDOR PORTAL - AUTHENTICATION
// ==========================================
function submitAdminLogin(e) {
  e.preventDefault();
  
  const userInp = document.getElementById('admin-user').value.trim();
  const passInp = document.getElementById('admin-pass').value.trim();
  const loginErrorMsg = document.getElementById('loginErrorMsg');

  // Hardcoded check for admin/admin
  if (userInp === 'admin' && passInp === 'admin') {
    loginErrorMsg.classList.add('hidden');
    isAdminAuthenticated = true;
    sessionStorage.setItem('bcp_admin_auth', 'true');
    
    // Reload active view hash layout
    checkViewFromHash();
  } else {
    loginErrorMsg.classList.remove('hidden');
  }
}

function logoutAdmin() {
  isAdminAuthenticated = false;
  sessionStorage.removeItem('bcp_admin_auth');
  window.location.hash = ''; // redirect to storefront home
}

// ==========================================
// ADMIN DASHBOARD
// ==========================================
async function loadAdminDashboard() {
  showGlobalLoader('Fetching vendor stats...');
  try {
    await Promise.all([
      fetchAdminOrders(),
      fetchEmailLogs()
    ]);
  } catch (error) {
    console.error('Failed to load dashboard data:', error);
  } finally {
    hideGlobalLoader();
  }
}

async function fetchAdminOrders() {
  try {
    const res = await fetch('/api/admin/orders');
    if (!res.ok) throw new Error();
    const orders = await res.json();
    renderAdminOrders(orders);
    calculateStats(orders);
  } catch (error) {
    alert('Failed to load orders for vendor dashboard.');
  }
}

function renderAdminOrders(orders) {
  if (!orders.length) {
    adminOrdersTableBody.innerHTML = `
      <tr>
        <td colspan="8" class="text-center pad-20">No orders received yet. Wait for customer purchases.</td>
      </tr>
    `;
    return;
  }

  adminOrdersTableBody.innerHTML = orders.map(order => {
    const itemsText = order.items.map(i => {
      const name = currentLang === 'hi' ? (i.nameHi || i.name) : i.name;
      return `<li>• ${name} (${i.quantity} qty)</li>`;
    }).join('');
    
    const time = new Date(order.createdAt).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });

    const payment = order.paymentDetails 
      ? `<strong>${order.paymentDetails.method}</strong><br><span style="font-size:0.75rem; color:#666">UTR: ${order.paymentDetails.utr}</span>`
      : `<span class="text-primary">Unpaid</span>`;

    const statuses = ['Pending Payment', 'Paid', 'Cooking', 'Out for Delivery', 'Delivered', 'Cancelled'];
    const options = statuses.map(s => `
      <option value="${s}" ${order.status === s ? 'selected' : ''}>${s}</option>
    `).join('');

    let badgeClass = 'pending';
    if (order.status === 'Paid') badgeClass = 'paid';
    if (order.status === 'Cooking') badgeClass = 'cooking';
    if (order.status === 'Out for Delivery') badgeClass = 'shipping';
    if (order.status === 'Delivered') badgeClass = 'delivered';
    if (order.status === 'Cancelled') badgeClass = 'cancelled';

    return `
      <tr>
        <td><strong>${order.id}</strong><br><span style="font-size:0.75rem; color:#777">${time}</span></td>
        <td>
          <strong>${order.customerName}</strong><br>
          <a href="tel:${order.customerPhone}" style="color:var(--primary)">${order.customerPhone}</a><br>
          <span style="font-size:0.8rem;color:#555">${order.customerEmail}</span>
        </td>
        <td><div style="max-width: 150px; font-size: 0.85rem;">${order.deliveryAddress}</div></td>
        <td>
          <ul style="margin: 0; padding: 0;">${itemsText}</ul>
        </td>
        <td><strong style="color:var(--primary)">₹${order.totalAmount}</strong></td>
        <td>${payment}</td>
        <td><span class="badge ${badgeClass}">${order.status}</span></td>
        <td>
          <select class="form-control" onchange="updateOrderStatus('${order.id}', this.value)">
            ${options}
          </select>
        </td>
      </tr>
    `;
  }).join('');
}

async function updateOrderStatus(orderId, newStatus) {
  showGlobalLoader('Updating order status...');
  try {
    const res = await fetch(`/api/admin/orders/${orderId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    if (!res.ok) throw new Error();
    await fetchAdminOrders();
  } catch (error) {
    alert('Failed to update status.');
  } finally {
    hideGlobalLoader();
  }
}

function calculateStats(orders) {
  statTotal.textContent = orders.length;
  statPending.textContent = orders.filter(o => o.status === 'Pending Payment').length;
  statPaid.textContent = orders.filter(o => ['Paid', 'Cooking', 'Out for Delivery'].includes(o.status)).length;
  statDelivered.textContent = orders.filter(o => o.status === 'Delivered').length;
}

// ==========================================
// ADMIN EMAIL LOGS
// ==========================================
async function fetchEmailLogs() {
  try {
    const res = await fetch('/api/admin/emails');
    if (!res.ok) throw new Error();
    const emails = await res.json();
    renderEmailLogs(emails);
  } catch (error) {
    console.error('Failed to fetch emails', error);
  }
}

let loggedEmails = [];
function renderEmailLogs(emails) {
  loggedEmails = emails;
  if (!emails.length) {
    emailInboxList.innerHTML = '<p class="text-center pad-20">No email logs found. Place orders first!</p>';
    return;
  }

  emailInboxList.innerHTML = emails.map((email, idx) => {
    const time = new Date(email.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
    const isVendor = email.subject.includes('NEW ORDER');
    const badgeColor = isVendor ? '#1a1a1a' : '#c8102e';
    const recipientName = isVendor ? 'Vendor' : 'Customer';

    return `
      <div class="email-item" data-index="${idx}" onclick="selectEmail(${idx})">
        <div class="email-item-header">
          <span style="background:${badgeColor}; color:white; padding:1px 4px; border-radius:3px; font-weight:800; font-size:0.65rem">${recipientName}</span>
          <span>${time}</span>
        </div>
        <div class="email-item-to">${email.to}</div>
        <div class="email-item-subject">${email.subject}</div>
      </div>
    `;
  }).join('');
}

function selectEmail(idx) {
  document.querySelectorAll('.email-item').forEach(el => el.classList.remove('active'));
  const clicked = document.querySelector(`.email-item[data-index="${idx}"]`);
  if (clicked) clicked.classList.add('active');

  const email = loggedEmails[idx];
  const dateStr = new Date(email.timestamp).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });

  emailReadingPane.innerHTML = `
    <div class="email-pane-header">
      <h3>${email.subject}</h3>
      <div class="email-metadata">
        <div><strong>To:</strong> ${email.to}</div>
        <div><strong>Date:</strong> ${dateStr}</div>
        <div><strong>Sender Service:</strong> ${email.mode}</div>
      </div>
    </div>
    <div class="email-render-wrapper">
      ${email.body}
    </div>
  `;
}

// SMTP Settings Saving
async function saveSmtpSettings(e) {
  e.preventDefault();
  
  const host = document.getElementById('smtp-host').value.trim();
  const port = document.getElementById('smtp-port').value.trim();
  const user = document.getElementById('smtp-user').value.trim();
  const pass = document.getElementById('smtp-pass').value.trim();
  const isEnabled = document.getElementById('smtp-enabled').checked;
  const vendorEmail = document.getElementById('smtp-vendor').value.trim();

  showGlobalLoader('Saving config...');

  try {
    const res = await fetch('/api/admin/config/smtp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        host, port, user, pass, isEnabled, vendorEmail
      })
    });
    
    const data = await res.json();
    hideGlobalLoader();

    if (!res.ok) throw new Error(data.error);
    alert('SMTP Settings successfully updated!');
  } catch (error) {
    hideGlobalLoader();
    alert('Failed to save settings: ' + error.message);
  }
}

// ==========================================
// EVENT LISTENERS CONFIG
// ==========================================
function setupEventListeners() {
  // Language Switch trigger
  const langToggleBtn = document.getElementById('langToggleBtn');
  if (langToggleBtn) {
    langToggleBtn.addEventListener('click', () => {
      const nextLang = currentLang === 'en' ? 'hi' : 'en';
      setLanguage(nextLang);
    });
  }

  // Admin Auth triggers
  const adminLoginForm = document.getElementById('adminLoginForm');
  if (adminLoginForm) {
    adminLoginForm.addEventListener('submit', submitAdminLogin);
  }

  const adminLogoutBtn = document.getElementById('adminLogoutBtn');
  if (adminLogoutBtn) {
    adminLogoutBtn.addEventListener('click', logoutAdmin);
  }

  // Cart toggle
  cartBtn.addEventListener('click', openCart);
  closeCartBtn.addEventListener('click', closeCart);
  cartBackdrop.addEventListener('click', closeCart);

  // Close UPI Payment Modal
  closeUpiBtn.addEventListener('click', () => {
    if (confirm(currentLang === 'hi' ? 'क्या आप वाकई चेकआउट बंद करना चाहते हैं? आपका पेंडिंग ऑर्डर रद्द कर दिया जाएगा।' : 'Are you sure you want to exit checkout? Your pending order will be cancelled.')) {
      upiModal.classList.remove('open');
    }
  });

  // Verify UPI input
  mockUtrBtn.addEventListener('click', generateMockUtr);
  verifyPaymentBtn.addEventListener('click', verifyPayment);

  // Checkout submission
  checkoutForm.addEventListener('submit', submitCheckout);
  submitCheckoutBtn.addEventListener('click', () => {
    checkoutForm.requestSubmit();
  });

  // QR Code toggle handlers
  if (qrToggleDynamic && qrToggleStatic) {
    qrToggleDynamic.addEventListener('click', () => {
      qrToggleDynamic.classList.add('active');
      qrToggleStatic.classList.remove('active');
      upiQrCodeImg.classList.remove('hidden');
      upiStaticQrImg.classList.add('hidden');
      qrCodeWrapper.classList.remove('static-view');
      qrLoader.classList.add('hidden');

      // Update instructions
      upiInstructions.setAttribute('data-translate', 'upi-instructions');
      upiInstructions.textContent = translations[currentLang]['upi-instructions'];
    });

    qrToggleStatic.addEventListener('click', () => {
      qrToggleStatic.classList.add('active');
      qrToggleDynamic.classList.remove('active');
      upiQrCodeImg.classList.add('hidden');
      upiStaticQrImg.classList.remove('hidden');
      qrCodeWrapper.classList.add('static-view');
      qrLoader.classList.add('hidden');

      // Update instructions
      upiInstructions.setAttribute('data-translate', 'upi-instructions-static');
      upiInstructions.textContent = translations[currentLang]['upi-instructions-static'];
    });
  }

  // Success overlay buttons
  successHomeBtn.addEventListener('click', () => {
    successScreen.classList.add('hidden');
    window.location.hash = '';
  });
  
  successAdminBtn.addEventListener('click', () => {
    successScreen.classList.add('hidden');
    window.location.hash = '#admin';
  });

  // Category filter tabs
  const tabBtns = document.querySelectorAll('.tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      tabBtns.forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      currentCategory = e.target.getAttribute('data-category');
      renderMenuGrid();
    });
  });

  // Refresh admin tables
  refreshOrdersBtn.addEventListener('click', fetchAdminOrders);

  // Admin Dashboard Tabs
  const adminTabBtns = document.querySelectorAll('.admin-tab-btn');
  const adminTabContents = document.querySelectorAll('.admin-tab-content');

  adminTabBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      adminTabBtns.forEach(b => b.classList.remove('active'));
      adminTabContents.forEach(c => c.classList.remove('active'));
      
      e.target.classList.add('active');
      const tabId = e.target.getAttribute('data-tab');
      document.getElementById(tabId).classList.add('active');
    });
  });

  // SMTP form submission
  smtpSettingsForm.addEventListener('submit', saveSmtpSettings);
}
