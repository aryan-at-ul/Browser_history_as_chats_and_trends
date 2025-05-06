// JavaScript logic
/**
 * Search page functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const query = searchInput ? searchInput.value.trim() : '';
    
    if (query) {
        performSearch(query);
    }
    
    // Set up analyze results button
    const analyzeBtn = document.getElementById('analyze-results-btn');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', function() {
            analyzeSearchResults(query);
        });
    }
});

async function performSearch(query) {
    const resultsContainer = document.getElementById('search-results-container');
    
    try {
        // Fetch search results
        const response = await apiRequest(`/search?q=${encodeURIComponent(query)}`);
        
        // Render results
        renderSearchResults(response.results, query);
        
    } catch (error) {
        resultsContainer.innerHTML = `
            <div class="card">
                <div class="card-body">
                    <p class="text-danger">Error performing search: ${error.message}</p>
                </div>
            </div>
        `;
    }
}

function renderSearchResults(results, query) {
    const resultsContainer = document.getElementById('search-results-container');
    
    if (!results || results.length === 0) {
        resultsContainer.innerHTML = `
            <div class="card">
                <div class="card-body text-center">
                    <i class="bi bi-search display-4 text-muted"></i>
                    <h3 class="mt-3">No results found</h3>
                    <p class="text-muted">Try a different search query</p>
                </div>
            </div>
        `;
        return;
    }
    
    // Group results by URL
    const groupedResults = {};
    results.forEach(result => {
        if (!groupedResults[result.url]) {
            groupedResults[result.url] = [];
        }
        groupedResults[result.url].push(result);
    });
    
    let html = '';
    
    Object.keys(groupedResults).forEach(url => {
        const groupResults = groupedResults[url];
        const firstResult = groupResults[0];
        
        html += `
            <div class="card mb-3">
                <div class="card-body">
                    <h5 class="card-title">
                        <a href="${url}" target="_blank">${firstResult.title || 'Untitled'}</a>
                    </h5>
                    <h6 class="card-subtitle mb-2 text-muted">${url}</h6>
                    <div class="card-text">
        `;
        
        // Add content snippets
        groupResults.forEach(result => {
            html += `
                <div class="search-snippet mb-2">
                    ${highlightText(truncateText(result.chunk_text, 200), query)}
                </div>
            `;
        });
        
        html += `
                    </div>
                </div>
            </div>
        `;
    });
    
    resultsContainer.innerHTML = html;
}

async function analyzeSearchResults(query) {
    const analysisContainer = document.getElementById('ai-analysis');
    const analyzeBtn = document.getElementById('analyze-results-btn');
    
    try {
        // Show loading state
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Analyzing...';
        
        // Send chat request with the query
        const response = await apiRequest('/chat', 'POST', { 
            query: `Analyze these search results for "${query}". What patterns or insights can you find?` 
        });
        
        // Display analysis
        analysisContainer.innerHTML = `
            <div class="card bg-light">
                <div class="card-body">
                    <p>${response.response}</p>
                    <p class="text-muted small">Analysis based on search results for "${query}"</p>
                </div>
            </div>
        `;
        
    } catch (error) {
        console.error('Analysis error:', error);
        analysisContainer.innerHTML = `
            <div class="alert alert-danger">
                Error analyzing results: ${error.message}
            </div>
        `;
    } finally {
        // Reset button
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<i class="bi bi-magic me-2"></i> Analyze these results';
    }
}