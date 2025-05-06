// static/js/calendar.js
document.addEventListener('DOMContentLoaded', function() {
    // Global variables
    let currentView = 'dayGridMonth';
    let selectedDate = null;
    let selectedStartDate = null;
    let selectedEndDate = null;
    let calendarData = [];
    
    // Initialize FullCalendar
    const calendarEl = document.getElementById('calendar');
    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: currentView,
        headerToolbar: false, // We have custom buttons above the calendar
        height: 'auto',
        firstDay: 1, // Start week on Monday
        selectable: true,
        unselectAuto: false,
        select: function(info) {
            selectedDate = info.startStr;
            selectedStartDate = info.startStr;
            selectedEndDate = info.endStr;
            
            // Update UI to show selected date
            updateSelectedDates(selectedStartDate, selectedEndDate);
            
            // Load activity for selected date or period
            if (currentView === 'dayGridMonth') {
                loadDateActivity(selectedDate);
            } else {
                loadPeriodActivity(selectedStartDate, selectedEndDate);
            }
        },
        dayRender: function(info) {
            // Custom styling for days based on activity level
            const dateStr = info.date.toISOString().split('T')[0];
            const dateData = calendarData.find(d => d.date === dateStr);
            
            if (dateData) {
                const visitCount = dateData.visit_count;
                
                // Add intensity classes based on visit count
                if (visitCount > 50) {
                    info.el.classList.add('high-activity');
                } else if (visitCount > 20) {
                    info.el.classList.add('medium-activity');
                } else if (visitCount > 0) {
                    info.el.classList.add('low-activity');
                }
            }
        },
        eventDidMount: function(info) {
            // Customizing event tooltips
            if (info.event.extendedProps.description) {
                const tooltip = document.createElement('div');
                tooltip.classList.add('calendar-tooltip');
                tooltip.innerHTML = info.event.extendedProps.description;
                
                const closeBtn = document.createElement('span');
                closeBtn.classList.add('tooltip-close');
                closeBtn.innerHTML = '&times;';
                closeBtn.onclick = function() {
                    tooltip.remove();
                };
                
                tooltip.appendChild(closeBtn);
                info.el.appendChild(tooltip);
            }
        }
    });
    
    // Render the calendar
    calendar.render();
    
    // Load initial calendar data
    loadCalendarData();
    
    // Button handlers
    document.getElementById('btn-prev-month').addEventListener('click', function() {
        calendar.prev();
        updateDateRange();
    });
    
    document.getElementById('btn-next-month').addEventListener('click', function() {
        calendar.next();
        updateDateRange();
    });
    
    document.getElementById('btn-today').addEventListener('click', function() {
        calendar.today();
        updateDateRange();
    });
    
    document.getElementById('btn-day').addEventListener('click', function() {
        toggleViewButton('btn-day');
        currentView = 'timeGridDay';
        calendar.changeView(currentView);
        updateDateRange();
    });
    
    document.getElementById('btn-month').addEventListener('click', function() {
        toggleViewButton('btn-month');
        currentView = 'dayGridMonth';
        calendar.changeView(currentView);
        updateDateRange();
    });
    
    document.getElementById('btn-analyze').addEventListener('click', function() {
        if (selectedStartDate && selectedEndDate) {
            analyzeTimePeriod(selectedStartDate, selectedEndDate);
        } else {
            showNotification('Please select a date or period first', 'warning');
        }
    });
    
    document.getElementById('btn-send-chat').addEventListener('click', function() {
        sendChatMessage();
    });
    
    document.getElementById('chat-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendChatMessage();
        }
    });
    
    // Helper functions
    function updateDateRange() {
        const viewTitle = calendar.view.title;
        document.getElementById('calendar-date-range').textContent = viewTitle;
    }
    
    function toggleViewButton(activeId) {
        document.getElementById('btn-day').classList.remove('active');
        document.getElementById('btn-month').classList.remove('active');
        document.getElementById(activeId).classList.add('active');
    }
    
    function updateSelectedDates(startDate, endDate) {
        let title = '';
        
        if (startDate === endDate || !endDate) {
            title = formatDate(startDate);
        } else {
            // Calculate the day before endDate (FullCalendar end dates are exclusive)
            const end = new Date(endDate);
            end.setDate(end.getDate() - 1);
            const formattedEnd = end.toISOString().split('T')[0];
            
            if (startDate === formattedEnd) {
                title = formatDate(startDate);
            } else {
                title = `${formatDate(startDate)} to ${formatDate(formattedEnd)}`;
            }
        }
        
        document.getElementById('activity-title').textContent = title;
    }
    
    function formatDate(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { 
            weekday: 'short', 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        });
    }
    
    function showNotification(message, type = 'info') {
        // Simple notification system
        const notificationEl = document.createElement('div');
        notificationEl.className = `alert alert-${type} alert-dismissible fade show`;
        notificationEl.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Find notification container or create one
        let container = document.querySelector('.notification-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'notification-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(container);
        }
        
        container.appendChild(notificationEl);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            notificationEl.remove();
        }, 5000);
    }
    
    // API functions
    async function loadCalendarData() {
        try {
            const response = await fetch('/api/calendar/overview');
            if (!response.ok) {
                throw new Error('Failed to load calendar data');
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                calendarData = data.calendar_data;
                
                // Create events from calendar data
                const events = calendarData.map(day => {
                    return {
                        title: `${day.visit_count} visits`,
                        start: day.date,
                        allDay: true,
                        backgroundColor: getColorForVisitCount(day.visit_count),
                        borderColor: getColorForVisitCount(day.visit_count),
                        extendedProps: {
                            description: `${day.visit_count} pages visited across ${day.domain_count} domains`
                        }
                    };
                });
                
                // Add events to calendar
                calendar.removeAllEvents();
                calendar.addEventSource(events);
                
                // Update date range
                updateDateRange();
            } else {
                console.error('Error loading calendar data:', data.message);
            }
        } catch (error) {
            console.error('Error fetching calendar data:', error);
            showNotification('Failed to load calendar data', 'danger');
        }
    }
    
    function getColorForVisitCount(count) {
        // Return color based on visit count
        if (count > 100) {
            return '#d32f2f'; // High activity - red
        } else if (count > 50) {
            return '#ff9800'; // Medium-high activity - orange
        } else if (count > 20) {
            return '#4caf50'; // Medium activity - green
        } else if (count > 10) {
            return '#2196f3'; // Low-medium activity - blue
        } else {
            return '#9e9e9e'; // Low activity - gray
        }
    }
    
    async function loadDateActivity(date) {
        // Show loading state
        document.getElementById('activity-content').innerHTML = `
            <div class="text-center my-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading activity data...</p>
            </div>
        `;
        
        try {
            const response = await fetch(`/api/calendar/date/${date}`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    document.getElementById('activity-content').innerHTML = `
                        <div class="text-center text-muted my-5">
                            <p>No browsing history found for this date</p>
                        </div>
                    `;
                    return;
                }
                throw new Error('Failed to load date activity');
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Render date activity
                let html = `
                    <div class="summary-box mb-3">
                        <p>${data.summary}</p>
                    </div>
                    
                    <h6>Top Domains</h6>
                    <div class="domain-stats mb-4">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Domain</th>
                                        <th>Visits</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;
                
                // Add domain stats
                data.domain_stats.forEach(domain => {
                    html += `
                        <tr>
                            <td>${domain.domain}</td>
                            <td>${domain.visit_count}</td>
                        </tr>
                    `;
                });
                
                html += `
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <h6>Browsing Timeline</h6>
                    <div class="visits-timeline">
                `;
                
                // Add visits timeline
                data.visits.forEach(visit => {
                    const visitTime = new Date(visit.last_visit_time).toLocaleTimeString();
                    html += `
                        <div class="visit-item mb-2">
                            <div class="visit-time text-muted">${visitTime}</div>
                            <div class="visit-title">${visit.title || 'Untitled'}</div>
                            <div class="visit-domain text-muted small">${visit.domain}</div>
                        </div>
                    `;
                });
                
                html += `
                    </div>
                `;
                
                document.getElementById('activity-content').innerHTML = html;
                
                // Clear chat messages
                document.getElementById('chat-messages').innerHTML = `
                    <div class="text-center text-muted my-3">
                        <p>Ask questions about your browsing activity on this date</p>
                    </div>
                `;
            } else {
                console.error('Error loading date activity:', data.message);
            }
        } catch (error) {
            console.error('Error fetching date activity:', error);
            showNotification('Failed to load activity data', 'danger');
        }
    }
    
    async function loadPeriodActivity(startDate, endDate) {
        // Show loading state
        document.getElementById('activity-content').innerHTML = `
            <div class="text-center my-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading period data...</p>
            </div>
        `;
        
        try {
            const response = await fetch(`/api/calendar/period?start=${startDate}&end=${endDate}`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    document.getElementById('activity-content').innerHTML = `
                        <div class="text-center text-muted my-5">
                            <p>No browsing history found for this period</p>
                        </div>
                    `;
                    return;
                }
                throw new Error('Failed to load period activity');
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Render period activity
                let html = `
                    <div class="summary-box mb-3">
                        <p>${data.summary}</p>
                    </div>
                    
                    <div class="stats-overview mb-3">
                        <div class="row text-center">
                            <div class="col-6 col-md-3 mb-2">
                                <div class="stat-card p-2">
                                    <div class="stat-value">${data.stats.total_visits}</div>
                                    <div class="stat-label small">Total Visits</div>
                                </div>
                            </div>
                            <div class="col-6 col-md-3 mb-2">
                                <div class="stat-card p-2">
                                    <div class="stat-value">${data.stats.total_domains}</div>
                                    <div class="stat-label small">Domains</div>
                                </div>
                            </div>
                            <div class="col-6 col-md-3 mb-2">
                                <div class="stat-card p-2">
                                    <div class="stat-value">${data.stats.total_days}</div>
                                    <div class="stat-label small">Days</div>
                                </div>
                            </div>
                            <div class="col-6 col-md-3 mb-2">
                                <div class="stat-card p-2">
                                    <div class="stat-value">${data.stats.avg_visits_per_day}</div>
                                    <div class="stat-label small">Avg/Day</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <h6>Top Domains</h6>
                    <div class="domain-stats mb-4">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Domain</th>
                                        <th>Visits</th>
                                        <th>Days</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;
                
                // Add domain stats
                data.domain_stats.forEach(domain => {
                    html += `
                        <tr>
                            <td>${domain.domain}</td>
                            <td>${domain.visit_count}</td>
                            <td>${domain.days_count}</td>
                        </tr>
                    `;
                });
                
                html += `
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <h6>Daily Activity</h6>
                    <div id="daily-activity-chart" style="height: 200px;"></div>
                `;
                
                document.getElementById('activity-content').innerHTML = html;
                
                // Render daily activity chart
                renderDailyActivityChart(data.daily_activity);
                
                // Clear chat messages
                document.getElementById('chat-messages').innerHTML = `
                    <div class="text-center text-muted my-3">
                        <p>Ask questions about your browsing activity during this period</p>
                    </div>
                `;
            } else {
                console.error('Error loading period activity:', data.message);
            }
        } catch (error) {
            console.error('Error fetching period activity:', error);
            showNotification('Failed to load activity data', 'danger');
        }
    }
    
    function renderDailyActivityChart(dailyData) {
        // Simple chart using div heights
        const chartElement = document.getElementById('daily-activity-chart');
        if (!chartElement) return;
        
        // Find max value for scaling
        const maxVisits = Math.max(...dailyData.map(day => day.visit_count));
        
        let html = '<div class="daily-chart d-flex align-items-end" style="height: 100%;">';
        
        dailyData.forEach(day => {
            const date = new Date(day.date);
            const formattedDate = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            const heightPercent = (day.visit_count / maxVisits) * 100;
            
            html += `
                <div class="chart-bar-container mx-1" style="flex: 1;">
                    <div class="chart-bar bg-primary" style="height: ${heightPercent}%; min-height: 4px;" 
                        title="${day.visit_count} visits on ${formattedDate}"></div>
                    <div class="chart-label small text-truncate">${formattedDate}</div>
                </div>
            `;
        });
        
        html += '</div>';
        chartElement.innerHTML = html;
    }
    
    async function analyzeTimePeriod(startDate, endDate) {
        // Show loading state
        document.getElementById('activity-content').innerHTML = `
            <div class="text-center my-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Analyzing your browsing activity...</p>
                <p class="text-muted small">This may take a moment</p>
            </div>
        `;
        
        try {
            const response = await fetch('/api/calendar/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    start_date: startDate,
                    end_date: endDate,
                    type: 'detailed'
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to analyze time period');
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Render analysis
                let html = `
                    <div class="analysis-content">
                        ${data.analysis}
                    </div>
                `;
                
                document.getElementById('activity-content').innerHTML = html;
            } else {
                console.error('Error analyzing time period:', data.message);
            }
        } catch (error) {
            console.error('Error fetching analysis:', error);
            showNotification('Failed to analyze browsing activity', 'danger');
        }
    }
    
    async function sendChatMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        
        if (!message || !selectedStartDate) return;
        
        // Clear input
        input.value = '';
        
        // Add user message to chat
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML += `
            <div class="chat-message user-message mb-2">
                <div class="message-content p-2">
                    ${message}
                </div>
            </div>
        `;
        
        // Add loading indicator
        chatMessages.innerHTML += `
            <div class="chat-message system-message mb-2" id="loading-message">
                <div class="message-content p-2">
                    <div class="d-flex align-items-center">
                        <div class="spinner-border spinner-border-sm text-primary me-2" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <span>Thinking...</span>
                    </div>
                </div>
            </div>
        `;
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        try {
            // Prepare request data
            const requestData = {
                query: message,
                start_date: selectedStartDate,
                end_date: selectedEndDate || selectedStartDate
            };
            
            // Send request
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                throw new Error('Failed to get chat response');
            }
            
            const data = await response.json();
            
            // Remove loading indicator
            document.getElementById('loading-message').remove();
            
            // Add assistant response
            if (data.status === 'success') {
                chatMessages.innerHTML += `
                    <div class="chat-message assistant-message mb-2">
                        <div class="message-content p-2">
                            ${data.response}
                        </div>
                    </div>
                `;
            } else {
                chatMessages.innerHTML += `
                    <div class="chat-message system-message mb-2">
                        <div class="message-content p-2 text-danger">
                            Error: ${data.message || 'Failed to get response'}
                        </div>
                    </div>
                `;
            }
            
            // Scroll to bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } catch (error) {
            console.error('Error sending chat message:', error);
            
            // Remove loading indicator
            document.getElementById('loading-message').remove();
            
            // Add error message
            chatMessages.innerHTML += `
                
                <div class="message-content p-2 text-danger">
                                        Error: Failed to get response. Please try again.
                                    </div>
                                </div>
                            `;
                            
                            // Scroll to bottom
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }
                    }
                    
    // Initialize on load
    updateDateRange();
});