/**
 * ThinkMech Solutions - Dynamic Schema.org SEO Structured Data
 */

(function injectSchema() {
  const orgSchema = {
    "@context": "https://schema.org",
    "@type": "HVACBusiness",
    "name": "ThinkMech Solutions",
    "alternateName": "ThinkMech HVAC Engineering",
    "url": "https://foliux.com/tm/",
    "logo": "https://foliux.com/tm/tmlogo.png",
    "image": "https://foliux.com/tm/tmlogo.png",
    "description": "Single Point of Contact (SPOC) for complete HVAC engineering solutions, retrofitting, energy optimization, indoor air quality, cleanroom validation, and 24x7 maintenance.",
    "telephone": "+91-98765-43210",
    "email": "info@thinkmech.com",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "ThinkMech Tech Park, Industrial Sector",
      "addressLocality": "Bengaluru",
      "addressRegion": "Karnataka",
      "postalCode": "560001",
      "addressCountry": "IN"
    },
    "openingHoursSpecification": [
      {
        "@type": "OpeningHoursSpecification",
        "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "opens": "08:00",
        "closes": "20:00"
      }
    ],
    "sameAs": [
      "https://facebook.com/thinkmech",
      "https://linkedin.com/company/thinkmech-solutions",
      "https://twitter.com/thinkmech"
    ],
    "priceRange": "$$"
  };

  const serviceSchema = {
    "@context": "https://schema.org",
    "@type": "Service",
    "serviceType": "HVAC Engineering & Maintenance",
    "provider": {
      "@type": "LocalBusiness",
      "name": "ThinkMech Solutions"
    },
    "areaServed": {
      "@type": "Country",
      "name": "India"
    },
    "hasOfferCatalog": {
      "@type": "OfferCatalog",
      "name": "HVAC Engineering Services",
      "itemListElement": [
        {
          "@type": "Offer",
          "itemOffered": {
            "@type": "Service",
            "name": "HVAC Retrofitting & Chiller Replacement"
          }
        },
        {
          "@type": "Offer",
          "itemOffered": {
            "@type": "Service",
            "name": "AHU & Ducting Solutions"
          }
        },
        {
          "@type": "Offer",
          "itemOffered": {
            "@type": "Service",
            "name": "Energy Audit & Qualification (DQ, IQ, OQ, PQ)"
          }
        },
        {
          "@type": "Offer",
          "itemOffered": {
            "@type": "Service",
            "name": "Indoor Air Quality & Clean Room Audit"
          }
        },
        {
          "@type": "Offer",
          "itemOffered": {
            "@type": "Service",
            "name": "24x7 AMC Maintenance & Blueace Digital Monitoring"
          }
        }
      ]
    }
  };

  function appendJsonLd(schemaObj) {
    const script = document.createElement('script');
    script.type = 'application/ld+json';
    script.text = JSON.stringify(schemaObj);
    document.head.appendChild(script);
  }

  appendJsonLd(orgSchema);
  appendJsonLd(serviceSchema);
})();
