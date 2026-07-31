/**
 * ThinkMech Solutions - Main Interactive Script
 */

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initCounters();
  initIAQGauge();
  initModals();
  initForms();
});

/* Navigation & Mobile Drawer */
function initNavigation() {
  const mobileToggle = document.querySelector('.mobile-toggle');
  const navMenu = document.querySelector('.nav-menu');

  if (mobileToggle && navMenu) {
    mobileToggle.addEventListener('click', () => {
      navMenu.classList.toggle('active');
      const icon = mobileToggle.querySelector('i');
      if (icon) {
        icon.classList.toggle('fa-bars');
        icon.classList.toggle('fa-xmark');
      }
    });
  }

  // Active Link Highlighting based on current pathname
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.nav-link');

  navLinks.forEach(link => {
    const linkPath = link.getAttribute('href');
    if (currentPath.endsWith(linkPath) || (linkPath === 'index.html' && (currentPath.endsWith('/tm/') || currentPath.endsWith('/tm')))) {
      link.classList.add('active');
    }
  });

  // Sticky Header Shadow on Scroll
  const header = document.querySelector('.header');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 30) {
      header.style.boxShadow = '0 10px 25px -5px rgba(15, 43, 72, 0.12)';
    } else {
      header.style.boxShadow = 'none';
    }
  });
}

/* Animated Counters on Scroll */
function initCounters() {
  const statNumbers = document.querySelectorAll('.stat-number');
  if (statNumbers.length === 0) return;

  let animated = false;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !animated) {
        animated = true;
        statNumbers.forEach(stat => {
          const target = stat.getAttribute('data-target');
          if (!target) return;

          const isPlus = target.includes('+');
          const numValue = parseInt(target.replace(/[^0-9]/g, ''));
          let current = 0;
          const duration = 1800; // ms
          const stepTime = 30;
          const increment = Math.ceil(numValue / (duration / stepTime));

          const timer = setInterval(() => {
            current += increment;
            if (current >= numValue) {
              current = numValue;
              clearInterval(timer);
            }
            if (target.includes('Lakh')) {
              stat.textContent = `${current} Lakh KW`;
            } else {
              stat.textContent = `${current}${isPlus ? '+' : ''}`;
            }
          }, stepTime);
        });
      }
    });
  }, { threshold: 0.3 });

  const statsSection = document.querySelector('.stats-grid');
  if (statsSection) {
    observer.observe(statsSection);
  }
}

/* Interactive Indoor Air Quality Meter Gauge */
function initIAQGauge() {
  const needle = document.getElementById('iaqNeedle');
  const statusBadge = document.getElementById('iaqStatusBadge');
  const levelTitle = document.getElementById('iaqLevelTitle');
  const levelDesc = document.getElementById('iaqLevelDesc');
  const buttons = document.querySelectorAll('.iaq-btn');

  if (!needle || !statusBadge) return;

  const iaqStates = {
    safe: {
      rotation: -60, // degrees
      badgeText: 'SAFE (AQI 0 - 50)',
      badgeClass: 'status-safe',
      title: 'Optimal & Clean Indoor Air Quality',
      desc: 'CO₂ levels < 600 ppm, zero pathogens, HEPA filtration active. Maximum workplace productivity & hygiene.'
    },
    risky: {
      rotation: 0,
      badgeText: 'RISKY (AQI 101 - 200)',
      badgeClass: 'status-risky',
      title: 'Moderate Contamination Detected',
      desc: 'Elevated CO₂ & humidity. Pathogen transmission risk increased. UVGI & EC Fan ventilation recommended.'
    },
    danger: {
      rotation: 60,
      badgeText: 'DANGER (AQI 250+)',
      badgeClass: 'status-danger',
      title: 'Hazardous Air Quality Warning',
      desc: 'High volatile organic compounds (VOCs), pathogens, particulates. Urgent HEPA + Gas Phase Filtration required.'
    }
  };

  function updateIAQ(stateKey) {
    const data = iaqStates[stateKey];
    if (!data) return;

    needle.style.transform = `translateX(-50%) rotate(${data.rotation}deg)`;
    statusBadge.textContent = data.badgeText;
    statusBadge.className = `iaq-status-badge ${data.badgeClass}`;
    if (levelTitle) levelTitle.textContent = data.title;
    if (levelDesc) levelDesc.textContent = data.desc;

    buttons.forEach(btn => {
      if (btn.getAttribute('data-state') === stateKey) {
        btn.classList.add('btn-primary');
        btn.classList.remove('btn-outline');
      } else {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-outline');
      }
    });
  }

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      const state = btn.getAttribute('data-state');
      updateIAQ(state);
    });
  });

  // Default to Safe state
  updateIAQ('safe');
}

/* Modals Trigger */
function initModals() {
  const modal = document.getElementById('quoteModal');
  const triggers = document.querySelectorAll('.open-quote-modal');
  const closeBtn = document.querySelector('.close-modal');

  if (!modal) return;

  triggers.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      modal.classList.add('active');
    });
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      modal.classList.remove('active');
    });
  }

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.classList.remove('active');
    }
  });
}

/* Forms Handling */
function initForms() {
  const forms = document.querySelectorAll('form');

  forms.forEach(form => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();

      const formData = new FormData(form);
      const data = Object.fromEntries(formData.entries());

      // Save to localStorage for demo persistence
      const submissions = JSON.parse(localStorage.getItem('thinkmech_leads') || '[]');
      submissions.push({ ...data, date: new Date().toISOString() });
      localStorage.setItem('thinkmech_leads', JSON.stringify(submissions));

      // Feedback alert
      alert('Thank you! Your inquiry has been received. A ThinkMech HVAC engineer will contact you shortly.');
      form.reset();

      const modal = document.getElementById('quoteModal');
      if (modal) modal.classList.remove('active');
    });
  });
}
