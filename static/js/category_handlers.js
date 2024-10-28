document.addEventListener('DOMContentLoaded', function() {
    const categorySelector = document.getElementById('categorySelector');
    const subcategorySelector = document.getElementById('subcategorySelector');
    
    // Load all events initially
    showAllCategories();
    
    // Initialize the category selector
    categorySelector.addEventListener('change', function() {
        const selectedCategoryId = this.value;
        if (selectedCategoryId) {
            fetchSubcategories(selectedCategoryId);
            loadEventsByCategory(selectedCategoryId);
        } else {
            resetSubcategorySelector();
            showAllCategories();
        }
    });
    
    // Handle subcategory selection
    subcategorySelector.addEventListener('change', function() {
        const selectedCategoryId = categorySelector.value;
        const selectedSubcategoryId = this.value;
        if (selectedCategoryId && selectedSubcategoryId) {
            loadEventsBySubcategory(selectedCategoryId, selectedSubcategoryId);
        }
    });
});

function fetchSubcategories(categoryId) {
    fetch(`/api/subcategories?category_id=${categoryId}`)
        .then(response => response.json())
        .then(data => {
            updateSubcategorySelector(data);
        })
        .catch(error => console.error('Error fetching subcategories:', error));
}

function updateSubcategorySelector(subcategories) {
    const subcategorySelector = document.getElementById('subcategorySelector');
    subcategorySelector.innerHTML = '<option value="">Select Subcategory</option>';
    subcategorySelector.disabled = false;
    
    subcategories.forEach(subcategory => {
        const option = document.createElement('option');
        option.value = subcategory.id;
        option.textContent = subcategory.subnombre;
        subcategorySelector.appendChild(option);
    });
}

function resetSubcategorySelector() {
    const subcategorySelector = document.getElementById('subcategorySelector');
    subcategorySelector.innerHTML = '<option value="">Select Subcategory</option>';
    subcategorySelector.disabled = true;
}

function showAllCategories() {
    const date = document.getElementById('dateSelector').value;
    let url = '/api/articles';
    if (date) url += `?date=${date}`;
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            document.querySelectorAll('.category-section').forEach(section => {
                const categoryId = section.dataset.categoryId;
                section.style.display = 'block';
                const eventsContainer = section.querySelector('.events-container');
                const categoryEvents = data.events.filter(event => {
                    return true; // Show all events in each category section
                });
                updateEventsDisplay({ events: categoryEvents }, categoryId);
            });
        })
        .catch(error => console.error('Error loading events:', error));
}

function loadEventsByCategory(categoryId) {
    const date = document.getElementById('dateSelector').value;
    let url = `/api/articles?category_id=${categoryId}`;
    if (date) url += `&date=${date}`;
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            updateEventsDisplay(data, categoryId);
        })
        .catch(error => console.error('Error loading events:', error));
}

function loadEventsBySubcategory(categoryId, subcategoryId) {
    const date = document.getElementById('dateSelector').value;
    let url = `/api/articles?category_id=${categoryId}&subcategory_id=${subcategoryId}`;
    if (date) url += `&date=${date}`;
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            updateEventsDisplay(data, categoryId);
        })
        .catch(error => console.error('Error loading events:', error));
}

function updateEventsDisplay(data, categoryId) {
    const categorySection = document.querySelector(`.category-section[data-category-id="${categoryId}"]`);
    if (!categorySection) return;
    
    const eventsContainer = categorySection.querySelector('.events-container');
    
    if (data.events && data.events.length > 0) {
        eventsContainer.innerHTML = data.events.map(event => `
            <div class="event-articles mb-4">
                <div class="row">
                    <div class="col-md-3">
                        <div class="event-info">
                            <h4 class="event-title">${event.titulo}</h4>
                            <p class="event-description">${event.descripcion || ''}</p>
                            <div class="event-meta">
                                <small class="text-muted">${event.fecha_evento || ''}</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-9">
                        <div class="articles-carousel">
                            <div class="carousel-wrapper">
                                ${event.articles.map(article => `
                                    <div class="article-card">
                                        <div class="card h-100">
                                            <div class="card-body">
                                                <img src="${article.periodico_logo || '/static/img/default-newspaper.svg'}" 
                                                     class="newspaper-logo mb-2" alt="Newspaper logo">
                                                <h5 class="card-title article-title ${article.paywall ? 'text-muted' : ''}">
                                                    ${article.titular}
                                                </h5>
                                                ${article.paywall ? '<span class="badge bg-secondary">Paywall</span>' : ''}
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    } else {
        eventsContainer.innerHTML = '<div class="alert alert-info">No events found</div>';
    }
}
