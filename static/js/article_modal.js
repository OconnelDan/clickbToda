// Initialize Bootstrap modal
let articleModal;

document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing article modal...');
    // Initialize the Bootstrap modal
    const modalElement = document.getElementById('articleModal');
    if (modalElement) {
        articleModal = new bootstrap.Modal(modalElement);
        console.log('Modal initialized successfully');
    } else {
        console.error('Modal element not found in the DOM');
    }
    
    // Add click event listeners to all article cards
    document.addEventListener('click', function(event) {
        const articleCard = event.target.closest('.article-card');
        if (!articleCard) return;
        
        console.log('Article card clicked:', articleCard);
        event.preventDefault();
        event.stopPropagation();
        
        const articleId = articleCard.dataset.articleId;
        console.log('Fetching details for article ID:', articleId);
        
        if (!articleId) {
            console.error('No article ID found on clicked card');
            return;
        }
        
        // Show modal with loading state
        showLoading(true);
        hideError();
        
        if (articleModal) {
            articleModal.show();
        } else {
            console.error('Modal not properly initialized');
            return;
        }
        
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
    });
});

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

function showError(message) {
    const errorDiv = document.getElementById('articleErrorMessage');
    if (!errorDiv) {
        console.error('Error message element not found');
        return;
    }
    errorDiv.textContent = message;
    errorDiv.classList.remove('d-none');
}

function hideError() {
    const errorDiv = document.getElementById('articleErrorMessage');
    if (!errorDiv) {
        console.error('Error message element not found');
        return;
    }
    errorDiv.classList.add('d-none');
}

function updateModalContent(article) {
    try {
        // Update basic article information
        const elements = {
            'modalNewspaperLogo': article.periodico_logo || '/static/img/default-newspaper.svg',
            'articleModalLabel': article.titular,
            'articleSubtitle': article.subtitular || '',
            'articleDate': article.fecha_publicacion || '',
            'articleAuthor': article.periodista || '',
            'articleAgency': article.agencia || '',
            'articleSummary': article.gpt_resumen || 'No summary available',
            'articleOpinion': article.gpt_opinion || 'No opinion available'
        };
        
        // Update all elements
        for (const [id, value] of Object.entries(elements)) {
            const element = document.getElementById(id);
            if (element) {
                if (id === 'modalNewspaperLogo') {
                    element.src = value;
                } else {
                    element.textContent = value;
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
