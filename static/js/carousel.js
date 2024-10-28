document.addEventListener('DOMContentLoaded', function() {
    // Load articles for each category
    document.querySelectorAll('.carousel-container').forEach(container => {
        const categoryId = container.dataset.category;
        loadArticles(container, categoryId);
    });
    
    // Date selector handler
    const dateSelector = document.getElementById('dateSelector');
    if (dateSelector) {
        dateSelector.addEventListener('change', function() {
            document.querySelectorAll('.carousel-container').forEach(container => {
                const categoryId = container.dataset.category;
                loadArticles(container, categoryId, this.value);
            });
        });
    }
});

function loadArticles(container, categoryId, date = null) {
    let url = `/api/articles?category_id=${categoryId}`;
    if (date) url += `&date=${date}`;
    
    fetch(url)
        .then(response => response.json())
        .then(articles => {
            const wrapper = container.querySelector('.carousel-wrapper');
            wrapper.innerHTML = articles.map(article => `
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
            `).join('');
        })
        .catch(error => console.error('Error loading articles:', error));
}
