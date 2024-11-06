document.addEventListener('DOMContentLoaded', function() {
    const timeFilter = document.querySelector('.toggle-slider-small');
    if (!timeFilter) return;

    timeFilter.addEventListener('change', function(e) {
        if (!e.target.matches('input[type="radio"]')) return;
        
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
        
        // Format date as YYYY-MM-DD
        const formattedDate = filterDate.toISOString().split('T')[0];
        
        // Reload articles with new date filter
        reloadArticles(formattedDate);
    });
});
