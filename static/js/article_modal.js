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
        
        // Add modal events for debugging
        modalElement.addEventListener('show.bs.modal', function() {
            console.log('Modal is about to be shown');
        });
        
        modalElement.addEventListener('shown.bs.modal', function() {
            console.log('Modal is now visible');
        });
    } catch (error) {
        console.error('Error initializing modal:', error);
    }
}

function setupEventDelegation() {
    // Use event delegation for dynamically loaded cards
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
            return;
        }
        
        // Show modal with loading state
        showLoading(true);
        hideError();
        articleModal.show();
        
        // Fetch article details
        fetchArticleDetails(articleId);
    });
}

function showLoading(show) {
    console.log('Toggling loading state:', show);
    const spinner = document.getElementById('articleLoadingSpinner');
    const content = document.getElementById('articleContent');
    if (!spinner || !content) {
        console.error('Loading elements not found');
        return;
    }
    spinner.classList.toggle('d-none', !show);
    content.classList.toggle('d-none', show);
}

function hideError() {
    const errorDiv = document.getElementById('articleErrorMessage');
    if (!errorDiv) {
        console.error('Error message element not found');
        return;
    }
    errorDiv.classList.add('d-none');
}

function showError(message) {
    console.error('Error:', message);
    const errorDiv = document.getElementById('articleErrorMessage');
    if (!errorDiv) {
        console.error('Error message element not found');
        return;
    }
    errorDiv.textContent = message;
    errorDiv.classList.remove('d-none');
}

function fetchArticleDetails(articleId) {
    console.log('Fetching article details:', articleId);
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

function updateModalContent(article) {
    try {
        const elements = {
            'modalNewspaperLogo': { type: 'img', value: article.periodico_logo || '/static/img/default-newspaper.svg' },
            'articleModalLabel': { type: 'text', value: article.titular },
            'articleSubtitle': { type: 'text', value: article.subtitular || '' },
            'articleDate': { type: 'text', value: article.fecha_publicacion || '' },
            'articleAuthor': { type: 'text', value: article.periodista || '' },
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
                console.error(`Element with id '${id}' not found`);
            }
        }
        
        updateKeywords(article.gpt_palabras_clave);
        updateSources(article.gpt_cantidad_fuentes_citadas);
        updatePaywallWarning(article.paywall);
        updateArticleLink(article.url);
    } catch (error) {
        console.error('Error updating modal content:', error);
        showError('Failed to display article details');
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
            .map(keyword => `<span class="badge bg-secondary me-1">${keyword.trim()}</span>`)
            .join('');
        keywordsDiv.innerHTML = badges;
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
        `${sourcesCount} sources cited` : 
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