/**
 * Domain details page functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Load domain data
    loadDomainData();
    
    // Set up refresh button
    const refreshBtn = document.getElementById('refreshDomainBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadDomainData);
    }
    
    // Set up domain query
    const queryBtn = document.getElementById('domain-query-btn');
    const queryInput = document.getElementById('domain-query-input');
    
    if (queryBtn && queryInput) {
        queryBtn.addEventListener('click', function() {
            const query = queryInput.value.trim();
            if (query) {
                handleDomainQuery(query);
            }
        });
        
        queryInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const query = queryInput.value.trim();
                if (query) {
                    handleDomainQuery(query);
                }
            }
        });
    }
});

async function loadDomainData() {
    try {
        // Get domain name from global variable
        if (typeof domainName === 'undefined') {
            console.error('Domain name not defined');
            return;
        }
        
        // Fetch domain analysis
        const response = await apiRequest(`/domain/${encodeURIComponent(domainName)}`);
        
        // Render domain analysis
        renderDomainAnalysis(response.analysis);
        
        // Render history table
        renderDomainHistory(response.history);
        
        // Render history chart
        renderDomainHistoryChart(response.history);
        
    } catch (error) {
        console.error('Error loading domain data:', error);
        showNotification('Error loading domain data', 'danger');
    }
}

function renderDomainAnalysis(analysis) {
    const container = document.getElementById('domain-analysis');
    
    if (analysis) {
        container.innerHTML = `<p>${analysis}</p>`;
    } else {
        container.innerHTML = '<p class="text-center text-muted">No analysis available</p>';
    }
}

function renderDomainHistory(history) {
    const container = document.getElementById('domain-pages-table');
    
    if (!history || history.length === 0) {
        container.innerHTML = '<tr><td colspan="4" class="text-center">No history available</td></tr>';
        return;
    }
    
    let html = '';
    
    history.forEach(item => {
        html += `
            <tr>
                <td>${item.title || 'Untitled'}</td>
                <td>
                    <a href="${item.url}" target="_blank" title="${item.url}">
                        ${truncateText(item.url, 50)}
                    </a>
                </td>
                <td>${item.visit_count}</td>
                <td>${formatDate(item.last_visit_time)}</td>
            </tr>
        `;
    });
    
    container.innerHTML = html;
}

function renderDomainHistoryChart(history) {
    // Group by date
    const dateGroups = {};
    
    history.forEach(item => {
        const date = new Date(item.last_visit_time).toLocaleDateString();
        if (!dateGroups[date]) {
            dateGroups[date] = 0;
        }
        dateGroups[date]++;
    });
    
    // Convert to arrays for chart
    const dates = Object.keys(dateGroups).sort();
    const counts = dates.map(date => dateGroups[date]);
    
    // Create chart
    const ctx = document.getElementById('domainHistoryChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dates,
            datasets: [{
                label: 'Pages Visited',
                data: counts,
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

async function handleDomainQuery(query) {
    const responseContainer = document.getElementById('domain-query-response');
    const responseText = document.getElementById('domain-response-text');
    const queryBtn = document.getElementById('domain-query-btn');
    
    try {
        // Show response container and loading state
        responseContainer.classList.remove('d-none');
        responseText.innerHTML = 'Thinking...';
        queryBtn.disabled = true;
        
        // Send query with domain context
        const response = await apiRequest('/chat', 'POST', { 
            query: `About ${domainName}: ${query}` 
        });
        
        // Display response
        responseText.innerHTML = response.response;
        
    } catch (error) {
        console.error('Domain query error:', error);
        responseText.innerHTML = 'Sorry, I encountered an error while processing your request.';
    } finally {
        queryBtn.disabled = false;
    }
}