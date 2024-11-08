// Only updating the relevant sorting functions, rest of the file remains same
function updateDisplay(data) {
    const eventsContent = document.getElementById('events-content');
    if (!eventsContent) return;

    try {
        if (!data || !data.categories) {
            throw new Error('Invalid response format');
        }
        
        if (data.categories.length === 0) {
            eventsContent.innerHTML = `
                <div class="alert alert-info">
                    <h4 class="alert-heading">Loading Content...</h4>
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `;
            setTimeout(() => reloadArticles(), 2000);
            return;
        }

        const fragment = document.createDocumentFragment();
        
        // Sort categories by article count descending
        data.categories.sort((a, b) => {
            const aCount = a.article_count || 0;
            const bCount = b.article_count || 0;
            return bCount - aCount;
        });
        
        data.categories.forEach(category => {
            const categorySection = document.createElement('div');
            categorySection.className = 'category-section mb-5';
            categorySection.dataset.categoryId = category.categoria_id || '';
            categorySection.dataset.loaded = 'true';
            
            // Sort subcategories by article count descending
            const sortedSubcategories = (category.subcategories || []).sort((a, b) => {
                const aCount = a.article_count || 0;
                const bCount = b.article_count || 0;
                return bCount - aCount;
            });

            categorySection.innerHTML = `
                <h2 class="mb-3">
                    ${category.nombre || 'Unnamed Category'}
                    <span class="badge bg-secondary">${category.article_count || 0}</span>
                </h2>
                <div class="category-content">
                    ${sortedSubcategories.map(subcategory => {
                        // Sort events by article count descending
                        const sortedEvents = (subcategory.events || []).sort((a, b) => {
                            const aCount = a.article_count || 0;
                            const bCount = b.article_count || 0;
                            if (bCount !== aCount) return bCount - aCount;
                            // Secondary sort by date if counts are equal
                            return (b.fecha_evento || '') > (a.fecha_evento || '') ? 1 : -1;
                        });

                        return `
                            <div class="subcategory-section mb-4">
                                ${subcategory.nombre ? 
                                    `<h3 class="h4 mb-3">
                                        ${subcategory.nombre}
                                        <span class="badge bg-secondary">${subcategory.article_count || 0}</span>
                                    </h3>` : 
                                    ''}
                                <div class="events-container">
                                    ${sortedEvents.map(event => `
                                        <div class="event-articles mb-4">
                                            <div class="row">
                                                <div class="col-md-3">
                                                    <div class="event-info">
                                                        <h4 class="event-title">
                                                            ${event.titulo || 'Untitled Event'}
                                                            <span class="badge bg-secondary">${event.article_count || 0}</span>
                                                        </h4>
                                                        <p class="event-description">${event.descripcion || ''}</p>
                                                        <div class="event-meta">
                                                            <small class="text-muted">${event.fecha_evento || ''}</small>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div class="col-md-9">
                                                    <div class="articles-carousel">
                                                        <div class="carousel-wrapper">
                                                            ${(event.articles || []).map(article => `
                                                                <div class="article-card" data-article-id="${article.id}" data-article-url="${article.url || ''}" role="button">
                                                                    <div class="card h-100">
                                                                        <div class="card-body">
                                                                            <img src="${article.periodico_logo || '/static/img/default-newspaper.svg'}" 
                                                                                 class="newspaper-logo mb-2" alt="Newspaper logo">
                                                                            <h5 class="card-title article-title ${article.paywall ? 'text-muted' : ''}">
                                                                                ${article.titular || 'No Title'}
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
                                    `).join('')}
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
            
            fragment.appendChild(categorySection);
        });
        
        eventsContent.innerHTML = '';
        eventsContent.appendChild(fragment);

        document.querySelectorAll('.article-card').forEach(card => {
            card.style.cursor = 'pointer';
            card.classList.add('article-card-clickable');
        });

        initializeCarousels();
    } catch (error) {
        console.error('Error updating display:', error);
        showError('Error loading content. Retrying...');
        setTimeout(() => reloadArticles(), 2000);
    }
}
