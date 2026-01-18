// App Utilities
function confirmAction(message) {
    return confirm(message || "Are you sure?");
}

// Fade out alerts
setTimeout(function () {
    let alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (alert) {
        try {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        } catch (e) { }
    });
}, 3000);
