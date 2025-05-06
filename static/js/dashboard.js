// JavaScript logic
/**
 * Dashboard page functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Load dashboard data
    loadDashboardData();
    
    // Set up refresh button
    const refreshBtn = document.getElementById('refreshDashboardBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadDashboardData);
    }
    
    // Set up quick chat
    const quickChatInput = document.getElementById('quickChatInput');
    if (quickChatInput) {
        quickChatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const query = quickChatInput.value.trim();
                if (query) {
                    handleQuickChat(query);
                }
            }
        });
    }
});

async function loadDashboardData() {
    try {
        // Show loading states
        document.getElementById('activity-summary').innerHTML = '<p class="text-center text-muted">Loading summary...</p>';
        document.getElementById('recent-activity').innerHTML = '<p class="text-center text-muted">Loading recent activity...</p>';
        
        // Load summary (without generating with LLM initially)
        const summaryData = await apiRequest('/summary');
        renderSummary(summaryData);
        
        // Add a "Generate AI Summary" button
        const summaryContainer = document.getElementById('activity-summary');
        const generateButton = document.createElement('button');
        generateButton.className = 'btn btn-sm btn-outline-primary mt-3';
        generateButton.textContent = 'Generate AI Summary';
        generateButton.addEventListener('click', generateAISummary);
        summaryContainer.appendChild(generateButton);
        
        // Load statistics
        const statsData = await apiRequest('/stats');
        renderCharts(statsData);
        
        // Load recent activity
        const recentData = await apiRequest('/recent');
        renderRecentActivity(recentData.items);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

async function generateAISummary() {
    try {
        const summaryContainer = document.getElementById('activity-summary');
        
        // Show loading state
        summaryContainer.innerHTML = '<p class="text-center text-muted">Generating AI summary...</p>';
        
        // Request AI-generated summary
        const summaryData = await apiRequest('/summary?generate=true');
        
        // Render summary
        renderSummary(summaryData);
        
    } catch (error) {
        console.error('Error generating AI summary:', error);
        document.getElementById('activity-summary').innerHTML = 
            '<p class="text-danger">Error generating AI summary. Please try again later.</p>';
    }
}

function renderSummary(data) {
    const summaryContainer = document.getElementById('activity-summary');
    
    if (data.summary) {
        summaryContainer.innerHTML = `<p>${data.summary}</p>`;
    } else {
        summaryContainer.innerHTML = '<p class="text-center text-muted">No summary available</p>';
    }
}

function renderCharts(data) {
    // Domains chart
    const domainsCtx = document.getElementById('domainsChart').getContext('2d');
    const domainsData = data.domains.slice(0, 5); // Top 5 domains
    
    new Chart(domainsCtx, {
        type: 'bar',
        data: {
            labels: domainsData.map(d => d.domain),
            datasets: [{
                label: 'Pages Visited',
                data: domainsData.map(d => d.count),
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
    
    // Hourly chart
    const hourlyCtx = document.getElementById('hourlyChart').getContext('2d');
    
    new Chart(hourlyCtx, {
        type: 'line',
        data: {
            labels: data.hourly.map(h => `${h.hour}:00`),
            datasets: [{
                label: 'Activity',
                data: data.hourly.map(h => h.count),
                fill: false,
                borderColor: 'rgba(54, 162, 235, 1)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

function renderRecentActivity(items) {
    const container = document.getElementById('recent-activity');
    
    if (!items || items.length === 0) {
        container.innerHTML = '<p class="text-center text-muted">No recent activity found</p>';
        return;
    }
    
    let html = '<div class="table-responsive"><table class="table table-hover">';
    html += `
        <thead>
            <tr>
                <th>Page</th>
                <th>Domain</th>
                <th>Last Visit</th>
            </tr>
        </thead>
        <tbody>
    `;
    
    items.forEach(item => {
        html += `
            <tr>
                <td>
                    <a href="${item.url}" target="_blank" title="${item.url}">
                        ${item.title || 'Untitled'}
                    </a>
                </td>
                <td>${item.domain || extractDomain(item.url)}</td>
                <td>${formatDate(item.last_visit_time)}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

async function handleQuickChat(query) {
    const responseContainer = document.getElementById('quick-chat-response');
    const responseText = document.getElementById('quick-chat-text');
    const sourcesContainer = document.getElementById('quick-chat-sources');
    
    try {
        // Show response container and loading state
        responseContainer.classList.remove('d-none');
        responseText.innerHTML = 'Thinking...';
        sourcesContainer.innerHTML = '';
        
        // Send chat request
        const response = await apiRequest('/chat', 'POST', { query });
        
        // Display response
        responseText.innerHTML = response.response;
        
        // Display sources if available
        if (response.sources && response.sources.length > 0) {
            let sourcesHtml = '<p><strong>Sources:</strong></p><ul>';
            response.sources.forEach(source => {
                sourcesHtml += `<li><a href="${source}" target="_blank">${source}</a></li>`;
            });
            sourcesHtml += '</ul>';
            sourcesContainer.innerHTML = sourcesHtml;
        }
        
    } catch (error) {
        responseText.innerHTML = 'Sorry, I encountered an error while processing your request.';
        console.error('Chat error:', error);
    }
}