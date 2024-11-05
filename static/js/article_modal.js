// Initialize modal globally
let articleModal = null;

// Initialize the modal
function initModal() {
    console.log('Initializing article modal...');
    const modalElement = document.getElementById('articleModal');
    if (!modalElement) {
        console.error('Modal element not found in the DOM');
        return false;
    }
    try {
        articleModal = new bootstrap.Modal(modalElement);
        console.log('Modal initialized successfully');
        return true;
    } catch (error) {
        console.error('Error initializing modal:', error);
        return false;
    }
}

// Add click handlers to article cards
function addClickHandlers() {
    console.log('Adding click handlers to article cards...');
    document.addEventListener('click', handleArticleClick);
}

// Handle article card clicks
function handleArticleClick(event) {
    const articleCard = event.target.closest('.article-card');
    if (!articleCard) return;
    
    console.log('Article card clicked:', articleCard);
    event.preventDefault();
    event.stopPropagation();
    
    const articleId = articleCard.dataset.articleId;
    if (!articleId) {
        console.error('No article ID found on clicked card');
        return;
    }
    
    console.log('Fetching details for article ID:', articleId);
    showArticleDetails(articleId);
}

// Show article details in modal
function showArticleDetails(articleId) {
    if (!articleModal) {
        console.error('Modal not initialized');
        if (!initModal()) {
            showError('Unable to display article details. Please try again.');
            return;
        }
    }
    
    // Show modal with loading state
    showLoading(true);
    hideError();
    articleModal.show();
    
    // Fetch article details
    fetch(`/api/article/${articleId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(article => {
            console.log('Article details received:', article);
            updateModalContent(article);
            showLoading(false);
        })
        .catch(error => {
            console.error('Error loading article details:', error);
            showError('Failed to load article details. Please try again.');
            showLoading(false);
        });
}

// Show/hide loading state
function showLoading(show) {
    const spinner = document.getElementById('articleLoadingSpinner');
    const content = document.getElementById('articleContent');
    
    if (!spinner || !content) {
        console.error('Loading spinner or content elements not found');
        return;
    }
    
    if (show) {
        spinner.classList.remove('d-none');
        content.classList.add('d-none');
    } else {
        spinner.classList.add('d-none');
        content.classList.remove('d-none');
    }
}

// Show error message
function showError(message) {
    const errorDiv = document.getElementById('articleErrorMessage');
    if (!errorDiv) {
        console.error('Error message element not found');
        return;
    }
    errorDiv.textContent = message;
    errorDiv.classList.remove('d-none');
}

// Hide error message
function hideError() {
    const errorDiv = document.getElementById('articleErrorMessage');
    if (!errorDiv) {
        console.error('Error message element not found');
        return;
    }
    errorDiv.classList.add('d-none');
}

// Update modal content with article details
function updateModalContent(article) {
    try {
        const elements = {
            modalNewspaperLogo: {
                type: 'img',
                value: article.periodico_logo || '/static/img/default-newspaper.svg'
            },
            articleModalLabel: {
                type: 'text',
                value: article.titular
            },
            articleSubtitle: {
                type: 'text',
                value: article.subtitular || ''
            },
            articleDate: {
                type: 'text',
                value: article.fecha_publicacion || ''
            },
            articleAuthor: {
                type: 'text',
                value: article.periodista || ''
            },
            articleAgency: {
                type: 'text',
                value: article.agencia || ''
            },
            articleSummary: {
                type: 'text',
                value: article.gpt_resumen || 'No summary available'
            },
            articleOpinion: {
                type: 'text',
                value: article.gpt_opinion || 'No opinion available'
            }
        };
        
        // Update all elements
        for (const [id, config] of Object.entries(elements)) {
            const element = document.getElementById(id);
            if (element) {
                if (config.type === 'img') {
                    element.src = config.value;
                } else {
                    element.textContent = config.value;
                }
            } else {
                console.error(`Element with id '${id}' not found`);
            }
        }
        
        // Update keywords with badges
        const keywordsDiv = document.getElementById('articleKeywords');
        if (keywordsDiv) {
            if (article.gpt_palabras_clave) {
                const keywords = article.gpt_palabras_clave.split(',').map(keyword => 
                    `<span class="badge bg-secondary me-1">${keyword.trim()}</span>`
                ).join('');
                keywordsDiv.innerHTML = keywords;
            } else {
                keywordsDiv.innerHTML = '<span class="text-muted">No keywords available</span>';
            }
        }
        
        // Update sources count
        const sourcesDiv = document.getElementById('articleSources');
        if (sourcesDiv) {
            sourcesDiv.textContent = article.gpt_cantidad_fuentes_citadas ? 
                `${article.gpt_cantidad_fuentes_citadas} sources cited` : 
                'No source information available';
        }
        
        // Update article link
        const articleLink = document.getElementById('articleLink');
        if (articleLink && article.url) {
            articleLink.href = article.url;
        }
        
        // Show/hide paywall warning
        const paywallWarning = document.getElementById('paywallWarning');
        if (paywallWarning) {
            if (article.paywall) {
                paywallWarning.classList.remove('d-none');
            } else {
                paywallWarning.classList.add('d-none');
            }
        }
    } catch (error) {
        console.error('Error updating modal content:', error);
        showError('Failed to display article details');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing modal and handlers...');
    initModal();
    addClickHandlers();
});
