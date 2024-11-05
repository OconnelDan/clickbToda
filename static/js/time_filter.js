document.addEventListener('DOMContentLoaded', function() {
    const timeFilter = document.querySelector('.toggle-slider');
    if (!timeFilter) return;

    timeFilter.addEventListener('change', function(e) {
        if (!e.target.matches('input[type="radio"]')) return;
        
        const timeRange = e.target.value;
        const currentDate = new Date();
        let filterDate = new Date();
        
        switch(timeRange) {
            case 'today':
                filterDate = currentDate;
                break;
            case 'week':
                filterDate.setDate(currentDate.getDate() - 7);
                break;
            case 'month':
                filterDate.setMonth(currentDate.getMonth() - 1);
                break;
        }
        
        // Format date as YYYY-MM-DD
        const formattedDate = filterDate.toISOString().split('T')[0];
        
        // Reload articles with new date filter
        reloadArticles(formattedDate);
    });
});
