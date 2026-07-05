const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const nodemailer = require('nodemailer');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Enable CORS and JSON parsing
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve static files from 'public' directory
app.use(express.static(path.join(__dirname, 'public')));

// Database File Paths
const ORDERS_FILE = path.join(__dirname, 'orders.json');
const EMAIL_LOGS_FILE = path.join(__dirname, 'email_logs.json');

// Initialize local JSON files if they don't exist
if (!fs.existsSync(ORDERS_FILE)) {
  fs.writeFileSync(ORDERS_FILE, JSON.stringify([], null, 2));
}
if (!fs.existsSync(EMAIL_LOGS_FILE)) {
  fs.writeFileSync(EMAIL_LOGS_FILE, JSON.stringify([], null, 2));
}

// Read database helper
function readDB(filePath) {
  try {
    const data = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error(`Error reading ${filePath}:`, error);
    return [];
  }
}

// Write database helper
function writeDB(filePath, data) {
  try {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
    return true;
  } catch (error) {
    console.error(`Error writing ${filePath}:`, error);
    return false;
  }
}

// Menu Items (Categorized and priced directly from shop displays in 3.jpg, 4.jpg, 5.jpg)
const MENU = [
  // Raw items (sold by weight)
  {
    id: 'fresh_chicken',
    name: 'Fresh Chicken (Whole Cut)',
    nameHi: 'ताजा चिकन (साबुत कट)',
    category: 'raw',
    price: 220,
    unit: 'Per Kg',
    description: 'Clean, fresh whole chicken cut to your preference (curry cut, biryani cut, etc.).',
    descriptionHi: 'आपकी पसंद के अनुसार काटा गया ताजा चिकन (करी कट, बिरयानी कट, आदि)।',
    image: 'assets/fresh_chicken.jpg'
  },
  {
    id: 'breast_boneless',
    name: 'Breast Boneless Chicken',
    nameHi: 'ब्रेस्ट बोनलेस चिकन',
    category: 'raw',
    price: 260,
    unit: 'Per Kg',
    description: 'Fresh, skinless, boneless chicken breast meat. Extremely lean and tender.',
    descriptionHi: 'ताजा, बिना त्वचा और बिना हड्डी वाला चिकन ब्रेस्ट मीट। बहुत ही हल्का और कोमल।',
    image: 'assets/breast_boneless.jpg'
  },
  {
    id: 'thai_boneless',
    name: 'Thai Boneless Chicken',
    nameHi: 'थाई बोनलेस चिकन',
    category: 'raw',
    price: 320,
    unit: 'Per Kg',
    description: 'Juicy, boneless chicken thigh pieces, perfect for grilling, frying, or tikka.',
    descriptionHi: 'चिकन जांघ के रसीले टुकड़े, तंदूरी, फ्राइंग या तिक्का बनाने के लिए एकदम सही।',
    image: 'assets/thai_boneless.jpg'
  },
  {
    id: 'chicken_tangri',
    name: 'Chicken Tangri (Drumsticks)',
    nameHi: 'चिकन टांगड़ी (लेग पीस)',
    category: 'raw',
    price: 260,
    unit: 'Per Kg',
    description: 'Cleaned chicken drumsticks, ready for marination and tandoori cooking.',
    descriptionHi: 'साफ की हुई चिकन टांगड़ी (ड्रमस्टिक्स), मैरीनेशन और तंदूरी कुकिंग के लिए तैयार।',
    image: 'assets/chicken_tangri.jpg'
  },
  {
    id: 'chicken_wings',
    name: 'Chicken Wings',
    nameHi: 'चिकन विंग्स (पंख)',
    category: 'raw',
    price: 260,
    unit: 'Per Kg',
    description: 'Clean chicken wings, ideal for spicy wings fry or barbecue.',
    descriptionHi: 'साफ चिकन विंग्स, मसालेदार विंग्स फ्राई या बारबेक्यू के लिए एकदम सही।',
    image: 'assets/chicken_wings.jpg'
  },
  {
    id: 'chicken_keema',
    name: 'Chicken Keema (Minced)',
    nameHi: 'चिकन कीमा',
    category: 'raw',
    price: 260,
    unit: 'Per Kg',
    description: 'Premium quality minced chicken, freshly prepared, low-fat.',
    descriptionHi: 'प्रीमियम गुणवत्ता वाला कीमा चिकन, ताजा तैयार किया हुआ और कम वसा वाला।',
    image: 'assets/chicken_keema.jpg'
  },
  {
    id: 'chicken_full_leg',
    name: 'Chicken Full Leg Quarter',
    nameHi: 'चिकन फुल लेग क्वार्टर',
    category: 'raw',
    price: 280,
    unit: 'Per Kg',
    description: 'Full leg quarters containing both the thigh and the drumstick.',
    descriptionHi: 'साबुत चिकन लेग पीस जिसमें जांघ और टांग दोनों भाग शामिल हैं।',
    image: 'assets/chicken_full_leg.jpg'
  },
  {
    id: 'fresh_mutton',
    name: 'Fresh Mutton (Goat Meat)',
    nameHi: 'ताजा मटन (बकरे का मीट)',
    category: 'raw',
    price: 700,
    unit: 'Per Kg',
    description: 'Premium, tender fresh goat meat. Sourced daily and hygienically cut.',
    descriptionHi: 'प्रीमियम और कोमल बकरे का मीट, रोजाना ताजा और स्वच्छता से कटा हुआ।',
    image: 'assets/fresh_mutton.jpg'
  },

  // Ready to Eat / Cooked / Semi-cooked items
  {
    id: 'mutton_kabab',
    name: 'Mutton Seekh Kabab',
    nameHi: 'मटन सीख कबाब',
    category: 'ready',
    price: 350,
    unit: 'Per Pkt',
    description: 'Authentic spiced minced mutton skewers, ready to grill, pan-fry, or eat.',
    descriptionHi: 'स्वादिष्ट मसालेदार पिसा हुआ मटन कबाब सीक, तलने या ग्रिल करने के लिए तैयार।',
    image: 'assets/mutton_kabab.jpg'
  },
  {
    id: 'chicken_salami',
    name: 'Chicken Salami',
    nameHi: 'चिकन सलामी',
    category: 'ready',
    price: 180,
    unit: 'Per Pkt',
    description: 'Deliciously sliced chicken cold-cut salami, mildly seasoned.',
    descriptionHi: 'स्वादिष्ट कटी हुई चिकन सलामी, हल्के मसालों के साथ सीजन की हुई।',
    image: 'assets/chicken_salami.jpg'
  },
  {
    id: 'spicy_salami',
    name: 'Spicy Chicken Salami',
    nameHi: 'तीखी चिकन सलामी',
    category: 'ready',
    price: 180,
    unit: 'Per Pkt',
    description: 'Sliced chicken salami loaded with red chili flakes and spices.',
    descriptionHi: 'लाल मिर्च के फ्लेक्स और तीखे मसालों से भरपूर चिकन सलामी स्लाइस।',
    image: 'assets/spicy_salami.jpg'
  },
  {
    id: 'chicken_nuggets',
    name: 'Chicken Nuggets',
    nameHi: 'चिकन नगेट्स',
    category: 'ready',
    price: 250,
    unit: 'Per Pkt',
    description: 'Golden, crispy, breaded chicken nuggets. Store and fry as needed.',
    descriptionHi: 'सुनहरे, कुरकुरे और ब्रेड क्रम्ब्स वाले चिकन नगेट्स। घर पर तलने के लिए तैयार।',
    image: 'assets/chicken_nuggets.jpg'
  },
  {
    id: 'angara_kabab',
    name: 'Angara Chicken Kabab',
    nameHi: 'अंगारा चिकन कबाब',
    category: 'ready',
    price: 250,
    unit: 'Per Pkt',
    description: 'Spicy chicken seekh kababs marinated in fiery red Angara spices.',
    descriptionHi: 'तीखे लाल अंगारा मसालों में मैरीनेट किया हुआ चिकन सीख कबाब।',
    image: 'assets/angara_kabab.jpg'
  },
  {
    id: 'mughlai_kabab',
    name: 'Mughlai Chicken Kabab',
    nameHi: 'मुगलई चिकन कबाब',
    category: 'ready',
    price: 250,
    unit: 'Per Pkt',
    description: 'Creamy, rich, and mildly flavored chicken seekh kababs in royal Mughlai marinade.',
    descriptionHi: 'शाही मलाईदार और बेहद कोमल मुगलई मैरीनेशन से तैयार चिकन सीख कबाब।',
    image: 'assets/mughlai_kabab.jpg'
  },
  {
    id: 'peri_peri_kabab',
    name: 'Peri-Peri Chicken Kabab',
    nameHi: 'पेरी-पेरी चिकन कबाब',
    category: 'ready',
    price: 250,
    unit: 'Per Pkt',
    description: 'Zesty and tangy chicken kababs marinated in citrusy African Peri-Peri sauce.',
    descriptionHi: 'चटपटे और तीखे अफ्रीकी पेरी-पेरी सॉस से मैरीनेट किया हुआ चिकन कबाब।',
    image: 'assets/peri_peri_kabab.jpg'
  },
  {
    id: 'malai_kabab',
    name: 'Malai Chicken Kabab',
    nameHi: 'मलाई चिकन कबाब',
    category: 'ready',
    price: 250,
    unit: 'Per Pkt',
    description: 'Extremely soft, melt-in-the-mouth chicken kababs with rich cream and cheese.',
    descriptionHi: 'अत्यंत कोमल, मुंह में घुलने वाले मलाईदार और चीजी चिकन कबाब।',
    image: 'assets/malai_kabab.jpg'
  },
  {
    id: 'achari_kabab',
    name: 'Achari Chicken Kabab',
    nameHi: 'अचारी चिकन कबाब',
    category: 'ready',
    price: 250,
    unit: 'Per Pkt',
    description: 'Tender chicken kababs with the tangy, savory flavors of traditional Indian pickle.',
    descriptionHi: 'चिकन कबाब जिसमें भारतीय मसालों और खट्टे अचार का चटपटा स्वाद है।',
    image: 'assets/achari_kabab.jpg'
  },
  {
    id: 'cheesy_onion_kabab',
    name: 'Cheesy Onion Chicken Kabab',
    nameHi: 'चीजी अनियन चिकन कबाब',
    category: 'ready',
    price: 250,
    unit: 'Per Pkt',
    description: 'Succulent chicken kababs stuffed with mozzarella cheese and sweet onions.',
    descriptionHi: 'मोज़ेरेला चीज़ और मीठे प्याज के टुकड़ों से भरा रसीला चिकन कबाब।',
    image: 'assets/cheesy_onion_kabab.jpg'
  },

  // Prepared hot specials
  {
    id: 'karachi_chicken',
    name: 'Karachi Chicken Fry',
    nameHi: 'कराची चिकन फ्राई',
    category: 'specials',
    price: 100,
    unit: '250 Grams',
    description: 'Karachi-style stir fried chicken, cooked with freshly ground whole spices.',
    descriptionHi: 'कराची स्टाइल स्वादिष्ट चिकन फ्राई, ताज़ा पीसे खड़े मसालों के साथ भुना हुआ।',
    image: 'assets/karachi_chicken.jpg'
  },
  {
    id: 'chicken_lollypop',
    name: 'Chicken Lollypop Fry',
    nameHi: 'चिकन लॉलीपॉप फ्राई',
    category: 'specials',
    price: 80,
    unit: '250 Grams',
    description: 'Indo-Chinese style crispy fried chicken drumettes coated in seasoned batter.',
    descriptionHi: 'मसालेदार घोल में लपेटकर गहरा तला हुआ क्रिस्पी इंडो-चाइनीज चिकन विंग्स।',
    image: 'assets/chicken_lollypop.jpg'
  },
  {
    id: 'chicken_fry',
    name: 'Bharat Special Chicken Fry',
    nameHi: 'भारत स्पेशल चिकन फ्राई',
    category: 'specials',
    price: 200,
    unit: 'Full Plate',
    description: 'Our signature crispy, deep-fried chicken marinated in secret traditional spices.',
    descriptionHi: 'हमारा विशेष क्रिस्पी फ्राइड चिकन, पारंपरिक और अनोखे मसालों से मैरीनेटेड।',
    image: 'assets/chicken_fry.jpg'
  }
];

