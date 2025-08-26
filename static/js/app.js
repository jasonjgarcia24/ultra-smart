// Ultra Smart Analytics - JavaScript functionality

// Global variables
let selectedAthletes = new Set();
let loadingStates = new Map();

// Utility functions
function formatTime(hours) {
    const h = Math.floor(hours);
    const m = Math.floor((hours - h) * 60);
    return `${h}h ${m}m`;
}

function formatPace(minutes) {
    const m = Math.floor(minutes);
    const s = Math.floor((minutes - m) * 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

// Loading state management
function setLoadingState(elementId, isLoading) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    loadingStates.set(elementId, isLoading);
    
    if (isLoading) {
        element.innerHTML = `
            <div class="d-flex justify-content-center align-items-center" style="height: 80px;">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
    }
}

// API calls with error handling
async function fetchWithRetry(url, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            if (i === maxRetries - 1) throw error;
            await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)));
        }
    }
}

// Load athlete statistics
async function loadAthleteStats(athleteId) {
    const containerElement = `stats-${athleteId}`;
    setLoadingState(containerElement, true);
    
    try {
        const data = await fetchWithRetry(`/api/athlete/${athleteId}/stats`);
        
        const container = document.getElementById(containerElement);
        if (!container) return;
        
        if (data.error) {
            container.innerHTML = `
                <div class="alert alert-danger alert-sm mb-0">
                    <i class="fas fa-exclamation-triangle"></i> Error loading stats
                </div>
            `;
            return;
        }
        
        // Create animated stats display
        container.innerHTML = `
            <div class="row g-2 fade-in">
                <div class="col-6">
                    <div class="stat-mini">
                        <small class="text-muted d-block">Total Miles</small>
                        <div class="fw-bold text-primary">${data.total_miles}</div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="stat-mini">
                        <small class="text-muted d-block">Avg Pace</small>
                        <div class="fw-bold text-success">${formatPace(data.average_pace_minutes)}/mi</div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="stat-mini">
                        <small class="text-muted d-block">Sub-15 Miles</small>
                        <div class="fw-bold text-warning">${data.sub_15_miles} <span class="small">(${data.sub_15_percent.toFixed(1)}%)</span></div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="stat-mini">
                        <small class="text-muted d-block">Total Time</small>
                        <div class="fw-bold text-info">${formatTime(data.total_time_hours)}</div>
                    </div>
                </div>
            </div>
        `;
        
        // Add hover effects
        container.querySelectorAll('.stat-mini').forEach(stat => {
            stat.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.05)';
                this.style.transition = 'transform 0.2s ease';
            });
            
            stat.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1)';
            });
        });
        
    } catch (error) {
        console.error('Error loading athlete stats:', error);
        const container = document.getElementById(containerElement);
        if (container) {
            container.innerHTML = `
                <div class="alert alert-danger alert-sm mb-0">
                    <i class="fas fa-exclamation-triangle"></i> 
                    Failed to load stats
                    <button class="btn btn-sm btn-outline-danger ms-2" onclick="loadAthleteStats('${athleteId}')">
                        <i class="fas fa-redo"></i> Retry
                    </button>
                </div>
            `;
        }
    }
}

// Quick comparison functionality
function addToComparison(athleteId, athleteName) {
    if (selectedAthletes.size >= 5) {
        showNotification('Maximum 5 athletes can be compared at once', 'warning');
        return;
    }
    
    selectedAthletes.add({id: athleteId, name: athleteName});
    updateComparisonPanel();
    
    // Visual feedback
    showNotification(`Added ${athleteName} to comparison`, 'success');
    
    // Animate the button
    const button = event.target.closest('button');
    if (button) {
        button.classList.add('btn-success');
        button.classList.remove('btn-outline-success');
        button.innerHTML = '<i class="fas fa-check"></i> Added';
        
        setTimeout(() => {
            button.classList.remove('btn-success');
            button.classList.add('btn-outline-success');
            button.innerHTML = '<i class="fas fa-plus"></i> Add to Comparison';
        }, 2000);
    }
}

function removeFromComparison(athleteId) {
    selectedAthletes = new Set([...selectedAthletes].filter(a => a.id !== athleteId));
    updateComparisonPanel();
    showNotification('Athlete removed from comparison', 'info');
}

function clearComparison() {
    selectedAthletes.clear();
    updateComparisonPanel();
    showNotification('Comparison cleared', 'info');
}

function updateComparisonPanel() {
    const panel = document.getElementById('comparison-panel');
    const container = document.getElementById('selected-athletes');
    const compareBtn = document.getElementById('compare-btn');
    
    if (!panel) return;
    
    if (selectedAthletes.size === 0) {
        panel.style.display = 'none';
        return;
    }
    
    panel.style.display = 'block';
    panel.classList.add('slide-up');
    
    if (container) {
        container.innerHTML = [...selectedAthletes].map((athlete, index) => `
            <span class="badge bg-primary me-2 mb-2 fade-in" style="animation-delay: ${index * 0.1}s">
                <i class="fas fa-user"></i> ${athlete.name}
                <button class="btn-close btn-close-white ms-2" 
                        onclick="removeFromComparison('${athlete.id}')" 
                        style="font-size: 0.7em;" 
                        title="Remove ${athlete.name}"></button>
            </span>
        `).join('');
    }
    
    if (compareBtn) {
        compareBtn.disabled = selectedAthletes.size < 2;
        compareBtn.innerHTML = `
            <i class="fas fa-chart-line"></i> 
            Compare Selected Athletes (${selectedAthletes.size})
        `;
    }
}

function runComparison() {
    if (selectedAthletes.size < 2) {
        showNotification('Please select at least 2 athletes to compare', 'warning');
        return;
    }
    
    const athleteIds = [...selectedAthletes].map(a => a.id);
    const params = athleteIds.map(id => `athletes=${id}`).join('&');
    
    // Show loading state
    const button = document.getElementById('compare-btn');
    if (button) {
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading comparison...';
    }
    
    window.location.href = `/compare?${params}`;
}

// Notification system
function showNotification(message, type = 'info', duration = 3000) {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification-toast');
    existingNotifications.forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} notification-toast position-fixed top-0 end-0 m-3`;
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    notification.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <i class="fas fa-info-circle"></i> ${message}
            </div>
            <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }
    }, duration);
}

