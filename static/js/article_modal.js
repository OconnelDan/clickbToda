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
        // Update modal header
        document.getElementById('modalNewspaperLogo').src = article.periodico_logo || '/static/img/default-newspaper.svg';
        document.getElementById('articleModalLabel').textContent = article.titular;
        
        // Update article details
        document.getElementById('articleSubtitle').textContent = article.subtitular || '';
        document.getElementById('articleDate').textContent = article.fecha_publicacion || '';
        document.getElementById('articleAuthor').textContent = article.periodista || '';
        document.getElementById('articleAgency').textContent = article.agencia || '';
        
        // Update summary and opinion
        document.getElementById('articleSummary').textContent = article.gpt_resumen || 'No summary available';
        document.getElementById('articleOpinion').textContent = article.gpt_opinion || 'No opinion available';
        
        // Update keywords
        const keywordsDiv = document.getElementById('articleKeywords');
        if (article.gpt_palabras_clave) {
            const keywords = article.gpt_palabras_clave.split(',');
            keywordsDiv.innerHTML = keywords
                .map(keyword => `<span class="badge bg-secondary me-1">${keyword.trim()}</span>`)
                .join('');
        } else {
            keywordsDiv.innerHTML = '<span class="text-muted">No keywords available</span>';
        }
        
        // Update sources
        const sourcesDiv = document.getElementById('articleSources');
        sourcesDiv.textContent = article.gpt_cantidad_fuentes_citadas ? 
            `${article.gpt_cantidad_fuentes_citadas} sources cited` : 
            'No source information available';
        
        // Update paywall warning
        document.getElementById('paywallWarning').classList.toggle('d-none', !article.paywall);
        
        // Update article link
        const articleLink = document.getElementById('articleLink');
        if (article.url) {
            articleLink.href = article.url;
            articleLink.classList.remove('d-none');
        } else {
            articleLink.classList.add('d-none');
        }
    } catch (error) {
        console.error('Error updating modal content:', error);
        showError('Failed to display article details');
    }
}
