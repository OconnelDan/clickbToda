document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    
    function performSearch() {
        const query = searchInput.value.trim();
        const date = document.getElementById('dateSelector').value;
        
        document.querySelectorAll('.carousel-container').forEach(container => {
            const categoryId = container.dataset.category;
            let url = `/api/articles?category_id=${categoryId}&q=${encodeURIComponent(query)}`;
            if (date) url += `&date=${date}`;
            
            fetch(url)
                .then(response => response.json())
                .then(articles => {
                    const wrapper = container.querySelector('.carousel-wrapper');
                    if (articles.length === 0) {
                        wrapper.innerHTML = '<div class="text-muted">No articles found</div>';
                    } else {
                        loadArticles(container, categoryId, date);
                    }
                })
                .catch(error => console.error('Error searching articles:', error));
        });
    }
    
    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
});
