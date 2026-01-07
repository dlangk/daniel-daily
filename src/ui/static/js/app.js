document.addEventListener('DOMContentLoaded', function() {
    // Theme handling
    const themeToggle = document.getElementById('theme-toggle');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedTheme = localStorage.getItem('theme');

    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.body.classList.add('dark');
    }

    themeToggle.addEventListener('click', function() {
        document.body.classList.toggle('dark');
        const isDark = document.body.classList.contains('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });

    // Source panel handling
    const panel = document.getElementById('source-panel');
    const overlay = document.getElementById('panel-overlay');
    const closeBtn = document.getElementById('close-panel');
    const sourceTitle = document.getElementById('source-title');
    const sourceName = document.getElementById('source-name');
    const sourceLink = document.getElementById('source-link');
    const sourceContent = document.getElementById('source-content');

    function openPanel() {
        panel.classList.add('open');
        overlay.classList.add('visible');
        document.body.classList.add('panel-open');
    }

    function closePanel() {
        panel.classList.remove('open');
        overlay.classList.remove('visible');
        document.body.classList.remove('panel-open');
    }

    closeBtn.addEventListener('click', closePanel);
    overlay.addEventListener('click', closePanel);

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closePanel();
        }
    });

    // Source reference click handling
    document.addEventListener('click', async function(e) {
        const ref = e.target.closest('.source-ref');
        if (!ref) return;

        const path = ref.dataset.path;
        if (!path) return;

        sourceContent.innerHTML = '<p>Loading...</p>';
        openPanel();

        try {
            const response = await fetch(`/api/source/${encodeURIComponent(path)}`);
            if (!response.ok) {
                throw new Error('Failed to load source');
            }

            const data = await response.json();

            sourceTitle.textContent = data.title;
            sourceName.textContent = data.source_name;
            sourceLink.href = data.url;
            sourceContent.innerHTML = data.content;

        } catch (error) {
            sourceContent.innerHTML = `<p>Error loading source: ${error.message}</p>`;
        }
    });
});