// Helper: Send Email (handles SMTP sending OR saves to JSON log file)
async function sendNotificationEmail({ to, subject, htmlBody, type }) {
  const isSmtpEnabled = process.env.IS_SMTP_ENABLED === 'true';

  if (isSmtpEnabled) {
    try {
      const transporter = nodemailer.createTransport({
        host: process.env.SMTP_HOST,
        port: parseInt(process.env.SMTP_PORT) || 587,
        secure: process.env.SMTP_PORT === '465',
        auth: {
          user: process.env.SMTP_USER,
          pass: process.env.SMTP_PASS
        }
      });

      const mailOptions = {
        from: `"Bharat Chicken Point" <${process.env.SMTP_USER}>`,
        to,
        subject,
        html: htmlBody
      };

      await transporter.sendMail(mailOptions);
      console.log(`Real email sent successfully to ${to} (${type})`);
      
      // Still log it locally for history
      const logs = readDB(EMAIL_LOGS_FILE);
      logs.unshift({
        id: 'L-' + Math.floor(100000 + Math.random() * 900000),
        to,
        subject,
        body: htmlBody,
        timestamp: new Date().toISOString(),
        mode: 'Real SMTP'
      });
      writeDB(EMAIL_LOGS_FILE, logs);

      return true;
    } catch (error) {
      console.error(`Failed to send real email to ${to}:`, error);
      // Fallback to logging locally
    }
  }

  // Fallback / Simulated mode: Log email details to file
  const logs = readDB(EMAIL_LOGS_FILE);
  const logEntry = {
    id: 'L-' + Math.floor(100000 + Math.random() * 900000),
    to,
    subject,
    body: htmlBody,
    timestamp: new Date().toISOString(),
    mode: 'Simulated Log'
  };
  logs.unshift(logEntry);
  writeDB(EMAIL_LOGS_FILE, logs);
  console.log(`[SIMULATED EMAIL LOGGED] To: ${to} | Subject: ${subject}`);
  return true;
}

