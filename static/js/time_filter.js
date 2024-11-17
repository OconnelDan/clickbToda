document.addEventListener('DOMContentLoaded', function() {
    const timeFilterGroup = document.querySelector('.time-filter-group');
    if (!timeFilterGroup) return;

    // Set default time filter from URL or fallback to 72h
    const urlParams = new URLSearchParams(window.location.search);
    const timeFilter = urlParams.get('time_filter') || '72h';
    const defaultFilter = timeFilterGroup.querySelector(`input[value="${timeFilter}"]`);
    if (defaultFilter) {
        defaultFilter.checked = true;
    }

    timeFilterGroup.addEventListener('change', function(e) {
        if (!e.target.matches('input[type="radio"]')) return;
        
        const timeFilter = e.target.value;
        
        // Reload the entire page to update all counts
        window.location.href = '/?time_filter=' + timeFilter;
    });
});