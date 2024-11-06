document.addEventListener('DOMContentLoaded', function() {
    const timeFilter = document.querySelector('.toggle-slider');
    const eventsContent = document.getElementById('events-content');
    if (!timeFilter) return;

    timeFilter.addEventListener('change', function(e) {
        if (!e.target.matches('input[type="radio"]')) return;
        
        // Show loading state
        if (eventsContent) {
            eventsContent.innerHTML = `
                <div class="text-center my-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2">Loading articles...</p>
                </div>
            `;
        }
        
        const timeRange = e.target.value;
        const currentDate = new Date();
        let filterDate = new Date();
        
        switch(timeRange) {
            case '24h':
                filterDate.setHours(currentDate.getHours() - 24);
                break;
            case '48h':
                filterDate.setHours(currentDate.getHours() - 48);
                break;
            case '72h':
                filterDate.setHours(currentDate.getHours() - 72);
                break;
        }
        
        // Format date as YYYY-MM-DD HH:mm:ss
        const formattedDate = filterDate.toISOString().slice(0, 19).replace('T', ' ');
        
        // Reload articles with new date filter
        reloadArticles(formattedDate);
    });
});
