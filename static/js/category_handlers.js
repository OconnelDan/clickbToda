document.addEventListener('DOMContentLoaded', function() {
    initializeTabNavigation();
    loadDefaultCategory();
});

function initializeTabNavigation() {
    const categoryTabs = document.getElementById('categoryTabs');
    const subcategoryTabs = document.getElementById('subcategoryTabs');

    if (!categoryTabs || !subcategoryTabs) return;

    // Add touch scrolling for navigation bars
    [categoryTabs, subcategoryTabs].forEach(container => {
        let touchStartX = 0;
        let startScrollLeft = 0;

        container.addEventListener('touchstart', e => {
            touchStartX = e.touches[0].clientX;
            startScrollLeft = container.scrollLeft;
            container.style.scrollBehavior = 'auto';
        }, { passive: true });

        container.addEventListener('touchmove', e => {
            const touchCurrentX = e.touches[0].clientX;
            const diff = touchStartX - touchCurrentX;
            container.scrollLeft = startScrollLeft + diff;
        }, { passive: true });

        container.addEventListener('touchend', () => {
            container.style.scrollBehavior = 'smooth';
        });
    });

    // Category tab click handler
    categoryTabs.addEventListener('click', function(e) {
        const tabButton = e.target.closest('[data-bs-toggle="tab"]');
        if (!tabButton) return;

        const categoryId = tabButton.dataset.categoryId;
        if (!categoryId) return;

        // Remove active class from all tabs and add to selected
        categoryTabs.querySelectorAll('.nav-link').forEach(tab => tab.classList.remove('active'));
        tabButton.classList.add('active');

        showLoadingState();
        loadCategoryContent(categoryId);
    });
}

function updateNavigation() {
    const categoryTabs = document.getElementById('categoryTabs');
    const subcategoryTabs = document.getElementById('subcategoryTabs');

    if (!categoryTabs || !subcategoryTabs) return;

    // Update category tabs scroll position
    const activeCategoryTab = categoryTabs.querySelector('.nav-link.active');
    if (activeCategoryTab) {
        const tabRect = activeCategoryTab.getBoundingClientRect();
        const containerRect = categoryTabs.getBoundingClientRect();
        if (tabRect.left < containerRect.left || tabRect.right > containerRect.right) {
            activeCategoryTab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        }
    }

    // Update subcategory tabs scroll position
    const activeSubcategoryTab = subcategoryTabs.querySelector('.nav-link.active');
    if (activeSubcategoryTab) {
        const tabRect = activeSubcategoryTab.getBoundingClientRect();
        const containerRect = subcategoryTabs.getBoundingClientRect();
        if (tabRect.left < containerRect.left || tabRect.right > containerRect.right) {
            activeSubcategoryTab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        }
    }
}

function loadDefaultCategory() {
    try {
        const categoryTabs = document.getElementById('categoryTabs');
        if (!categoryTabs) {
            console.error('Category tabs container not found');
            return;
        }

        const tabs = categoryTabs.querySelectorAll('.nav-link');
        if (tabs.length === 0) {
            console.log('Waiting for categories to load...');
            // Retry after a short delay
            setTimeout(loadDefaultCategory, 500);
            return;
        }

        // Remove active class from any previously active tabs
        tabs.forEach(tab => tab.classList.remove('active'));

        // Set the first category as active
        tabs[0].classList.add('active');

        // Load content for the first category
        const categoryId = tabs[0].dataset.categoryId;
        if (!categoryId) {
            console.error('No category ID found on first tab');
            return;
        }

        loadCategoryContent(categoryId);
    } catch (error) {
        console.error('Error loading default category:', error);
        const eventsContent = document.getElementById('events-content');
        if (eventsContent) {
            eventsContent.innerHTML = `
                <div class="alert alert-danger">
                    <h4 class="alert-heading">Error loading categories</h4>
                    <p>Please try refreshing the page. If the problem persists, contact support.</p>
                </div>
            `;
        }
    }
}