// Generate Email HTML Templates
function getCustomerEmailTemplate(order) {
  const itemsList = order.items.map(item => `
    <tr>
      <td style="padding: 8px; border-bottom: 1px solid #ddd;">${item.name}</td>
      <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">${item.quantity}</td>
      <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">₹${item.price}</td>
      <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">₹${item.price * item.quantity}</td>
    </tr>
  `).join('');

  return `
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
      <div style="background-color: #c8102e; padding: 15px; text-align: center; border-radius: 6px 6px 0 0;">
        <h2 style="color: white; margin: 0;">Bharat Chicken & Mutton Shop</h2>
      </div>
      <div style="padding: 20px;">
        <h3 style="color: #333;">Order Confirmed!</h3>
        <p>Dear <strong>${order.customerName}</strong>,</p>
        <p>Thank you for placing your order with us. We have received your payment and our kitchen is preparing your items.</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
          <thead>
            <tr style="background-color: #f8f8f8;">
              <th style="padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">Item</th>
              <th style="padding: 8px; text-align: center; border-bottom: 2px solid #ddd;">Qty</th>
              <th style="padding: 8px; text-align: right; border-bottom: 2px solid #ddd;">Price</th>
              <th style="padding: 8px; text-align: right; border-bottom: 2px solid #ddd;">Total</th>
            </tr>
          </thead>
          <tbody>
            ${itemsList}
            <tr>
              <td colspan="3" style="padding: 8px; text-align: right; font-weight: bold;">Grand Total:</td>
              <td style="padding: 8px; text-align: right; font-weight: bold; color: #c8102e;">₹${order.totalAmount}</td>
            </tr>
          </tbody>
        </table>

        <div style="background-color: #fff9e6; border-left: 4px solid #ffc72c; padding: 12px; margin: 20px 0;">
          <h4 style="margin: 0 0 5px 0; color: #7a5f00;">Delivery Details:</h4>
          <p style="margin: 0; font-size: 14px;"><strong>Address:</strong> ${order.deliveryAddress}</p>
          <p style="margin: 5px 0 0 0; font-size: 14px;"><strong>Phone:</strong> ${order.customerPhone}</p>
        </div>

        <p style="font-size: 14px; color: #666;">If you have any questions, feel free to call us at <strong>9899946076</strong> or <strong>9560569646</strong>.</p>
        <p style="margin-top: 30px; font-size: 12px; text-align: center; color: #999;">S-10, Private Colony, Sriniwaspuri, New Delhi - 110065</p>
      </div>
    </div>
  `;
}

