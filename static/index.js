// Form submission and loading spinner
document.getElementById('scrape-form').addEventListener('submit', function (e) {
    const urlInput = document.getElementById('url');
    const urlPattern = /^https?:\/\/.+\..+/;

    if (!urlPattern.test(urlInput.value)) {
        e.preventDefault();
        urlInput.classList.add('is-invalid');
        document.querySelector('.url-validator-feedback').style.display = 'block';
        return false;
    }

    document.getElementById('submit-btn').disabled = true;
    document.getElementById('spinner').style.display = 'block';

    // Simulate status updates
    const statusUpdates = document.getElementById('status-updates');
    const updates = [
        "Connecting to target website...",
        "Analyzing site structure...",
        "Prioritizing high-value pages...",
        "Searching for contact information...",
        "Processing found data...",
        "Organizing results..."
    ];

    let i = 0;
    const updateInterval = setInterval(function () {
        if (i < updates.length) {
            statusUpdates.innerHTML += `<p class="mb-1"><small>${updates[i]}</small></p>`;
            statusUpdates.scrollTop = statusUpdates.scrollHeight;
            i++;
        } else {
            clearInterval(updateInterval);
        }
    }, 3000);
});

// URL validation on input
document.getElementById('url').addEventListener('input', function () {
    const urlInput = this;
    const urlPattern = /^https?:\/\/.+\..+/;

    if (urlPattern.test(urlInput.value)) {
        urlInput.classList.remove('is-invalid');
        document.querySelector('.url-validator-feedback').style.display = 'none';
    }
});

// Dark mode toggle
document.getElementById('theme-toggle').addEventListener('click', function () {
    const html = document.documentElement;
    const themeIcon = this.querySelector('i');

    if (html.getAttribute('data-bs-theme') === 'dark') {
        html.setAttribute('data-bs-theme', 'light');
        themeIcon.classList.remove('bi-sun-fill');
        themeIcon.classList.add('bi-moon-fill');
    } else {
        html.setAttribute('data-bs-theme', 'dark');
        themeIcon.classList.remove('bi-moon-fill');
        themeIcon.classList.add('bi-sun-fill');
    }
});