function loadCategoryContent(categoryId) {
    if (!categoryId) {
        console.error('No category ID provided');
        showError('Invalid category selection');
        return;
    }

    const timeFilter = document.querySelector('input[name="timeFilter"]:checked').value;
    const subcategoryTabs = document.getElementById('subcategoryTabs');

    // Clear existing subcategories
    subcategoryTabs.innerHTML = '';

    // Show loading state before fetching
    showLoadingState();

    // Fetch subcategories and articles simultaneously
    Promise.all([
        fetch(`/api/subcategories?category_id=${categoryId}&time_filter=${timeFilter}`).then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        }),
        fetch(`/api/articles?category_id=${categoryId}&time_filter=${timeFilter}`).then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
    ])
        .then(([subcategories, articlesData]) => {
            if (!articlesData || !articlesData.categories) {
                throw new Error('Invalid response format');
            }

            // Sort subcategories by article count
            subcategories.sort((a, b) => (b.article_count || 0) - (a.article_count || 0));

            updateSubcategoryTabs(subcategories);
            updateDisplay(articlesData);
            hideLoadingState();
            updateNavigation();
        })
        .catch(error => {
            console.error('Error loading category content:', error);
            showError(`Failed to load category content: ${error.message}`);
            hideLoadingState();
        });
}

function updateSubcategoryTabs(subcategories) {
    const subcategoryTabs = document.getElementById('subcategoryTabs');
    if (!subcategoryTabs) return;

    if (!Array.isArray(subcategories)) {
        console.error('Invalid subcategories data:', subcategories);
        return;
    }

    subcategoryTabs.innerHTML = subcategories.map(subcat => `
        <li class="nav-item" role="presentation">
            <button class="nav-link" 
                    data-bs-toggle="pill"
                    data-subcategory-id="${subcat.id}"
                    type="button">
                ${subcat.nombre}
                <span class="badge bg-secondary ms-1">${subcat.article_count || 0}</span>
            </button>
        </li>
    `).join('');

    // Initialize subcategory click handlers
    subcategoryTabs.querySelectorAll('[data-subcategory-id]').forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all subcategory tabs
            subcategoryTabs.querySelectorAll('.nav-link').forEach(tab => tab.classList.remove('active'));
            // Add active class to clicked tab
            this.classList.add('active');

            const subcategoryId = this.dataset.subcategoryId;
            loadArticlesForSubcategory(subcategoryId);
        });
    });

    updateNavigation();
}