function getVendorEmailTemplate(order) {
  const itemsList = order.items.map(item => `
    <tr>
      <td style="padding: 8px; border-bottom: 1px solid #ddd;">${item.name}</td>
      <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">${item.quantity}</td>
      <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">₹${item.price}</td>
      <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">₹${item.price * item.quantity}</td>
    </tr>
  `).join('');

  return `
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px; border-top: 5px solid #ffc72c;">
      <div style="background-color: #1a1a1a; padding: 15px; text-align: center; border-radius: 6px 6px 0 0;">
        <h2 style="color: #ffc72c; margin: 0;">NEW ORDER RECEIVED!</h2>
        <span style="color: #fff; font-size: 12px;">Order ID: ${order.id}</span>
      </div>
      <div style="padding: 20px;">
        <h3 style="color: #c8102e; border-bottom: 1px solid #eee; padding-bottom: 8px;">Order Details</h3>
        <p><strong>Customer:</strong> ${order.customerName}</p>
        <p><strong>Phone:</strong> <a href="tel:${order.customerPhone}">${order.customerPhone}</a></p>
        <p><strong>Email:</strong> ${order.customerEmail}</p>
        <p><strong>Address:</strong> ${order.deliveryAddress}</p>
        <p><strong>Time:</strong> ${new Date(order.createdAt).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}</p>

        <h3 style="color: #c8102e; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-top: 20px;">Items Ordered</h3>
        <table style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr style="background-color: #f8f8f8;">
              <th style="padding: 8px; text-align: left;">Item</th>
              <th style="padding: 8px; text-align: center;">Qty</th>
              <th style="padding: 8px; text-align: right;">Price</th>
              <th style="padding: 8px; text-align: right;">Total</th>
            </tr>
          </thead>
          <tbody>
            ${itemsList}
            <tr style="font-weight: bold;">
              <td colspan="3" style="padding: 8px; text-align: right;">Total Amount Paid:</td>
              <td style="padding: 8px; text-align: right; color: #c8102e;">₹${order.totalAmount}</td>
            </tr>
          </tbody>
        </table>

        <div style="background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 12px; margin-top: 20px; border-radius: 4px;">
          <h4 style="margin: 0 0 5px 0; color: #2e7d32;">Payment Details (UPI):</h4>
          <p style="margin: 0; font-size: 14px;"><strong>Status:</strong> Success (PAID)</p>
          <p style="margin: 3px 0 0 0; font-size: 14px;"><strong>Payment Method:</strong> ${order.paymentDetails?.method || 'UPI'}</p>
          <p style="margin: 3px 0 0 0; font-size: 14px;"><strong>Transaction UTR/Reference:</strong> ${order.paymentDetails?.utr || 'N/A'}</p>
        </div>

        <div style="margin-top: 30px; text-align: center;">
          <a href="http://localhost:3000/#admin" style="background-color: #c8102e; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold;">Open Vendor Dashboard</a>
        </div>
      </div>
    </div>
  `;
}

