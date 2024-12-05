// Global modal instance
let articleModal;

document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing article modal...');
    
    initializeModal();
    setupEventDelegation();
});

function initializeModal() {
    const modalElement = document.getElementById('articleModal');
    if (!modalElement) {
        console.error('Modal element not found in the DOM');
        return;
    }
    
    try {
        articleModal = new bootstrap.Modal(modalElement);
        console.log('Modal initialized successfully');
        
        // Add modal events for loading states
        modalElement.addEventListener('show.bs.modal', function() {
            console.log('Modal is about to be shown');
            showLoading(true);
            hideError();
        });
        
        modalElement.addEventListener('hidden.bs.modal', function() {
            console.log('Modal was hidden');
            resetModalContent();
        });
    } catch (error) {
        console.error('Error initializing modal:', error);
        showError('Failed to initialize article modal');
    }
}

function setupEventDelegation() {
    document.addEventListener('click', function(event) {
        const articleCard = event.target.closest('.article-card');
        if (!articleCard) return;
        
        event.preventDefault();
        event.stopPropagation();
        
        const articleId = articleCard.dataset.articleId;
        console.log('Article card clicked:', articleId);
        
        if (!articleId) {
            console.error('No article ID found on clicked card');
            return;
        }
        
        if (!articleModal) {
            console.error('Modal not properly initialized');
            showError('Unable to display article details');
            return;
        }
        
        // Show modal and fetch article details
        articleModal.show();
        fetchArticleDetails(articleId);
    });
}

function resetModalContent() {
    const elements = {
        'modalNewspaperLogo': { type: 'img', value: '/static/img/default-newspaper.svg' },
        'articleModalLabel': { type: 'text', value: '' },
        'articleSubtitle': { type: 'text', value: '' },
        'articleDate': { type: 'text', value: '' },
        'articleAgency': { type: 'text', value: '' },
        'articleSummary': { type: 'text', value: '' },
        'articleAuthor': { type: 'text', value: '' }
    };
    
    for (const [id, config] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            if (config.type === 'img') {
                element.src = config.value;
            } else {
                element.textContent = config.value;
            }
        }
    }
    
    hideError();
    showLoading(false);
}

function showLoading(show) {
    console.log('Toggling loading state:', show);
    const elements = {
        'articleLoadingSpinner': show,
        'articleContent': !show,
        'articleErrorMessage': false
    };
    
    for (const [id, visible] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            element.classList.toggle('d-none', !visible);
        } else {
            console.error(`Element with id '${id}' not found`);
        }
    }
}

function hideError() {
    const errorDiv = document.getElementById('articleErrorMessage');
    if (errorDiv) {
        errorDiv.classList.add('d-none');
        errorDiv.textContent = '';
    }
}

function showError(message, error = null, retryCallback = null) {
    console.error('Error:', message, error);
    const errorDiv = document.getElementById('articleErrorMessage');
    if (!errorDiv) return;
    
    showLoading(false);
    errorDiv.innerHTML = `
        ${message}
        ${error ? `<br><small class="text-muted">Details: ${error.message || error}</small>` : ''}
        ${retryCallback ? `<button class="btn btn-outline-primary btn-sm ms-3" onclick="window.retryCallback = ${retryCallback}; window.retryCallback();">Retry</button>` : ''}
    `;
    errorDiv.classList.remove('d-none');
}

function fetchArticleDetails(articleId, retryCount = 0) {
    console.log('Fetching article details:', articleId);
    
    const maxRetries = 3;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    
    fetch(`/api/article/${articleId}`, { 
        signal: controller.signal,
        headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    })
        .then(response => {
            clearTimeout(timeoutId);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(article => {
            console.log('Article details received:', article);
            if (!article || typeof article !== 'object') {
                throw new Error('Invalid article data received');
            }
            updateModalContent(article);
        })
        .catch(error => {
            clearTimeout(timeoutId);
            console.error('Error loading article details:', error);
            
            if (retryCount < maxRetries) {
                console.log(`Retrying... Attempt ${retryCount + 1} of ${maxRetries}`);
                setTimeout(() => {
                    fetchArticleDetails(articleId, retryCount + 1);
                }, 1000 * (retryCount + 1)); // Exponential backoff
            } else {
                showError(
                    'Failed to load article details. Please try again.',
                    error,
                    () => fetchArticleDetails(articleId)
                );
            }
        });
}

function updateModalContent(article) {
    try {
        // Basic article information
        const elements = {
            'modalNewspaperLogo': { type: 'img', value: article.periodico_logo || '/static/img/default-newspaper.svg' },
            'articleModalLabel': { type: 'text', value: article.titular || 'No Title' },
            'articleSubtitle': { type: 'text', value: article.subtitular || '' },
            'articleDate': { type: 'text', value: `Publicado el: ${formatDate(article.fecha_publicacion)}` },
            'articleUpdateDate': { type: 'text', value: article.updated_on ? `Actualizado el: ${formatDate(article.updated_on, true)}` : '' },
            'articleAgency': { type: 'text', value: article.agencia || '' },
            'articleSummary': { type: 'text', value: article.gpt_resumen || 'No summary available' },
            'articleAuthor': { type: 'text', value: article.periodista || 'Unknown Author' }
        };
        
        for (const [id, config] of Object.entries(elements)) {
            const element = document.getElementById(id);
            if (element) {
                if (config.type === 'img') {
                    element.src = config.value;
                } else {
                    element.textContent = config.value;
                }
            }
        }
        
        updatePaywallWarning(article.paywall);
        updateArticleLink(article.url);
        
        showLoading(false);
    } catch (error) {
        console.error('Error updating modal content:', error);
        showError('Failed to display article details');
    }
}

function formatDate(dateString, includeTime = false) {
    if (!dateString) return '';
    try {
        const date = new Date(dateString);
        const options = {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            ...(includeTime && {
                hour: '2-digit',
                minute: '2-digit'
            })
        };
        return date.toLocaleDateString('es-ES', options);
    } catch (error) {
        console.warn('Error formatting date:', error);
        return dateString;
    }
}

function updatePaywallWarning(hasPaywall) {
    const paywallWarning = document.getElementById('paywallWarning');
    if (!paywallWarning) {
        console.error('Paywall warning element not found');
        return;
    }
    
    paywallWarning.classList.toggle('d-none', !hasPaywall);
}

function updateArticleLink(url) {
    const articleLink = document.getElementById('articleLink');
    if (!articleLink) {
        console.error('Article link element not found');
        return;
    }
    
    if (url) {
        articleLink.href = url;
        articleLink.classList.remove('d-none');
    } else {
        articleLink.classList.add('d-none');
    }
}