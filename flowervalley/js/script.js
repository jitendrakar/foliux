/* ==========================================================================
   FLOWER VALLEY OCCUPATIONAL THERAPY CENTRE - INTERACTIVE SCRIPT
   - Responsive Navigation & Smooth Scrolling
   - Teacher's Checklist State, Count & WhatsApp Pre-fill
   - Print Checklist Handler
   - Appointment Form Validation & Modal Trigger
   - Simple Admin Content Management System (CMS) via LocalStorage
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initCMS();
  initNavigation();
  initChecklist();
  initAppointmentForm();
  initModals();
});

/* --------------------------------------------------------------------------
   1. NAVIGATION & HAMBURGER MENU
   -------------------------------------------------------------------------- */
function initNavigation() {
  const hamburger = document.getElementById('hamburgerBtn');
  const navMenu = document.getElementById('navMenu');
  const navLinks = document.querySelectorAll('.nav-link');

  if (hamburger && navMenu) {
    hamburger.addEventListener('click', () => {
      navMenu.classList.toggle('active');
      const icon = hamburger.querySelector('i');
      if (icon) {
        icon.className = navMenu.classList.contains('active') ? 'fas fa-times' : 'fas fa-bars';
      }
    });

    navLinks.forEach(link => {
      link.addEventListener('click', () => {
        navMenu.classList.remove('active');
        const icon = hamburger.querySelector('i');
        if (icon) icon.className = 'fas fa-bars';
      });
    });
  }
}

/* --------------------------------------------------------------------------
   2. TEACHER'S CHECKLIST INTERACTIVITY & PRINT
   -------------------------------------------------------------------------- */
function initChecklist() {
  const checkboxes = document.querySelectorAll('.checklist-item input[type="checkbox"]');
  const counterBadge = document.getElementById('selectedCountBadge');
  const discussBtn = document.getElementById('discussTherapistBtn');
  const printBtn = document.getElementById('printChecklistBtn');
  const clearBtn = document.getElementById('clearChecklistBtn');

  function updateChecklistState() {
    let checkedCount = 0;
    const selectedItems = [];

    checkboxes.forEach(cb => {
      const parentLabel = cb.closest('.checklist-item');
      if (cb.checked) {
        checkedCount++;
        if (parentLabel) parentLabel.classList.add('checked');
        const itemText = cb.getAttribute('data-title') || parentLabel.textContent.trim();
        const category = cb.getAttribute('data-category') || 'Classroom Observation';
        selectedItems.push(`${category}: ${itemText}`);
      } else {
        if (parentLabel) parentLabel.classList.remove('checked');
      }
    });

    if (counterBadge) {
      counterBadge.textContent = `${checkedCount} Red Flags Selected`;
      counterBadge.style.background = checkedCount > 0 ? '#c0392b' : '#5d6d7e';
    }

    return selectedItems;
  }

  checkboxes.forEach(cb => {
    cb.addEventListener('change', updateChecklistState);
  });

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      checkboxes.forEach(cb => { cb.checked = false; });
      updateChecklistState();
    });
  }

  if (printBtn) {
    printBtn.addEventListener('click', () => {
      window.print();
    });
  }

  if (discussBtn) {
    discussBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const selected = updateChecklistState();
      
      const phone = getCMSValue('phone', '9716004677');
      let msg = `Hello Dr. Zeena Jahan,\n\nI am contacting you regarding Flower Valley Occupational Therapy Centre.`;
      
      if (selected.length > 0) {
        msg += `\n\nI have completed the Teacher's Checklist and observed the following ${selected.length} red flag(s):\n- ` + selected.join('\n- ');
        msg += `\n\nI would like to discuss early intervention and support options for my student/child.`;
      } else {
        msg += `\n\nI would like to discuss a consultation for my child.`;
      }

      // Also pre-populate appointment main concern field
      const concernInput = document.getElementById('mainConcern');
      if (concernInput && selected.length > 0) {
        concernInput.value = `Observed Red Flags (${selected.length}):\n` + selected.join('\n');
      }

      // Scroll smoothly to appointment or open WhatsApp
      const waUrl = `https://wa.me/91${phone}?text=${encodeURIComponent(msg)}`;
      window.open(waUrl, '_blank');
    });
  }
}

/* --------------------------------------------------------------------------
   3. APPOINTMENT FORM & SUCCESS MODAL
   -------------------------------------------------------------------------- */
