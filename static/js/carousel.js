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
    // Handle both article carousels and category selectors
    document.querySelectorAll('.articles-carousel, .nav-tabs-wrapper, .nav-pills-wrapper').forEach(container => {
        const wrapper = container.querySelector('.carousel-wrapper, .nav-tabs, .nav-pills');
        const leftBtn = container.querySelector('.scroll-button.left');
        const rightBtn = container.querySelector('.scroll-button.right');
        
        if (!wrapper || !leftBtn || !rightBtn) return;

        const updateButtons = () => {
            const hasOverflow = wrapper.scrollWidth > wrapper.clientWidth;
            const atStart = wrapper.scrollLeft <= 10; // Small threshold for better UX
            const atEnd = wrapper.scrollLeft + wrapper.clientWidth >= wrapper.scrollWidth - 10;

            // Show/hide buttons based on scroll position
            leftBtn.style.display = hasOverflow && !atStart ? 'flex' : 'none';
            rightBtn.style.display = hasOverflow && !atEnd ? 'flex' : 'none';

            // Update opacity for smooth transitions
            leftBtn.style.opacity = hasOverflow && !atStart ? '1' : '0';
            rightBtn.style.opacity = hasOverflow && !atEnd ? '1' : '0';
        };

        const scroll = (direction) => {
            const isCategory = wrapper.classList.contains('nav-tabs') || wrapper.classList.contains('nav-pills');
            const scrollAmount = isCategory ? 200 : wrapper.clientWidth * 0.8;
            
            wrapper.scrollBy({
                left: direction === 'left' ? -scrollAmount : scrollAmount,
                behavior: 'smooth'
            });
        };

        // Button click handlers
        container.querySelectorAll('.scroll-button').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault(); // Prevent any default behavior
                e.stopPropagation(); // Prevent event bubbling
                scroll(btn.dataset.direction);
            });
        });

        // Scroll event listener
        wrapper.addEventListener('scroll', () => {
            requestAnimationFrame(updateButtons);
        });

        // Resize observer for responsive updates
        const resizeObserver = new ResizeObserver(() => {
            requestAnimationFrame(updateButtons);
        });
        resizeObserver.observe(wrapper);
        
        // Initial check
        updateButtons();
    });
}

function initializeCarousels() {
    document.querySelectorAll('.carousel-wrapper').forEach(wrapper => {
        // Add touch event listeners for mobile swipe
        let touchStartX = 0;
        let touchEndX = 0;
        let isSwiping = false;
        
        wrapper.addEventListener('touchstart', e => {
            touchStartX = e.touches[0].clientX;
            isSwiping = true;
        }, { passive: true });
        
        wrapper.addEventListener('touchmove', e => {
            if (!isSwiping) return;
            touchEndX = e.touches[0].clientX;
            // Prevent vertical scroll while swiping horizontally
            if (Math.abs(touchEndX - touchStartX) > 10) {
                e.preventDefault();
            }
        }, { passive: false });
        
        wrapper.addEventListener('touchend', () => {
            if (!isSwiping) return;
            handleSwipe(wrapper, touchStartX, touchEndX);
            isSwiping = false;
        });

        // Reinitialize scroll buttons after content changes
        const observer = new MutationObserver(() => {
            initializeScrollButtons();
        });
        
        observer.observe(wrapper, { 
            childList: true, 
            subtree: true 
        });
    });
}

function handleSwipe(wrapper, startX, endX) {
    const SWIPE_THRESHOLD = 50;
    const difference = startX - endX;
    
    if (Math.abs(difference) > SWIPE_THRESHOLD) {
        const scrollAmount = wrapper.clientWidth * 0.8;
        wrapper.scrollBy({ 
            left: difference > 0 ? scrollAmount : -scrollAmount, 
            behavior: 'smooth' 
        });
    }
}

function reloadArticles(date) {
    const activeTab = document.querySelector('#categoryTabs .nav-link.active');
    const selectedCategoryId = activeTab ? activeTab.dataset.categoryId : null;
    
    let url = '/api/articles';
    const params = new URLSearchParams();
    
    if (selectedCategoryId) params.append('category_id', selectedCategoryId);
    if (date) params.append('date', date);
    
    if (params.toString()) url += `?${params.toString()}`;
    
    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch articles');
            return response.json();
        })
        .then(data => {
            if (!data.categories) throw new Error('Invalid response format');
            
            updateDisplay(data);
            initializeCarousels();
            initializeScrollButtons();
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
