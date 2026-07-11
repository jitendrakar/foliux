/**
 * SalonX - Premium Unisex Salon
 * Custom JavaScript File
 */

$(document).ready(function() {
    "use strict";

    // ----------------------------------------------------
    // 1. Gallery Filtering & Animations
    // ----------------------------------------------------
    $('.gallery-filters').on('click', '.btn-filter', function() {
        var filterValue = $(this).attr('data-filter');
        
        // Update active class on buttons
        $('.gallery-filters .btn-filter').removeClass('active');
        $(this).addClass('active');

        if (filterValue === 'all') {
            $('.gallery-item-col').fadeIn(350);
        } else {
            $('.gallery-item-col').hide();
            $('.gallery-item-col[data-category="' + filterValue + '"]').fadeIn(350);
        }
    });

    // ----------------------------------------------------
    // 2. Gallery Popup Viewer
    // ----------------------------------------------------
    $('.gallery-item-wrapper').on('click', function() {
        var imgSrc = $(this).find('img').attr('src');
        var imgTitle = $(this).find('.gallery-overlay h5').text();

        $('body').append(
            '<div class="popup-viewer-overlay" style="display: flex;">' +
                '<div class="popup-viewer-content">' +
                    '<span class="popup-viewer-close">&times;</span>' +
                    '<img src="' + imgSrc + '" alt="' + imgTitle + '">' +
                    '<h4 class="text-center text-white mt-3 font-luxury">' + imgTitle + '</h4>' +
                '</div>' +
            '</div>'
        );

        // Lock background scroll
        $('body').css('overflow', 'hidden');
    });

    // Close Popup Viewer
    $(document).on('click', '.popup-viewer-close, .popup-viewer-overlay', function(e) {
        if (e.target !== this && !$(e.target).hasClass('popup-viewer-close')) {
            return;
        }
        $('.popup-viewer-overlay').fadeOut(200, function() {
            $(this).remove();
            $('body').css('overflow', 'auto');
        });
    });

    // ----------------------------------------------------
    // 3. AJAX Booking Submission
    // ----------------------------------------------------
    $('#ajax-booking-form').on('submit', function(e) {
        e.preventDefault();
        
        var form = $(this);
        var submitBtn = form.find('button[type="submit"]');
        var formResult = $('#booking-form-result');
        
        submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...');

        $.ajax({
            url: form.attr('action') || window.location.href,
            type: 'POST',
            data: form.serialize(),
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(response) {
                submitBtn.prop('disabled', false).html('Book Appointment');
                
                if (response.status === 'success') {
                    formResult.html(
                        '<div class="alert alert-success alert-dismissible fade show" role="alert">' +
                            '<strong>Success!</strong> ' + response.message +
                            '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
                        '</div>'
                    );
                    form[0].reset();
                } else if (response.status === 'error') {
                    var errHTML = '<div class="alert alert-danger alert-dismissible fade show" role="alert"><strong>Error!</strong> Please fix the errors below:<ul>';
                    $.each(response.errors, function(key, val) {
                        errHTML += '<li>' + key + ': ' + val.join(', ') + '</li>';
                    });
                    errHTML += '</ul><button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>';
                    formResult.html(errHTML);
                }
            },
            error: function() {
                submitBtn.prop('disabled', false).html('Book Appointment');
                formResult.html(
                    '<div class="alert alert-danger alert-dismissible fade show" role="alert">' +
                        '<strong>Error!</strong> Something went wrong. Please check your inputs and try again.' +
                        '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
                    '</div>'
                );
            }
        });
    });

    // ----------------------------------------------------
    // 4. AJAX Contact Form Submission
    // ----------------------------------------------------
    $('#ajax-contact-form').on('submit', function(e) {
        e.preventDefault();
        
        var form = $(this);
        var submitBtn = form.find('button[type="submit"]');
        var formResult = $('#contact-form-result');
        
        submitBtn.prop('disabled', true).html('Sending...');

        $.ajax({
            url: form.attr('action') || window.location.href,
            type: 'POST',
            data: form.serialize(),
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(response) {
                submitBtn.prop('disabled', false).html('Send Message');
                if (response.status === 'success') {
                    formResult.html(
                        '<div class="alert alert-success" role="alert">' +
                            response.message +
                        '</div>'
                    );
                    form[0].reset();
                }
            },
            error: function() {
                submitBtn.prop('disabled', false).html('Send Message');
                formResult.html(
                    '<div class="alert alert-danger" role="alert">' +
                        'Oops, something went wrong. Please try again later.' +
                    '</div>'
                );
            }
        });
    });

    // ----------------------------------------------------
    // 5. Native Image Lazy Loading Fallback
    // ----------------------------------------------------
    if ('IntersectionObserver' in window) {
        var lazyImageObserver = new IntersectionObserver(function(entries, observer) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    var lazyImage = entry.target;
                    if (lazyImage.dataset.src) {
                        lazyImage.src = lazyImage.dataset.src;
                    }
                    lazyImageObserver.unobserve(lazyImage);
                }
            });
        });

        $('img.lazy-load').each(function() {
            lazyImageObserver.observe(this);
        });
    } else {
        // Fallback for older browsers
        $('img.lazy-load').each(function() {
            if (this.dataset.src) {
                this.src = this.dataset.src;
            }
        });
    }

    // ----------------------------------------------------
    // 6. Smooth Scrolling for Anchor Links
    // ----------------------------------------------------
    $('a.smooth-scroll[href^="#"]').on('click', function(event) {
        var target = $(this.getAttribute('href'));
        if (target.length) {
            event.preventDefault();
            $('html, body').stop().animate({
                scrollTop: target.offset().top - 80
            }, 800);
        }
    });
});
