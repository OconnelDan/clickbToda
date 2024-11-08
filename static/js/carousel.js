document.addEventListener('DOMContentLoaded', function() {
    initializeCarousels();
    initializeScrollButtons();
    
    const dateSelector = document.getElementById('dateSelector');
    if (dateSelector) {
        dateSelector.addEventListener('change', function() {
            reloadArticles(this.value);
        });
    }
});

function initializeScrollButtons() {
    document.querySelectorAll('.articles-carousel, .nav-tabs-wrapper, .nav-pills-wrapper').forEach(container => {
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

        let scrollTimeout;
        wrapper.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                requestAnimationFrame(() => {
                    updateButtons();
                    updateEventDetails(wrapper);
                });
            }, 100);
        });

        updateButtons();
        
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
        
        const articlesSection = wrapper.querySelector('.articles-section');
        if (articlesSection) {
            // Initialize event details
            updateEventDetails(wrapper);
            
            // Touch events for articles section
            articlesSection.addEventListener('touchstart', e => {
                touchStartX = e.touches[0].clientX;
                startScrollLeft = articlesSection.scrollLeft;
                isSwiping = true;
                articlesSection.style.scrollBehavior = 'auto';
            }, { passive: true });
            
            articlesSection.addEventListener('touchmove', e => {
                if (!isSwiping) return;
                const touchCurrentX = e.touches[0].clientX;
                const diff = touchStartX - touchCurrentX;
                articlesSection.scrollLeft = startScrollLeft + diff;
            }, { passive: true });
            
            articlesSection.addEventListener('touchend', e => {
                if (!isSwiping) return;
                
                touchEndX = e.changedTouches[0].clientX;
                const diff = touchStartX - touchEndX;
                
                if (Math.abs(diff) > 50) {
                    const scrollAmount = articlesSection.clientWidth * 0.8;
                    articlesSection.style.scrollBehavior = 'smooth';
                    articlesSection.scrollBy({
                        left: diff > 0 ? scrollAmount : -scrollAmount,
                        behavior: 'smooth'
                    });
                }
                
                isSwiping = false;
                updateEventDetails(wrapper);
            });
        }

        // Observer for content changes
        const observer = new MutationObserver(() => {
            initializeScrollButtons();
        });
        
        observer.observe(wrapper, { 
            childList: true, 
            subtree: true 
        });
    });
}

function updateEventDetails(wrapper) {
    const eventDetailsSection = wrapper.querySelector('.event-details-mobile');
    if (!eventDetailsSection) return;

    const articlesSection = wrapper.querySelector('.articles-section');
    if (!articlesSection) return;

    const articles = articlesSection.querySelectorAll('.article-card');
    if (!articles.length) return;

    // Calculate which article is most visible
    const sectionRect = articlesSection.getBoundingClientRect();
    let mostVisibleArticle = null;
    let maxVisibleArea = 0;

    articles.forEach(article => {
        const rect = article.getBoundingClientRect();
        const visibleWidth = Math.min(rect.right, sectionRect.right) - Math.max(rect.left, sectionRect.left);
        if (visibleWidth > maxVisibleArea) {
            maxVisibleArea = visibleWidth;
            mostVisibleArticle = article;
        }
    });

    if (mostVisibleArticle) {
        const eventArticlesDiv = mostVisibleArticle.closest('.event-articles');
        if (eventArticlesDiv) {
            const eventInfo = eventArticlesDiv.querySelector('.event-info');
            if (eventInfo) {
                const title = eventInfo.querySelector('.event-title');
                const description = eventInfo.querySelector('.event-description');
                const date = eventInfo.querySelector('.event-meta small');

                eventDetailsSection.querySelector('.event-title').textContent = title ? title.textContent : '';
                eventDetailsSection.querySelector('.event-description').textContent = description ? description.textContent : '';
                eventDetailsSection.querySelector('.event-date').textContent = date ? date.textContent : '';
            }
        }
    }
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