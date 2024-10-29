document.addEventListener('DOMContentLoaded', function() {
    initializeTabNavigation();
    showAllCategories();
});

function initializeTabNavigation() {
    const tabElements = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabElements.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const categoryId = event.target.dataset.categoryId;
            if (categoryId) {
                fetchSubcategories(categoryId);
                loadEventsByCategory(categoryId);
            } else {
                hideSubcategoryTabs();
                showAllCategories();
            }
        });
    });

    // Handle subcategory clicks
    const subcategoryNav = document.querySelector('.subcategory-nav');
    if (subcategoryNav) {
        subcategoryNav.addEventListener('click', function(e) {
            const tabButton = e.target.closest('[role="tab"]');
            if (!tabButton) return;

            // Remove active class from all tabs
            const allSubcategoryTabs = subcategoryNav.querySelectorAll('[role="tab"]');
            allSubcategoryTabs.forEach(tab => {
                tab.classList.remove('active');
                tab.setAttribute('aria-selected', 'false');
            });
            
            // Add active class to clicked tab
            tabButton.classList.add('active');
            tabButton.setAttribute('aria-selected', 'true');

            const categoryId = document.querySelector('#categoryTabs .nav-link.active').dataset.categoryId;
            const subcategoryId = tabButton.dataset.subcategoryId;

            if (categoryId && subcategoryId) {
                loadEventsBySubcategory(categoryId, subcategoryId);
            } else if (categoryId) {
                loadEventsByCategory(categoryId);
            }
        });
    }
}

function showLoadingIndicator(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="text-center my-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading content...</p>
            </div>
        `;
    }
}

function showError(message, error = null) {
    console.error('Error:', message, error);
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show';
    errorDiv.innerHTML = `
        ${message}
        ${error ? `<br><small class="text-muted">Technical details: ${error.message || error}</small>` : ''}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(errorDiv, container.firstChild);
        setTimeout(() => {
            errorDiv.classList.add('fade');
            setTimeout(() => errorDiv.remove(), 300);
        }, 5000);
    }
}

function fetchSubcategories(categoryId) {
    const subcategoryNav = document.querySelector('.subcategory-nav');
    if (!subcategoryNav) return;

    fetch(`/api/subcategories?category_id=${categoryId}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (data && data.length > 0) {
                updateSubcategoryTabs(data);
                showSubcategoryNav();
            } else {
                hideSubcategoryTabs();
            }
        })
        .catch(error => {
            console.error('Error fetching subcategories:', error);
            hideSubcategoryTabs();
            showError('Failed to load subcategories', error);
        });
}

function updateSubcategoryTabs(subcategories) {
    const subcategoryTabs = document.getElementById('subcategoryTabs');
    if (!subcategoryTabs) return;

    // Create a Set to store unique subcategory names
    const uniqueSubcategories = new Set();
    const filteredSubcategories = subcategories.filter(subcat => {
        if (!subcat.subnombre) return false;
        const key = `${subcat.id}-${subcat.subnombre}`;
        if (!uniqueSubcategories.has(key)) {
            uniqueSubcategories.add(key);
            return true;
        }
        return false;
    });

    if (filteredSubcategories.length === 0) {
        hideSubcategoryTabs();
        return;
    }

    subcategoryTabs.innerHTML = `
        <li class="nav-item" role="presentation">
            <button class="nav-link active" role="tab" data-subcategory-id="" 
                    aria-selected="true">
                All
            </button>
        </li>
        ${filteredSubcategories.map(subcategory => `
            <li class="nav-item" role="presentation">
                <button class="nav-link" role="tab" data-subcategory-id="${subcategory.id}"
                        aria-selected="false">
                    ${subcategory.subnombre || 'Unnamed'}
                </button>
            </li>
        `).join('')}
    `;
}

function showSubcategoryNav() {
    const subcategoryNav = document.querySelector('.subcategory-nav');
    if (subcategoryNav) {
        subcategoryNav.style.display = 'block';
        // Trigger reflow
        subcategoryNav.offsetHeight;
        subcategoryNav.classList.add('show');
    }
}

function hideSubcategoryTabs() {
    const subcategoryNav = document.querySelector('.subcategory-nav');
    if (subcategoryNav) {
        subcategoryNav.classList.remove('show');
        setTimeout(() => {
            subcategoryNav.style.display = 'none';
            subcategoryNav.innerHTML = '';
        }, 300);
    }
}

// Rest of the functions (showAllCategories, loadEventsByCategory, etc.) remain unchanged...
