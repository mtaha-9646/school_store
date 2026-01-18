// Requires html5-qrcode library loaded from CDN
// Handles both embedded camera scanning AND socket pairing

function initScanner(socket, pairingCode) {
    if (!socket) return;

    console.log("Initializing remote scanner with code:", pairingCode);

    // Join Room
    socket.emit('join_pairing', pairingCode);

    socket.on('connect', () => {
        document.getElementById('connection-status').innerText = "Connected to Server";
        document.getElementById('connection-status').className = "badge bg-success";
    });

    socket.on('disconnect', () => {
        document.getElementById('connection-status').innerText = "Disconnected";
        document.getElementById('connection-status').className = "badge bg-danger";
    });

    // START CAMERA
    const html5QrCode = new Html5Qrcode("reader");
    const config = { fps: 10, qrbox: { width: 250, height: 150 }, aspectRatio: 1.0 };

    html5QrCode.start(
        { facingMode: "environment" },
        config,
        (decodedText, decodedResult) => {
            // Success
            console.log(`Scan result: ${decodedText}`);

            // Haptic Feedback
            if (navigator.vibrate) navigator.vibrate(200);

            // Send to server
            socket.emit('barcode_scanned', { code: pairingCode, barcode: decodedText });

            // Flash UI
            const status = document.getElementById('last-scan');
            if (status) {
                status.innerText = "Sent: " + decodedText;
                status.classList.add('text-success');
                setTimeout(() => status.classList.remove('text-success'), 500);
            }

            // Optional: Pause briefly to avoid double scan? 
            // html5QrCode.pause(); setTimeout(() => html5QrCode.resume(), 1000);
            // But we often want rapid scanning.
        },
        (errorMessage) => {
            // Parse error, ignore
        }
    ).catch(err => {
        console.error("Error starting scanner", err);
        document.getElementById('reader').innerText = "Camera access denied or error.";
    });
}
