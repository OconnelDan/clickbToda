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
    document.querySelectorAll('.articles-carousel, .nav-tabs-wrapper, .nav-pills-wrapper').forEach(container => {
        // Add scroll buttons if not present
        if (!container.querySelector('.scroll-button.left')) {
            const leftButton = document.createElement('button');
            leftButton.className = 'scroll-button left';
            leftButton.dataset.direction = 'left';
            leftButton.innerHTML = '←';
            container.insertBefore(leftButton, container.firstChild);
        }
        
        if (!container.querySelector('.scroll-button.right')) {
            const rightButton = document.createElement('button');
            rightButton.className = 'scroll-button right';
            rightButton.dataset.direction = 'right';
            rightButton.innerHTML = '→';
            container.appendChild(rightButton);
        }

        const wrapper = container.querySelector('.carousel-wrapper, .nav-tabs, .nav-pills');
        const leftBtn = container.querySelector('.scroll-button.left');
        const rightBtn = container.querySelector('.scroll-button.right');
        
        if (!wrapper || !leftBtn || !rightBtn) return;

        const updateButtons = () => {
            const hasOverflow = wrapper.scrollWidth > wrapper.clientWidth;
            const atStart = wrapper.scrollLeft <= 10;
            const atEnd = wrapper.scrollLeft + wrapper.clientWidth >= wrapper.scrollWidth - 10;

            leftBtn.classList.toggle('visible', hasOverflow && !atStart);
            rightBtn.classList.toggle('visible', hasOverflow && !atEnd);
            
            leftBtn.style.display = hasOverflow && !window.matchMedia('(max-width: 991px)').matches ? 'flex' : 'none';
            rightBtn.style.display = hasOverflow && !window.matchMedia('(max-width: 991px)').matches ? 'flex' : 'none';
        };

        // Button click handlers
        container.querySelectorAll('.scroll-button').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const direction = btn.dataset.direction;
                const scrollAmount = wrapper.clientWidth * 0.8;
                wrapper.scrollBy({
                    left: direction === 'left' ? -scrollAmount : scrollAmount,
                    behavior: 'smooth'
                });
            });
        });

        // Scroll event listener with debouncing
        let scrollTimeout;
        wrapper.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                requestAnimationFrame(updateButtons);
            }, 100);
        });

        // Initial check
        updateButtons();

        // Resize observer for responsive updates
        const resizeObserver = new ResizeObserver(() => {
            requestAnimationFrame(updateButtons);
        });
        resizeObserver.observe(wrapper);
    });
}

function initializeCarousels() {
    document.querySelectorAll('.carousel-wrapper').forEach(wrapper => {
        let touchStartX = 0;
        let touchStartY = 0;
        let touchEndX = 0;
        let touchEndY = 0;
        let startTime = 0;
        let isSwiping = false;
        let startScrollLeft = 0;
        let isScrollingVertically = false;
        
        wrapper.addEventListener('touchstart', e => {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
            startTime = Date.now();
            startScrollLeft = wrapper.scrollLeft;
            isSwiping = true;
            isScrollingVertically = false;
            wrapper.style.scrollBehavior = 'auto';
        }, { passive: true });
        
        wrapper.addEventListener('touchmove', e => {
            if (!isSwiping) return;
            
            const touchCurrentX = e.touches[0].clientX;
            const touchCurrentY = e.touches[0].clientY;
            const deltaX = touchStartX - touchCurrentX;
            const deltaY = touchStartY - touchCurrentY;

            // Determine scroll direction
            if (!isScrollingVertically && Math.abs(deltaX) > Math.abs(deltaY)) {
                e.preventDefault(); // Prevent vertical scroll when swiping horizontally
                wrapper.scrollLeft = startScrollLeft + deltaX;
            } else {
                isScrollingVertically = true;
            }
        }, { passive: false });
        
        wrapper.addEventListener('touchend', e => {
            if (!isSwiping) return;
            
            touchEndX = e.changedTouches[0].clientX;
            touchEndY = e.changedTouches[0].clientY;
            const deltaX = touchStartX - touchEndX;
            const deltaY = touchStartY - touchEndY;
            const elapsedTime = Date.now() - startTime;
            
            // Calculate swipe speed and distance
            const speed = Math.abs(deltaX) / elapsedTime;
            const isSwipe = Math.abs(deltaX) > 50 && Math.abs(deltaX) > Math.abs(deltaY) && speed > 0.2;
            
            if (isSwipe) {
                wrapper.style.scrollBehavior = 'smooth';
                const momentum = Math.min(speed * 500, wrapper.clientWidth);
                wrapper.scrollBy({
                    left: deltaX > 0 ? momentum : -momentum,
                    behavior: 'smooth'
                });
            }
            
            isSwiping = false;
            wrapper.style.scrollBehavior = 'smooth';
        });
        
        // Prevent click events during swipe
        wrapper.addEventListener('click', e => {
            if (Math.abs(touchStartX - touchEndX) > 10) {
                e.preventDefault();
                e.stopPropagation();
            }
        }, true);

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

function reloadArticles(date) {
    const activeTab = document.querySelector('#categoryTabs .nav-link.active');
    const selectedCategoryId = activeTab ? activeTab.dataset.categoryId : null;
    const selectedTimeFilter = document.querySelector('input[name="timeFilter"]:checked').value;
    
    let url = '/api/articles';
    const params = new URLSearchParams();
    
    if (selectedCategoryId) params.append('category_id', selectedCategoryId);
    if (date) params.append('date', date);
    params.append('time_filter', selectedTimeFilter);
    
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
