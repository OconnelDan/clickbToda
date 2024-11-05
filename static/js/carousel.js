document.addEventListener('DOMContentLoaded', function() {
    // Initialize carousels and scroll buttons
    initializeCarousels();
    initializeScrollButtons();
    
    // Date selector handler
    const dateSelector = document.getElementById('dateSelector');
    if (dateSelector) {
        dateSelector.addEventListener('change', function() {
            reloadArticles(this.value);
        });
    }
});

function initializeScrollButtons() {
    document.querySelectorAll('.articles-carousel, .nav-tabs-wrapper').forEach(container => {
        const wrapper = container.querySelector('.carousel-wrapper, .nav-tabs');
        const leftBtn = container.querySelector('.scroll-button.left');
        const rightBtn = container.querySelector('.scroll-button.right');
        
        if (!wrapper || !leftBtn || !rightBtn) return;

        const updateButtons = () => {
            const hasOverflow = wrapper.scrollWidth > wrapper.clientWidth;
            const atStart = wrapper.scrollLeft <= 0;
            const atEnd = wrapper.scrollLeft + wrapper.clientWidth >= wrapper.scrollWidth - 1;

            leftBtn.classList.toggle('visible', hasOverflow && !atStart);
            rightBtn.classList.toggle('visible', hasOverflow && !atEnd);
        };

        const scroll = (direction) => {
            const scrollAmount = wrapper.clientWidth * 0.8;
            wrapper.scrollBy({
                left: direction === 'left' ? -scrollAmount : scrollAmount,
                behavior: 'smooth'
            });
        };

        container.querySelectorAll('.scroll-button').forEach(btn => {
            btn.addEventListener('click', () => scroll(btn.dataset.direction));
        });

        wrapper.addEventListener('scroll', updateButtons);
        window.addEventListener('resize', updateButtons);
        
        // Initial check
        updateButtons();
    });
}

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
                    initializeScrollButtons();
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
