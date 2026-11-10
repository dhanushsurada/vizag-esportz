/**
 * Vizag Esportz - Tournament Payment Scripts
 */

function showUPI() {
    var upiPanel = document.getElementById('upi-panel');
    var rzpPanel = document.getElementById('razorpay-panel');
    if (upiPanel) upiPanel.style.display = 'block';
    if (rzpPanel) rzpPanel.style.display = 'none';
}

function showRazorpay() {
    var upiPanel = document.getElementById('upi-panel');
    var rzpPanel = document.getElementById('razorpay-panel');
    if (upiPanel) upiPanel.style.display = 'none';
    if (rzpPanel) rzpPanel.style.display = 'block';
}

function previewScreenshot(input) {
    var previewWrapper = document.getElementById('screenshot-preview-wrapper');
    var previewImg = document.getElementById('screenshot-preview-img');
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
            previewImg.src = e.target.result;
            previewWrapper.style.display = 'block';
        };
        reader.readAsDataURL(input.files[0]);
    } else {
        if (previewWrapper) previewWrapper.style.display = 'none';
        if (previewImg) previewImg.src = '';
    }
}

function openRazorpay() {
    var panel = document.getElementById('razorpay-panel');
    var key = panel ? panel.getAttribute('data-key') : '';
    if (!key || typeof Razorpay === 'undefined') {
        alert('Online payment gateway is currently not available. Please use the UPI option above.');
        return;
    }
    var options = {
        "key": key,
        "amount": panel.getAttribute('data-amount') || '0',
        "currency": panel.getAttribute('data-currency') || 'INR',
        "name": "Vizag Esportz",
        "description": "Tournament: " + (panel.getAttribute('data-title') || ''),
        "order_id": panel.getAttribute('data-order-id') || '',
        "prefill": {
            "name": panel.getAttribute('data-user-name') || '',
            "email": panel.getAttribute('data-user-email') || '',
            "contact": panel.getAttribute('data-user-phone') || ''
        },
        "theme": { "color": "#C41212" },
        "handler": function(response) {
            document.getElementById('razorpay_order_id').value = response.razorpay_order_id;
            document.getElementById('razorpay_payment_id').value = response.razorpay_payment_id;
            document.getElementById('razorpay_signature').value = response.razorpay_signature;
            document.getElementById('payment-form').submit();
        },
        "modal": { "ondismiss": function() { console.log("Payment cancelled."); } }
    };
    var rzp = new Razorpay(options);
    rzp.open();
}
