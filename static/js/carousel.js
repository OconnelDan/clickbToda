document.addEventListener('DOMContentLoaded', function() {
    // Initialize carousels
    initializeCarousels();
    
    // Date selector handler
    const dateSelector = document.getElementById('dateSelector');
    if (dateSelector) {
        dateSelector.addEventListener('change', function() {
            reloadArticles(this.value);
        });
    }
});

function initializeCarousels() {
    document.querySelectorAll('.carousel-wrapper').forEach(wrapper => {
        // Add touch event listeners for mobile swipe
        let touchStartX = 0;
        let touchEndX = 0;
        
        wrapper.addEventListener('touchstart', e => {
            touchStartX = e.touches[0].clientX;
        });
        
        wrapper.addEventListener('touchmove', e => {
            touchEndX = e.touches[0].clientX;
        });
        
        wrapper.addEventListener('touchend', () => {
            handleSwipe(wrapper, touchStartX, touchEndX);
        });
    });
}

function handleSwipe(wrapper, startX, endX) {
    const SWIPE_THRESHOLD = 50;
    const difference = startX - endX;
    
    if (Math.abs(difference) > SWIPE_THRESHOLD) {
        if (difference > 0) {
            // Swipe left
            wrapper.scrollBy({ left: wrapper.offsetWidth, behavior: 'smooth' });
        } else {
            // Swipe right
            wrapper.scrollBy({ left: -wrapper.offsetWidth, behavior: 'smooth' });
        }
    }
}

function reloadArticles(date) {
    const categorySelector = document.getElementById('categorySelector');
    const selectedCategoryId = categorySelector.value;
    
    let url = '/api/articles';
    if (selectedCategoryId) {
        url += `?category_id=${selectedCategoryId}`;
        if (date) url += `&date=${date}`;
    } else if (date) {
        url += `?date=${date}`;
    }
    
    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch articles');
            return response.json();
        })
        .then(data => {
            if (!data.categories) throw new Error('Invalid response format');
            
            document.querySelectorAll('.category-section').forEach(section => {
                const categoryId = section.dataset.categoryId;
                const categoryData = data.categories.find(c => c.categoria_id.toString() === categoryId);
                
                if (categoryData) {
                    section.style.display = 'block';
                    const eventsContainer = section.querySelector('.events-container');
                    updateEventsDisplay(categoryData, categoryId);
                    initializeCarousels();
                } else {
                    section.style.display = 'none';
                }
            });
        })
        .catch(error => {
            console.error('Error loading articles:', error);
            showError('Failed to load articles. Please try refreshing the page.');
        });
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show';
    errorDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('.container').insertBefore(errorDiv, document.querySelector('.container').firstChild);
}