function loadArticlesForSubcategory(subcategoryId) {
    if (!subcategoryId) {
        console.error('No subcategory ID provided');
        return;
    }

    const timeFilter = document.querySelector('input[name="timeFilter"]:checked').value;
    showLoadingState();

    fetch(`/api/articles?subcategory_id=${subcategoryId}&time_filter=${timeFilter}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            updateDisplay(data);
            hideLoadingState();
            updateNavigation();
        })
        .catch(error => {
            console.error('Error loading subcategory articles:', error);
            showError(`Failed to load articles: ${error.message}`);
            hideLoadingState();
        });
}

function showLoadingState() {
    const eventsContent = document.getElementById('events-content');
    if (!eventsContent) return;

    eventsContent.innerHTML = `
        <div class="text-center my-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading content...</p>
        </div>
    `;
}

function hideLoadingState() {
    const loadingDiv = document.querySelector('#events-content .text-center');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

function showError(message, error = null) {
    console.error('Error:', message, error);
    const eventsContent = document.getElementById('events-content');
    if (!eventsContent) return;

    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show';
    errorDiv.innerHTML = `
        <h4 class="alert-heading">Error</h4>
        <p>${message}</p>
        ${error ? `<p class="text-muted small">Technical details: ${error.message || error}</p>` : ''}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    eventsContent.innerHTML = '';
    eventsContent.appendChild(errorDiv);
}

function updateDisplay(data) {
    const eventsContent = document.getElementById('events-content');
    if (!eventsContent) return;

    try {
        if (!data || !data.categories) {
            throw new Error('Invalid response format');
        }

        if (data.categories.length === 0) {
            eventsContent.innerHTML = `
                <div class="alert alert-info">
                    <h4 class="alert-heading">No articles found</h4>
                    <p>Try selecting a different category or time range.</p>
                </div>
            `;
            return;
        }

        const fragment = document.createDocumentFragment();

        data.categories.forEach(category => {
            const categorySection = document.createElement('div');
            categorySection.className = 'category-section mb-5';
            categorySection.dataset.categoryId = category.categoria_id || '';
            categorySection.dataset.loaded = 'true';

            // Sort subcategories by article count (if available)
            const sortedSubcategories = (category.subcategories || []).sort((a, b) => {
                const aCount = (a.events || []).reduce((sum, event) => sum + (event.articles || []).length, 0);
                const bCount = (b.events || []).reduce((sum, event) => sum + (event.articles || []).length, 0);
                return bCount - aCount;
            });

            categorySection.innerHTML = `
                <div class="category-content">
                    ${sortedSubcategories.map(subcategory => {
                        // Sort events by article count
                        const sortedEvents = (subcategory.events || []).sort((a, b) => {
                            return (b.articles || []).length - (a.articles || []).length;
                        });

                        return `
                            <div class="subcategory-section mb-4">
                                <div class="events-container">
                                    ${sortedEvents.map(event => {
                                        // Sort articles by fecha_publicacion
                                        const sortedArticles = (event.articles || []).sort((a, b) => {
                                            return new Date(b.fecha_publicacion || 0) - new Date(a.fecha_publicacion || 0);
                                        });

                                        return `
                                            <div class="event-articles mb-4 mobile-view">
                                                <div class="row">
                                                    <div class="col-md-3">
                                                        <div class="event-info">
                                                            <h4 class="event-title">${event.titulo || 'Untitled Event'}</h4>
                                                            <p class="event-description">${event.descripcion || ''}</p>
                                                            <div class="event-meta">
                                                                <small class="text-muted">${event.fecha_evento || ''}</small>
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div class="col-md-9">
                                                        <div class="articles-carousel mobile-event-container">
                                                            <div class="mobile-carousel">
                                                                <div class="carousel-wrapper">
                                                                    ${sortedArticles.map(article => `
                                                                        <div class="article-card" data-article-id="${article.id}" data-article-url="${article.url || ''}" role="button">
                                                                            <div class="card h-100">
                                                                                <div class="card-body">
                                                                                    <img src="${article.periodico_logo || '/static/img/default-newspaper.svg'}" 
                                                                                         class="newspaper-logo mb-2" alt="Newspaper logo">
                                                                                    <h5 class="card-title article-title ${article.paywall ? 'text-muted' : ''}">
                                                                                        ${article.titular || 'No Title'}
                                                                                    </h5>
                                                                                    ${article.gpt_opinion ? `<div class="article-opinion">${article.gpt_opinion}</div>` : ''}
                                                                                    ${article.paywall ? '<span class="badge bg-secondary">Paywall</span>' : ''}
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                    `).join('')}
                                                                </div>
                                                                <div class="carousel-indicator left hidden">&#10094;</div>
                                                                <div class="carousel-indicator right">&#10095;</div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        `;
                                    }).join('')}
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;

            fragment.appendChild(categorySection);
        });

        eventsContent.innerHTML = '';
        eventsContent.appendChild(fragment);

        // Initialize article cards and touch events
        document.querySelectorAll('.article-card').forEach(card => {
            card.style.cursor = 'pointer';
            card.classList.add('article-card-clickable');
        });

        // Initialize mobile swipe events
        if (window.innerWidth <= 767) {
            document.querySelectorAll('.mobile-view').forEach(mobileView => {
                const container = mobileView.querySelector('.mobile-event-container');
                const carousel = mobileView.querySelector('.mobile-carousel');
                const carouselWrapper = carousel.querySelector('.carousel-wrapper');
                const articles = carouselWrapper.querySelectorAll('.article-card');
                const leftIndicator = carousel.querySelector('.carousel-indicator.left');
                const rightIndicator = carousel.querySelector('.carousel-indicator.right');

                let startX = 0, startY = 0;
                let isDragging = false;
                let isVerticalScroll = false;
                let currentTranslate = 0;
                let prevTranslate = 0;
                let animationFrame = null;
                let currentArticleIndex = 0;
                let isShowingEvent = true;


                // Función para actualizar los indicadores
                function updateIndicators() {
                    leftIndicator.classList.toggle('hidden', currentArticleIndex === 0);
                    rightIndicator.classList.toggle('hidden', currentArticleIndex === articles.length - 1);
                    if (isShowingEvent) {
                        leftIndicator.classList.add('hidden');
                        rightIndicator.classList.remove('hidden');
                    } else {
                        leftIndicator.classList.remove('hidden');
                        rightIndicator.classList.toggle('hidden', currentArticleIndex === articles.length - 1);
                    }
                }

                // Inicializar indicadores
                updateIndicators();

                mobileView.addEventListener('touchstart', (e) => {
                    startX = e.touches[0].clientX;
                    startY = e.touches[0].clientY;
                    isDragging = true;
                    isVerticalScroll = false;
                    cancelAnimationFrame(animationFrame);
                    container.style.transition = 'none';
                    carouselWrapper.style.transition = 'none';
                }, { passive: true });

                mobileView.addEventListener('touchmove', (e) => {
                    if (!isDragging) return;

                    const currentX = e.touches[0].clientX;
                    const currentY = e.touches[0].clientY;
                    const diffX = currentX - startX;
                    const diffY = currentY - startY;
                    const threshold = 10;

                    // Permitir scroll vertical por defecto
                    if (!isVerticalScroll && Math.abs(diffY) > threshold && Math.abs(diffY) > Math.abs(diffX)) {
                        isDragging = false;
                        isVerticalScroll = true;
                        return;
                    }

                    // Manejar el deslizamiento horizontal
                    if (!isVerticalScroll && Math.abs(diffX) > threshold && Math.abs(diffX) > Math.abs(diffY)) {
                        e.preventDefault();

                        if (isShowingEvent) {
                            // Deslizar desde el evento al carrusel
                            currentTranslate = Math.min(0, prevTranslate + diffX);
                        } else {
                            // Deslizar entre artículos
                            const containerWidth = carouselWrapper.offsetWidth;
                            const maxScroll = -(articles.length - 1) * containerWidth;
                            currentTranslate = Math.max(maxScroll, Math.min(0, prevTranslate + diffX));
                        }
                        if (!animationFrame) {
                            animationFrame = requestAnimationFrame(() => {
                                if (isShowingEvent) {
                                    container.style.transform = `translateX(${currentTranslate}px)`;
                                } else {
                                    carouselWrapper.style.transform = `translateX(${currentTranslate}px)`;
                                }
                                animationFrame = null;
                            });
                        }
                    }
                }, { passive: false });

                mobileView.addEventListener('touchend', () => {
                    if (!isDragging) return;
                    isDragging = false;
                    const threshold = carouselWrapper.offsetWidth / 3;

                    if (isShowingEvent) {
                        // Transición del evento al carrusel
                        if (currentTranslate < -threshold) {
                            currentTranslate = -mobileView.offsetWidth;
                            isShowingEvent = false;
                        } else {
                            currentTranslate = 0;
                        }

                        container.style.transition = 'transform 0.3s ease';
                        container.style.transform = `translateX(${currentTranslate}px)`;
                    } else {
                        // Navegación entre artículos
                        const containerWidth = carouselWrapper.offsetWidth;
                        const snapPoint = Math.round(currentTranslate / containerWidth) * containerWidth;
                        currentArticleIndex = Math.abs(Math.round(currentTranslate / containerWidth));

                        carouselWrapper.style.transition = 'transform 0.3s ease';
                        carouselWrapper.style.transform = `translateX(${snapPoint}px)`;
                        currentTranslate = snapPoint;
                        if (currentArticleIndex === 0) isShowingEvent = true;
                    }

                    prevTranslate = currentTranslate;
                    updateIndicators();
                });


                leftIndicator.addEventListener('click', () => {
                    currentArticleIndex = Math.max(0, currentArticleIndex - 1);
                    currentTranslate = -currentArticleIndex * carouselWrapper.offsetWidth;
                    carouselWrapper.style.transition = 'transform 0.3s ease';
                    carouselWrapper.style.transform = `translateX(${currentTranslate}px)`;
                    prevTranslate = currentTranslate;
                    isShowingEvent = (currentArticleIndex === 0);
                    updateIndicators();

                });

                rightIndicator.addEventListener('click', () => {
                    currentArticleIndex = Math.min(articles.length - 1, currentArticleIndex + 1);
                    currentTranslate = -currentArticleIndex * carouselWrapper.offsetWidth;
                    carouselWrapper.style.transition = 'transform 0.3s ease';
                    carouselWrapper.style.transform = `translateX(${currentTranslate}px)`;
                    prevTranslate = currentTranslate;
                    isShowingEvent = false;
                    updateIndicators();
                });
            });
        }


        initializeCarousels();
        initializeScrollButtons();

    } catch (error) {
        console.error('Error updating display:', error);
        showError('Failed to update display', error);
    }
}

// Placeholder functions -  Replace with your actual implementations
function initializeCarousels() {
    // Add your carousel initialization logic here if needed
}

function initializeScrollButtons() {
    // Add your scroll button initialization logic here if needed.
}