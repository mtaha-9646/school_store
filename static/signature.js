document.addEventListener("DOMContentLoaded", function () {
    const canvas = document.getElementById('signature-pad');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const input = document.getElementById('signature-data');
    let writing = false;

    // Resize
    function resize() {
        const rect = canvas.parentElement.getBoundingClientRect();
        canvas.width = rect.width;
        canvas.height = 150;
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.strokeStyle = '#000';
    }
    window.addEventListener('resize', resize);
    resize();

    function getPos(e) {
        const rect = canvas.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        return {
            x: clientX - rect.left,
            y: clientY - rect.top
        };
    }

    function start(e) {
        writing = true;
        ctx.beginPath();
        const pos = getPos(e);
        ctx.moveTo(pos.x, pos.y);
        e.preventDefault();
    }

    function move(e) {
        if (!writing) return;
        const pos = getPos(e);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
        e.preventDefault();
    }

    function end(e) {
        writing = false;
        if (input) input.value = canvas.toDataURL();
    }

    canvas.addEventListener('mousedown', start);
    canvas.addEventListener('mousemove', move);
    canvas.addEventListener('mouseup', end);

    canvas.addEventListener('touchstart', start, { passive: false });
    canvas.addEventListener('touchmove', move, { passive: false });
    canvas.addEventListener('touchend', end);

    document.getElementById('clear-sig').addEventListener('click', function () {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (input) input.value = '';
    });
});