function initAppointmentForm() {
  const form = document.getElementById('appointmentForm');
  const modal = document.getElementById('successModal');
  const modalWaBtn = document.getElementById('modalWaBtn');

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();

      const parentName = document.getElementById('parentName').value.trim();
      const childName = document.getElementById('childName').value.trim();
      const childAge = document.getElementById('childAge').value.trim();
      const phone = document.getElementById('phoneNum').value.trim();
      const email = document.getElementById('emailAddr').value.trim();
      const prefDate = document.getElementById('prefDate').value;
      const prefTime = document.getElementById('prefTime').value;
      const mainConcern = document.getElementById('mainConcern').value.trim();
      const message = document.getElementById('messageText').value.trim();

      if (!parentName || !childName || !phone) {
        alert('Please fill in all required fields (Parent Name, Child Name, and Phone Number).');
        return;
      }

      const appointmentData = {
        id: 'APT-' + Date.now(),
        parentName,
        childName,
        childAge,
        phone,
        email,
        prefDate,
        prefTime,
        mainConcern,
        message,
        timestamp: new Date().toISOString()
      };

      // Store in localStorage
      const existing = JSON.parse(localStorage.getItem('flower_valley_appointments') || '[]');
      existing.push(appointmentData);
      localStorage.setItem('flower_valley_appointments', JSON.stringify(existing));

      // Build WhatsApp payload for instant notification
      const cmsPhone = getCMSValue('phone', '9716004677');
      let waText = `*New Appointment Request - Flower Valley OT Centre*\n`;
      waText += `\n*Parent/Guardian:* ${parentName}`;
      waText += `\n*Child Name:* ${childName} (${childAge || 'N/A'} yrs)`;
      waText += `\n*Phone:* ${phone}`;
      if (email) waText += `\n*Email:* ${email}`;
      if (prefDate) waText += `\n*Preferred Date:* ${prefDate} (${prefTime || 'Any time'})`;
      if (mainConcern) waText += `\n*Main Concern:* ${mainConcern}`;
      if (message) waText += `\n*Notes:* ${message}`;

      if (modalWaBtn) {
        modalWaBtn.href = `https://wa.me/91${cmsPhone}?text=${encodeURIComponent(waText)}`;
      }

      // Reset form & show modal
      form.reset();
      if (modal) modal.classList.add('active');
    });
  }
}

/* --------------------------------------------------------------------------
   4. MODALS & ADMIN CMS
   -------------------------------------------------------------------------- */
function initModals() {
  const modals = document.querySelectorAll('.modal-backdrop');
  modals.forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal || e.target.classList.contains('modal-close-btn') || e.target.closest('.modal-close-btn')) {
        modal.classList.remove('active');
      }
    });
  });

  const adminTrigger = document.getElementById('adminCmsTrigger');
  const adminModal = document.getElementById('adminModal');
  const adminForm = document.getElementById('adminCmsForm');

  if (adminTrigger && adminModal) {
    adminTrigger.addEventListener('click', (e) => {
      e.preventDefault();
      loadAdminFormValues();
      adminModal.classList.add('active');
    });
  }

  if (adminForm) {
    adminForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const updated = {
        phone: document.getElementById('cmsPhone').value.trim(),
        email: document.getElementById('cmsEmail').value.trim(),
        address: document.getElementById('cmsAddress').value.trim(),
        tagline: document.getElementById('cmsTagline').value.trim(),
      };

      localStorage.setItem('flower_valley_cms_content', JSON.stringify(updated));
      applyCMSContent();
      if (adminModal) adminModal.classList.remove('active');
      alert('Website content updated successfully!');
    });
  }
}

function getCMSValue(key, defaultVal) {
  try {
    const saved = JSON.parse(localStorage.getItem('flower_valley_cms_content') || '{}');
    return saved[key] || defaultVal;
  } catch (e) {
    return defaultVal;
  }
}

function loadAdminFormValues() {
  document.getElementById('cmsPhone').value = getCMSValue('phone', '9716004677');
  document.getElementById('cmsEmail').value = getCMSValue('email', 'flowervalleytherapycentre@gmail.com');
  document.getElementById('cmsAddress').value = getCMSValue('address', 'B-433, DDA Janta Flats, Pocket-11, Ground Floor, Jasola, New Delhi – 110025');
  document.getElementById('cmsTagline').value = getCMSValue('tagline', 'Helping Every Child Bloom');
}

function initCMS() {
  applyCMSContent();
}

function applyCMSContent() {
  const phone = getCMSValue('phone', '9716004677');
  const email = getCMSValue('email', 'flowervalleytherapycentre@gmail.com');
  const address = getCMSValue('address', 'B-433, DDA Janta Flats, Pocket-11, Ground Floor, Jasola, New Delhi – 110025');
  const tagline = getCMSValue('tagline', 'Helping Every Child Bloom');

  // Update phone elements
  document.querySelectorAll('.cms-phone-text').forEach(el => el.textContent = phone);
  document.querySelectorAll('.cms-phone-link').forEach(el => el.href = `tel:${phone}`);
  document.querySelectorAll('.cms-wa-link').forEach(el => {
    el.href = `https://wa.me/91${phone}?text=${encodeURIComponent('Hello Flower Valley Occupational Therapy Centre, I would like to inquire about therapy services.')}`;
  });

  // Update email elements
  document.querySelectorAll('.cms-email-text').forEach(el => el.textContent = email);
  document.querySelectorAll('.cms-email-link').forEach(el => el.href = `mailto:${email}`);

  // Update address & tagline
  document.querySelectorAll('.cms-address-text').forEach(el => el.textContent = address);
  document.querySelectorAll('.cms-tagline-text').forEach(el => el.textContent = tagline);
}