// ==========================================
// API ROUTES
// ==========================================

// Get Menu Items
app.get('/api/menu', (req, res) => {
  res.json(MENU);
});

// Create Order (returns order context and UPI link details)
app.post('/api/orders', (req, res) => {
  const { customerName, customerPhone, customerEmail, deliveryAddress, items } = req.body;

  if (!customerName || !customerPhone || !deliveryAddress || !items || !items.length) {
    return res.status(400).json({ error: 'Missing required checkout information.' });
  }

  // Calculate prices based on official menu server-side to prevent client tampering
  let calculatedItems = [];
  let totalAmount = 0;

  for (const clientItem of items) {
    const menuItem = MENU.find(m => m.id === clientItem.id);
    if (!menuItem) {
      return res.status(400).json({ error: `Invalid menu item ID: ${clientItem.id}` });
    }
    const itemTotal = menuItem.price * clientItem.quantity;
    totalAmount += itemTotal;
    calculatedItems.push({
      id: menuItem.id,
      name: menuItem.name,
      price: menuItem.price,
      unit: menuItem.unit,
      quantity: clientItem.quantity
    });
  }

  const orderId = 'BCP-' + Math.floor(100000 + Math.random() * 900000);
  const upiId = process.env.UPI_ID || '9899946076@okbizaxis';
  const merchantName = process.env.MERCHANT_NAME || 'Bharat Chicken Point';

  // Construct UPI deep link
  // upi://pay?pa=recipient@upi&pn=MerchantName&am=Amount&cu=INR&tn=Note
  const upiString = `upi://pay?pa=${upiId}&pn=${encodeURIComponent(merchantName)}&am=${totalAmount.toFixed(2)}&cu=INR&tn=${encodeURIComponent('Order ' + orderId)}`;

  const newOrder = {
    id: orderId,
    customerName,
    customerPhone,
    customerEmail: customerEmail || 'no-email@bcp.local',
    deliveryAddress,
    items: calculatedItems,
    totalAmount,
    status: 'Pending Payment',
    createdAt: new Date().toISOString(),
    upiPaymentLink: upiString,
    paymentDetails: null
  };

  const orders = readDB(ORDERS_FILE);
  orders.push(newOrder);
  writeDB(ORDERS_FILE, orders);

  res.json({
    success: true,
    orderId: orderId,
    totalAmount: totalAmount,
    upiPaymentLink: upiString,
    upiId: upiId,
    merchantName: merchantName
  });
});

