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
    
    // Filter button handler
    const filterButton = document.querySelector('.filter');
    if (filterButton) {
        filterButton.dataset.order = 'desc'; // Default order
        filterButton.addEventListener('click', function() {
            console.log('Filter button clicked'); // Log para confirmar clic en el botón
            toggleOrder(this);
        });
    }
});

function toggleOrder(button) {
    if (!button) {
        console.log('Button not found!'); // Log para verificar si el botón existe
        return;
    }

    const currentOrder = button.dataset.order;
    console.log('Current order:', currentOrder); // Log para mostrar el orden actual

    const newOrder = currentOrder === 'desc' ? 'asc' : 'desc';
    button.dataset.order = newOrder;
    button.innerHTML = newOrder === 'desc' ? 'Filtrar por fecha descendente' : 'Filtrar por fecha ascendente';

    console.log('New order set to:', newOrder); // Log para mostrar el nuevo orden

    // Llamar a reloadArticles con el nuevo orden
    reloadArticles(null, newOrder);
}

function reloadArticles(date, order = 'desc') {
    const activeTab = document.querySelector('#categoryTabs .nav-link.active');
    const selectedCategoryId = activeTab ? activeTab.dataset.categoryId : null;
    const selectedTimeFilter = document.querySelector('input[name="timeFilter"]:checked').value;

    let url = '/api/articles';
    const params = new URLSearchParams();

    if (selectedCategoryId) params.append('category_id', selectedCategoryId);
    if (date) params.append('date', date);
    params.append('time_filter', selectedTimeFilter);
    params.append('order', order);

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
            
            leftBtn.style.display = hasOverflow ? 'flex' : 'none';
            rightBtn.style.display = hasOverflow ? 'flex' : 'none';
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
                e.preventDefault();
                e.stopPropagation();
                scroll(btn.dataset.direction);
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
        let touchEndX = 0;
        let isSwiping = false;
        let startScrollLeft = 0;

        wrapper.addEventListener('touchstart', e => {
            touchStartX = e.touches[0].clientX;
            startScrollLeft = wrapper.scrollLeft;
            isSwiping = true;
            wrapper.style.scrollBehavior = 'auto';  // Disable smooth scrolling during swipe
        }, { passive: true });

        wrapper.addEventListener('touchmove', e => {
            if (!isSwiping) return;
            const touchCurrentX = e.touches[0].clientX;
            const diff = touchStartX - touchCurrentX;
            wrapper.scrollLeft = startScrollLeft + diff;
        }, { passive: true });

        wrapper.addEventListener('touchend', e => {
            if (!isSwiping) return;

            touchEndX = e.changedTouches[0].clientX;
            const diff = touchStartX - touchEndX;

            // Determine scroll direction based on swipe
            const articleWidth = wrapper.querySelector('.article-card').clientWidth + parseInt(getComputedStyle(wrapper).gap);
            const scrollAmount = Math.round(diff / articleWidth) * articleWidth;

            wrapper.style.scrollBehavior = 'smooth';  // Re-enable smooth scrolling
            wrapper.scrollBy({
                left: scrollAmount,
                behavior: 'smooth'
            });

            isSwiping = false;
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



function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show';
    errorDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('.container').insertBefore(errorDiv, document.querySelector('.container').firstChild);
}
