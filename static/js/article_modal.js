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
        'articleAuthor': { type: 'text', value: '' },
        'articleAgency': { type: 'text', value: '' },
        'articleSummary': { type: 'text', value: '' },
        'articleOpinion': { type: 'text', value: '' },
        'articleKeywords': { type: 'html', value: '' },
        'articleSources': { type: 'text', value: '' }
    };
    
    for (const [id, config] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            if (config.type === 'img') {
                element.src = config.value;
            } else if (config.type === 'html') {
                element.innerHTML = config.value;
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

function showError(message) {
    console.error('Error:', message);
    const errorDiv = document.getElementById('articleErrorMessage');
    if (!errorDiv) {
        console.error('Error message element not found');
        return;
    }
    
    showLoading(false);
    errorDiv.textContent = message;
    errorDiv.classList.remove('d-none');
}

function fetchArticleDetails(articleId) {
    console.log('Fetching article details:', articleId);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    fetch(`/api/article/${articleId}`, { signal: controller.signal })
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
            showError(error.name === 'AbortError' ? 
                'Request timed out. Please try again.' : 
                'Failed to load article details. Please try again.');
        });
}

function updateModalContent(article) {
    try {
        // Basic article information
        const elements = {
            'modalNewspaperLogo': { type: 'img', value: article.periodico_logo || '/static/img/default-newspaper.svg' },
            'articleModalLabel': { type: 'text', value: article.titular || 'No Title' },
            'articleSubtitle': { type: 'text', value: article.subtitular || '' },
            'articleDate': { type: 'text', value: formatDate(article.fecha_publicacion) },
            'articleAuthor': { type: 'text', value: article.periodista || 'Unknown Author' },
            'articleAgency': { type: 'text', value: article.agencia || '' },
            'articleSummary': { type: 'text', value: article.gpt_resumen || 'No summary available' },
            'articleOpinion': { type: 'text', value: article.gpt_opinion || 'No opinion available' }
        };
        
        for (const [id, config] of Object.entries(elements)) {
            const element = document.getElementById(id);
            if (element) {
                if (config.type === 'img') {
                    element.src = config.value;
                } else {
                    element.textContent = config.value;
                }
            } else {
                console.warn(`Element with id '${id}' not found`);
            }
        }
        
        updateKeywords(article.gpt_palabras_clave);
        updateSources(article.gpt_cantidad_fuentes_citadas);
        updatePaywallWarning(article.paywall);
        updateArticleLink(article.url);
        
        showLoading(false);
    } catch (error) {
        console.error('Error updating modal content:', error);
        showError('Failed to display article details');
    }
}

function formatDate(dateString) {
    if (!dateString) return '';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    } catch (error) {
        console.warn('Error formatting date:', error);
        return dateString;
    }
}

function updateKeywords(keywords) {
    const keywordsDiv = document.getElementById('articleKeywords');
    if (!keywordsDiv) {
        console.error('Keywords element not found');
        return;
    }
    
    if (keywords) {
        const badges = keywords.split(',')
            .map(keyword => keyword.trim())
            .filter(keyword => keyword)
            .map(keyword => `<span class="badge bg-secondary me-1 mb-1">${keyword}</span>`)
            .join('');
        keywordsDiv.innerHTML = badges || '<span class="text-muted">No keywords available</span>';
    } else {
        keywordsDiv.innerHTML = '<span class="text-muted">No keywords available</span>';
    }
}

function updateSources(sourcesCount) {
    const sourcesDiv = document.getElementById('articleSources');
    if (!sourcesDiv) {
        console.error('Sources element not found');
        return;
    }
    
    sourcesDiv.textContent = sourcesCount ? 
        `${sourcesCount} source${sourcesCount !== 1 ? 's' : ''} cited` : 
        'No source information available';
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