// Verify Payment (Simulated verification callback from UI client)
app.post('/api/orders/:id/verify-payment', async (req, res) => {
  const { id } = req.params;
  const { utr, paymentMethod } = req.body;

  const orders = readDB(ORDERS_FILE);
  const orderIndex = orders.findIndex(o => o.id === id);

  if (orderIndex === -1) {
    return res.status(404).json({ error: 'Order not found.' });
  }

  const order = orders[orderIndex];

  // Update order status to Paid
  order.status = 'Paid';
  order.paymentDetails = {
    method: paymentMethod || 'UPI',
    utr: utr || 'UTR-' + Math.floor(100000000000 + Math.random() * 900000000000),
    paidAt: new Date().toISOString()
  };

  orders[orderIndex] = order;
  writeDB(ORDERS_FILE, orders);

  // Trigger emails asynchronously
  const customerEmailHtml = getCustomerEmailTemplate(order);
  const vendorEmailHtml = getVendorEmailTemplate(order);

  // 1. Send confirmation to customer
  if (order.customerEmail && order.customerEmail !== 'no-email@bcp.local') {
    sendNotificationEmail({
      to: order.customerEmail,
      subject: `Order Confirmed! Your Receipt from Bharat Chicken Point [${order.id}]`,
      htmlBody: customerEmailHtml,
      type: 'Customer Confirmation'
    });
  }

  // 2. Send notification to vendor
  const vendorEmail = process.env.VENDOR_EMAIL || 'sarfarajguddu.bcp@gmail.com';
  sendNotificationEmail({
    to: vendorEmail,
    subject: `⚠️ NEW ORDER ALREADY PAID: ${order.id} | ₹${order.totalAmount}`,
    htmlBody: vendorEmailHtml,
    type: 'Vendor Notification'
  });

  res.json({
    success: true,
    message: 'Payment verified and order confirmed.',
    order: order
  });
});