// Enhanced form validation
function validateComparisonForm(form) {
    const checkboxes = form.querySelectorAll('input[name="athletes"]:checked');
    
    if (checkboxes.length < 2) {
        showNotification('Please select at least 2 athletes to compare', 'warning');
        return false;
    }
    
    if (checkboxes.length > 5) {
        showNotification('Please select no more than 5 athletes to compare', 'warning');
        return false;
    }
    
    return true;
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K for quick search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('input[type="search"], input[placeholder*="search"]');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Escape to clear comparison
    if (e.key === 'Escape') {
        clearComparison();
    }
});

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Add loading states to all stat containers
    document.querySelectorAll('[id^="stats-"]').forEach(element => {
        element.classList.add('stat-container');
    });
});

// Enhanced table sorting
function sortTable(table, column, direction = 'asc') {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    const sortedRows = rows.sort((a, b) => {
        const aValue = a.children[column].textContent.trim();
        const bValue = b.children[column].textContent.trim();
        
        // Try to parse as numbers first
        const aNum = parseFloat(aValue.replace(/[^\d.-]/g, ''));
        const bNum = parseFloat(bValue.replace(/[^\d.-]/g, ''));
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return direction === 'asc' ? aNum - bNum : bNum - aNum;
        } else {
            return direction === 'asc' ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
        }
    });
    
    // Clear and re-add rows
    tbody.innerHTML = '';
    sortedRows.forEach(row => tbody.appendChild(row));
}

// Export data functionality
function exportComparisonData() {
    const data = {
        timestamp: new Date().toISOString(),
        athletes: [...selectedAthletes],
        // Add more data as needed
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `athlete-comparison-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Add CSS for stat-mini elements
const style = document.createElement('style');
style.textContent = `
    .stat-mini {
        padding: 8px;
        border-radius: 4px;
        background-color: rgba(0, 123, 255, 0.05);
        text-align: center;
        cursor: pointer;
    }
    
    .stat-mini:hover {
        background-color: rgba(0, 123, 255, 0.1);
    }
    
    .notification-toast {
        animation: slideInRight 0.3s ease;
        transition: opacity 0.3s ease, transform 0.3s ease;
    }
    
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100%);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
`;
document.head.appendChild(style);