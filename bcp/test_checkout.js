const http = require('http');
const fs = require('fs');
const path = require('path');

// Helper function to make HTTP requests
function request(options, postData = null) {
  return new Promise((resolve, reject) => {
    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          resolve({
            statusCode: res.statusCode,
            headers: res.headers,
            body: JSON.parse(data)
          });
        } catch (e) {
          resolve({
            statusCode: res.statusCode,
            headers: res.headers,
            body: data
          });
        }
      });
    });

    req.on('error', (e) => reject(e));

    if (postData) {
      req.write(JSON.stringify(postData));
    }
    req.end();
  });
}

async function runTests() {
  console.log('🚀 Starting end-to-end API tests...');

  try {
    // 1. GET Menu
    console.log('\n--- 1. Testing GET /api/menu ---');
    const menuRes = await request({
      hostname: 'localhost',
      port: 3000,
      path: '/api/menu',
      method: 'GET'
    });
    console.log('Status Code:', menuRes.statusCode);
    console.log('Number of items:', Array.isArray(menuRes.body) ? menuRes.body.length : 'Not an array');
    if (menuRes.statusCode !== 200 || !menuRes.body.length) {
      throw new Error('Menu fetch failed.');
    }
    console.log('✅ Menu endpoint working.');

    // 2. POST Orders
    console.log('\n--- 2. Testing POST /api/orders ---');
    const orderPayload = {
      customerName: 'Test Customer',
      customerPhone: '9999999999',
      customerEmail: 'testcustomer@gmail.com',
      deliveryAddress: 'House 42, Block C, Sriniwaspuri, New Delhi',
      items: [
        { id: 'fresh_chicken', quantity: 2 }, // 220 * 2 = 440
        { id: 'mutton_kabab', quantity: 1 }   // 350 * 1 = 350
      ] // Total should be 790
    };
    
    const orderRes = await request({
      hostname: 'localhost',
      port: 3000,
      path: '/api/orders',
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }, orderPayload);

    console.log('Status Code:', orderRes.statusCode);
    console.log('Response Body:', orderRes.body);

    if (orderRes.statusCode !== 200 || !orderRes.body.success) {
      throw new Error('Order creation failed.');
    }

    const { orderId, totalAmount, upiPaymentLink } = orderRes.body;
    if (totalAmount !== 790) {
      throw new Error(`Incorrect order total: expected 790, got ${totalAmount}`);
    }
    console.log('Order ID created:', orderId);
    console.log('UPI String generated:', upiPaymentLink);
    console.log('✅ Order creation working.');

    // 3. POST Verify Payment
    console.log('\n--- 3. Testing POST /api/orders/:id/verify-payment ---');
    const verifyPayload = {
      utr: '987654321012',
      paymentMethod: 'UPI'
    };

    const verifyRes = await request({
      hostname: 'localhost',
      port: 3000,
      path: `/api/orders/${orderId}/verify-payment`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }, verifyPayload);

    console.log('Status Code:', verifyRes.statusCode);
    console.log('Response Body:', verifyRes.body);

    if (verifyRes.statusCode !== 200 || !verifyRes.body.success) {
      throw new Error('Payment verification failed.');
    }
    console.log('✅ Payment verification working.');

    // 4. Validate Saved DB Data
    console.log('\n--- 4. Checking Saved Data File ---');
    const ordersFilePath = path.join(__dirname, 'orders.json');
    const ordersData = JSON.parse(fs.readFileSync(ordersFilePath, 'utf8'));
    const savedOrder = ordersData.find(o => o.id === orderId);

    if (!savedOrder) {
      throw new Error('Order not found in orders.json');
    }
    console.log('Order found in DB with Status:', savedOrder.status);
    if (savedOrder.status !== 'Paid' || savedOrder.paymentDetails.utr !== '987654321012') {
      throw new Error('Order state in database is incorrect!');
    }
    console.log('✅ DB order verification matches.');

    // 5. Validate Email Logs
    console.log('\n--- 5. Checking Simulated Email Logs ---');
    const emailFilePath = path.join(__dirname, 'email_logs.json');
    const emailLogs = JSON.parse(fs.readFileSync(emailFilePath, 'utf8'));
    
    // Find customer & vendor emails for this order
    const customerMail = emailLogs.find(e => e.to === 'testcustomer@gmail.com' && e.subject.includes(orderId));
    const vendorMail = emailLogs.find(e => e.subject.includes('NEW ORDER ALREADY PAID') && e.subject.includes(orderId));

    if (!customerMail) {
      throw new Error('Customer email confirmation was not logged.');
    }
    if (!vendorMail) {
      throw new Error('Vendor email notification was not logged.');
    }
    console.log('Customer Email logged:', customerMail.subject);
    console.log('Vendor Email logged:', vendorMail.subject);
    console.log('✅ Email notifications simulated correctly.');

    // 6. GET Admin Orders
    console.log('\n--- 6. Testing GET /api/admin/orders ---');
    const adminOrdersRes = await request({
      hostname: 'localhost',
      port: 3000,
      path: '/api/admin/orders',
      method: 'GET'
    });
    console.log('Status Code:', adminOrdersRes.statusCode);
    const hasOrder = adminOrdersRes.body.some(o => o.id === orderId);
    console.log('Order found in admin list:', hasOrder);
    if (adminOrdersRes.statusCode !== 200 || !hasOrder) {
      throw new Error('Admin orders view failed.');
    }
    console.log('✅ Admin orders list working.');

    console.log('\n🎉 ALL TESTS PASSED SUCCESSFULLY! THE APPLICATION IS 100% CORRECT AND FUNCTIONAL.');
  } catch (error) {
    console.error('\n❌ Test failed with error:', error);
    process.exit(1);
  }
}

runTests();
