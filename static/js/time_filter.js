document.addEventListener('DOMContentLoaded', function() {
    const timeFilter = document.querySelector('.toggle-slider');
    if (!timeFilter) return;

    timeFilter.addEventListener('change', function(e) {
        if (!e.target.matches('input[type="radio"]')) return;
        
        const hours = parseInt(e.target.value);
        const currentDate = new Date();
        let filterDate = new Date(currentDate - hours * 60 * 60 * 1000); // Convert hours to milliseconds
        
        // Format date as YYYY-MM-DD HH:mm:ss
        const formattedDate = filterDate.toISOString();
        
        // Reload articles with new date filter
        reloadArticles(formattedDate);
    });

    // Trigger initial load with 24h filter
    const defaultFilter = document.querySelector('input[value="24"]');
    if (defaultFilter) {
        defaultFilter.dispatchEvent(new Event('change'));
    }
});