// ==========================================
// VENDOR / ADMIN API ROUTES
// ==========================================

// Get all orders
app.get('/api/admin/orders', (req, res) => {
  const orders = readDB(ORDERS_FILE);
  // Sort by newest first
  orders.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  res.json(orders);
});

// Update order cooking / delivery status
app.post('/api/admin/orders/:id/status', (req, res) => {
  const { id } = req.params;
  const { status } = req.body;

  const validStatuses = ['Pending Payment', 'Paid', 'Cooking', 'Out for Delivery', 'Delivered', 'Cancelled'];
  if (!validStatuses.includes(status)) {
    return res.status(400).json({ error: 'Invalid order status.' });
  }

  const orders = readDB(ORDERS_FILE);
  const orderIndex = orders.findIndex(o => o.id === id);

  if (orderIndex === -1) {
    return res.status(404).json({ error: 'Order not found.' });
  }

  orders[orderIndex].status = status;
  writeDB(ORDERS_FILE, orders);

  res.json({
    success: true,
    message: `Order status updated to ${status}.`,
    order: orders[orderIndex]
  });
});

// Get email logs (for simulated logging review in Admin UI)
app.get('/api/admin/emails', (req, res) => {
  const logs = readDB(EMAIL_LOGS_FILE);
  res.json(logs);
});

// Configure SMTP directly from Admin Dashboard for quick setup!
app.post('/api/admin/config/smtp', (req, res) => {
  const { host, port, user, pass, isEnabled, vendorEmail } = req.body;

  try {
    const envPath = path.join(__dirname, '.env');
    let envContent = '';
    
    if (fs.existsSync(envPath)) {
      envContent = fs.readFileSync(envPath, 'utf8');
    }

    // Helper to replace or add env variables
    const updateEnvVar = (content, key, value) => {
      const regex = new RegExp(`^${key}=.*$`, 'm');
      if (regex.test(content)) {
        return content.replace(regex, `${key}=${value}`);
      } else {
        return content + `\n${key}=${value}`;
      }
    };

    let newEnvContent = envContent;
    newEnvContent = updateEnvVar(newEnvContent, 'IS_SMTP_ENABLED', isEnabled ? 'true' : 'false');
    if (host) newEnvContent = updateEnvVar(newEnvContent, 'SMTP_HOST', host);
    if (port) newEnvContent = updateEnvVar(newEnvContent, 'SMTP_PORT', port);
    if (user) newEnvContent = updateEnvVar(newEnvContent, 'SMTP_USER', user);
    if (pass) newEnvContent = updateEnvVar(newEnvContent, 'SMTP_PASS', pass);
    if (vendorEmail) newEnvContent = updateEnvVar(newEnvContent, 'VENDOR_EMAIL', vendorEmail);

    fs.writeFileSync(envPath, newEnvContent, 'utf8');

    // Reload process.env dynamically for the running server!
    process.env.IS_SMTP_ENABLED = isEnabled ? 'true' : 'false';
    if (host) process.env.SMTP_HOST = host;
    if (port) process.env.SMTP_PORT = port;
    if (user) process.env.SMTP_USER = user;
    if (pass) process.env.SMTP_PASS = pass;
    if (vendorEmail) process.env.VENDOR_EMAIL = vendorEmail;

    res.json({
      success: true,
      message: 'SMTP settings updated and reloaded successfully.'
    });
  } catch (error) {
    console.error('Error writing SMTP settings to .env:', error);
    res.status(500).json({ error: 'Failed to save SMTP configuration.' });
  }
});

// Start listening
app.listen(PORT, () => {
  console.log(`Bharat Chicken Point server is running on http://localhost:${PORT}`);
});
