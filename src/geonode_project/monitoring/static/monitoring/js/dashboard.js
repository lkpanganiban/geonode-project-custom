/**
 * Celery Monitoring Dashboard JavaScript
 */

(function() {
    'use strict';
    
    var autoRefreshInterval = null;
    var refreshTime = 60000; // 60 seconds
    var isPaused = false;
    
    // Initialize dashboard when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        // Initialize tooltips if Bootstrap is available
        if (typeof $ !== 'undefined' && $.fn.tooltip) {
            $('[data-toggle="tooltip"]').tooltip();
        }
        
        // Start auto-refresh
        startAutoRefresh();
        
        console.log('Celery Monitoring Dashboard initialized');
    });
    
    /**
     * Start auto-refresh timer
     */
    function startAutoRefresh() {
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
        }
        if (!isPaused) {
            autoRefreshInterval = setInterval(refreshData, refreshTime);
        }
    }
    
    /**
     * Toggle auto-refresh on/off
     */
    window.toggleAutoRefresh = function() {
        isPaused = !isPaused;
        var icon = document.getElementById('autorefresh-icon');
        var text = document.getElementById('autorefresh-text');
        
        if (isPaused) {
            clearInterval(autoRefreshInterval);
            if (icon) {
                icon.classList.remove('fa-pause');
                icon.classList.add('fa-play');
            }
            if (text) {
                text.textContent = 'Resume Auto-refresh';
            }
            console.log('Auto-refresh paused');
        } else {
            startAutoRefresh();
            if (icon) {
                icon.classList.remove('fa-play');
                icon.classList.add('fa-pause');
            }
            if (text) {
                text.textContent = 'Pause Auto-refresh';
            }
            console.log('Auto-refresh resumed');
        }
    };
    
    /**
     * Refresh dashboard data via AJAX
     */
    window.refreshData = function() {
        console.log('Refreshing dashboard data...');
        
        // Fetch updated worker stats
        fetch(MONITORING_CONFIG.refreshUrl, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': MONITORING_CONFIG.csrfToken
            }
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(function(data) {
            updateDashboard(data);
            console.log('Dashboard data refreshed');
        })
        .catch(function(error) {
            console.error('Error refreshing data:', error);
        });
        
        // Also refresh task history to update statuses
        if (MONITORING_CONFIG.historyUrl) {
            refreshTaskHistory();
        }
    };
    
    /**
     * Update dashboard with new data
     */
    function updateDashboard(data) {
        // Update stat cards
        var workerCount = document.getElementById('worker-count');
        var activeCount = document.getElementById('active-count');
        var scheduledCount = document.getElementById('scheduled-count');
        var reservedCount = document.getElementById('reserved-count');
        
        if (workerCount) {
            workerCount.textContent = data.worker_count || 0;
        }
        if (activeCount) {
            activeCount.textContent = data.active_count || 0;
        }
        if (scheduledCount) {
            scheduledCount.textContent = data.scheduled || 0;
        }
        if (reservedCount) {
            reservedCount.textContent = data.reserved || 0;
        }
        
        // Update workers table
        updateWorkersTable(data.workers || []);
        
        // Update active tasks table
        updateActiveTasksTable(data.workers || []);
    }
    
    /**
     * Update workers table
     */
    function updateWorkersTable(workers) {
        var tbody = document.getElementById('workers-tbody');
        if (!tbody) return;
        
        if (workers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted"><i class="fa fa-exclamation-circle"></i> No workers connected. Make sure Celery workers are running.</td></tr>';
            return;
        }
        
        var html = '';
        workers.forEach(function(worker) {
            var processed = (worker.stats && worker.stats.total && worker.stats.total.tasks) ? worker.stats.total.tasks : 0;
            var activeCount = (worker.active_tasks) ? worker.active_tasks.length : 0;
            var poolSize = (worker.stats && worker.stats.pool && worker.stats.pool['max-concurrency']) ? worker.stats.pool['max-concurrency'] : 'N/A';
            
            html += '<tr>';
            html += '<td><strong>' + escapeHtml(worker.name) + '</strong></td>';
            html += '<td><span class="badge badge-success">Online</span></td>';
            html += '<td>' + processed + '</td>';
            html += '<td>' + activeCount + '</td>';
            html += '<td>' + poolSize + '</td>';
            html += '<td><button class="btn btn-xs btn-info" onclick="showWorkerDetails(\'' + escapeHtml(worker.name) + '\')"><i class="fa fa-info-circle"></i> Details</button></td>';
            html += '</tr>';
        });
        
        tbody.innerHTML = html;
    }
    
    /**
     * Update active tasks table
     */
    function updateActiveTasksTable(workers) {
        var tbody = document.getElementById('active-tasks-tbody');
        if (!tbody) return;
        
        var hasActiveTasks = false;
        var html = '';
        
        workers.forEach(function(worker) {
            if (worker.active_tasks && worker.active_tasks.length > 0) {
                hasActiveTasks = true;
                worker.active_tasks.forEach(function(task) {
                    var taskId = (task.id) ? task.id.substring(0, 12) : 'N/A';
                    var args = task.args ? escapeHtml(JSON.stringify(task.args)).substring(0, 50) : '[]';
                    
                    html += '<tr>';
                    html += '<td><code>' + escapeHtml(taskId) + '</code></td>';
                    html += '<td>' + escapeHtml(task.name) + '</td>';
                    html += '<td>' + escapeHtml(worker.name) + '</td>';
                    html += '<td>' + args + '</td>';
                    html += '<td><button class="btn btn-xs btn-danger" onclick="revokeTask(\'' + escapeHtml(task.id) + '\', true)"><i class="fa fa-stop"></i> Terminate</button></td>';
                    html += '</tr>';
                });
            }
        });
        
        if (!hasActiveTasks) {
            html = '<tr><td colspan="5" class="text-center text-muted"><i class="fa fa-check-circle"></i> No active tasks</td></tr>';
        }
        
        tbody.innerHTML = html;
    }
    
    /**
     * Purge a queue
     */
    window.purgeQueue = function() {
        var queueSelect = document.getElementById('purge-queue-select');
        var queueName = queueSelect ? queueSelect.value : 'celery';
        
        if (!confirm('Are you sure you want to purge all messages from queue "' + queueName + '"? This cannot be undone.')) {
            return;
        }
        
        console.log('Purging queue:', queueName);
        
        fetch(MONITORING_CONFIG.purgeUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': MONITORING_CONFIG.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ queue_name: queueName })
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                alert('Queue purged successfully');
                refreshData();
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(function(error) {
            console.error('Error purging queue:', error);
            alert('Error purging queue: ' + error);
        });
    };
    
    /**
     * Set rate limit for a task
     */
    window.setRateLimit = function() {
        var taskNameInput = document.getElementById('rate-task-name');
        var rateInput = document.getElementById('rate-limit-value');
        
        var taskName = taskNameInput ? taskNameInput.value : '';
        var rate = rateInput ? rateInput.value : '';
        
        if (!taskName || !rate) {
            alert('Please enter both task name and rate limit');
            return;
        }
        
        console.log('Setting rate limit for', taskName, 'to', rate);
        
        fetch(MONITORING_CONFIG.rateLimitUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': MONITORING_CONFIG.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ task_name: taskName, rate: rate })
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                alert('Rate limit set successfully');
                if (taskNameInput) taskNameInput.value = '';
                if (rateInput) rateInput.value = '';
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(function(error) {
            console.error('Error setting rate limit:', error);
            alert('Error setting rate limit: ' + error);
        });
    };
    
    /**
     * Show worker details in modal
     */
    window.showWorkerDetails = function(workerName) {
        var modalBody = document.getElementById('worker-modal-body');
        if (!modalBody) return;
        
        // Find worker data
        var workers = [];
        var workersTbody = document.getElementById('workers-tbody');
        if (workersTbody) {
            // Get worker data from the table or fetch fresh
        }
        
        modalBody.innerHTML = '<div class="text-center"><i class="fa fa-spinner fa-spin"></i> Loading details for ' + escapeHtml(workerName) + '...</div>';
        
        // Show modal using jQuery if available
        if (typeof $ !== 'undefined') {
            $('#workerModal').modal('show');
        }
        
        // Simulate loading worker details
        setTimeout(function() {
            var html = '<div class="worker-details">';
            html += '<h5>Worker: ' + escapeHtml(workerName) + '</h5>';
            html += '<p><strong>Status:</strong> <span class="badge badge-success">Online</span></p>';
            html += '<p><strong>Details loaded from monitoring system.</strong></p>';
            html += '<p>Use the refresh button to get the latest information.</p>';
            html += '</div>';
            modalBody.innerHTML = html;
        }, 500);
    };
    
    /**
     * Retry a task
     */
    window.retryTask = function(taskName, args, kwargs) {
        console.log('Retrying task:', taskName);
        
        fetch(MONITORING_CONFIG.retryUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': MONITORING_CONFIG.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                task_name: taskName,
                args: args || [],
                kwargs: kwargs || {}
            })
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                alert('Task queued for retry. New task ID: ' + data.task_id);
                refreshData();
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(function(error) {
            console.error('Error retrying task:', error);
            alert('Error retrying task: ' + error);
        });
    };
    
    /**
     * Revoke a running task
     */
    window.revokeTask = function(taskId, terminate) {
        if (!confirm('Are you sure you want to revoke this task?')) {
            return;
        }
        
        console.log('Revoking task:', taskId, 'terminate:', terminate);
        
        fetch(MONITORING_CONFIG.revokeUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': MONITORING_CONFIG.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                task_id: taskId,
                terminate: terminate || false
            })
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                alert('Task revoked successfully');
                refreshData();
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(function(error) {
            console.error('Error revoking task:', error);
            alert('Error revoking task: ' + error);
        });
    };
    
    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        if (text === null || text === undefined) {
            return '';
        }
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Toggle custom task input based on dropdown selection
     */
    window.toggleTaskInputs = function() {
        var select = document.getElementById('trigger-task-select');
        var customInput = document.getElementById('trigger-task-custom');
        
        if (select && customInput) {
            if (select.value === 'custom') {
                customInput.disabled = false;
                customInput.focus();
            } else {
                customInput.disabled = true;
                customInput.value = '';
            }
        }
    };
    
    /**
     * Manually trigger a Celery task
     */
    window.triggerTask = function() {
        var select = document.getElementById('trigger-task-select');
        var customInput = document.getElementById('trigger-task-custom');
        var argsInput = document.getElementById('trigger-task-args');
        var resultDiv = document.getElementById('trigger-task-result');
        
        // Get task name
        var taskName = '';
        if (select) {
            if (select.value === 'custom') {
                taskName = customInput ? customInput.value.trim() : '';
            } else {
                taskName = select.value;
            }
        }
        
        if (!taskName) {
            showTriggerResult('error', 'Please select or enter a task name');
            return;
        }
        
        // Parse arguments
        var args = [];
        if (argsInput && argsInput.value.trim()) {
            try {
                args = JSON.parse(argsInput.value.trim());
                if (!Array.isArray(args)) {
                    showTriggerResult('error', 'Arguments must be a JSON array (e.g., ["arg1", 123])');
                    return;
                }
            } catch (e) {
                showTriggerResult('error', 'Invalid JSON arguments: ' + e.message);
                return;
            }
        }
        
        console.log('Triggering task:', taskName, 'with args:', args);
        
        // Show loading state
        showTriggerResult('info', 'Triggering task...');
        
        fetch(MONITORING_CONFIG.triggerUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': MONITORING_CONFIG.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                task_name: taskName,
                args: args,
                kwargs: {}
            })
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                showTriggerResult('success', 'Task triggered successfully! Task ID: ' + data.task_id);
                // Clear inputs after success
                if (select) select.value = '';
                if (customInput) customInput.value = '';
                if (argsInput) argsInput.value = '';
                if (customInput) customInput.disabled = true;
                // Refresh dashboard data
                refreshData();
            } else {
                showTriggerResult('error', 'Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(function(error) {
            console.error('Error triggering task:', error);
            showTriggerResult('error', 'Error triggering task: ' + error);
        });
    };
    
    /**
     * Show trigger task result message
     */
    function showTriggerResult(type, message) {
        var resultDiv = document.getElementById('trigger-task-result');
        if (!resultDiv) return;
        
        resultDiv.style.display = 'block';
        resultDiv.className = 'alert';
        
        if (type === 'success') {
            resultDiv.classList.add('alert-success');
        } else if (type === 'error') {
            resultDiv.classList.add('alert-danger');
        } else if (type === 'info') {
            resultDiv.classList.add('alert-info');
        }
        
        resultDiv.innerHTML = '<i class="fa fa-' + (type === 'success' ? 'check' : type === 'error' ? 'exclamation-circle' : 'info-circle') + '"></i> ' + escapeHtml(message);
        
        // Auto-hide success messages after 5 seconds
        if (type === 'success') {
            setTimeout(function() {
                resultDiv.style.display = 'none';
            }, 5000);
        }
    }
    
    /**
     * Refresh task history table
     */
    window.refreshTaskHistory = function() {
        console.log('Refreshing task history...');
        
        fetch(MONITORING_CONFIG.historyUrl, {
            method: 'GET',
            headers: {
                'X-CSRFToken': MONITORING_CONFIG.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                updateTaskHistoryTable(data.history);
                console.log('Task history refreshed, ' + data.history.length + ' items');
            } else {
                console.error('Error fetching history:', data.error);
            }
        })
        .catch(function(error) {
            console.error('Error refreshing history:', error);
        });
    };
    
    /**
     * Update task history table
     */
    function updateTaskHistoryTable(history) {
        var tbody = document.getElementById('task-history-tbody');
        var countBadge = document.getElementById('history-count');
        if (!tbody) return;
        
        // Update count badge
        if (countBadge) {
            countBadge.textContent = history.length;
        }
        
        if (history.length === 0) {
            tbody.innerHTML = '<tr id="history-empty-row"><td colspan="8" class="text-center text-muted"><i class="fa fa-info-circle"></i> No tasks triggered yet. Use the "Trigger Task Manually" form above to run tasks.</td></tr>';
            return;
        }
        
        var html = '';
        history.forEach(function(item) {
            var badgeClass = 'info';
            if (item.status === 'SUCCESS') badgeClass = 'success';
            else if (item.status === 'FAILURE') badgeClass = 'danger';
            else if (item.status === 'PENDING') badgeClass = 'warning';
            else if (item.status === 'REVOKED') badgeClass = 'secondary';
            
            var taskIdShort = item.task_id ? item.task_id.substring(0, 12) : 'N/A';
            var args = item.args ? escapeHtml(JSON.stringify(item.args)).substring(0, 30) : '[]';
            var result = item.result ? escapeHtml(item.result).substring(0, 50) : '-';
            var triggeredBy = escapeHtml(item.triggered_by || 'Unknown');
            var triggeredAt = item.triggered_at ? new Date(item.triggered_at).toLocaleString() : '-';
            
            html += '<tr id="history-row-' + escapeHtml(item.task_id) + '">';
            html += '<td><code>' + escapeHtml(taskIdShort) + '</code></td>';
            html += '<td>' + escapeHtml(item.task_name) + '</td>';
            html += '<td>' + args + '</td>';
            html += '<td>' + triggeredBy + '</td>';
            html += '<td>' + triggeredAt + '</td>';
            html += '<td><span class="badge badge-' + badgeClass + '">' + item.status + '</span></td>';
            html += '<td>' + result + '</td>';
            html += '<td><button class="btn btn-xs btn-danger" onclick="deleteTaskHistory(\'' + escapeHtml(item.task_id) + '\')" title="Delete"><i class="fa fa-trash"></i></button></td>';
            html += '</tr>';
        });
        
        tbody.innerHTML = html;
    }
    
    /**
     * Delete a specific task from history
     */
    window.deleteTaskHistory = function(taskId) {
        if (!confirm('Are you sure you want to delete this task from history?')) {
            return;
        }
        
        console.log('Deleting task:', taskId);
        
        fetch(MONITORING_CONFIG.deleteTaskUrl.replace('TASK_ID', taskId), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': MONITORING_CONFIG.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                console.log('Task deleted:', data.message);
                refreshTaskHistory();
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(function(error) {
            console.error('Error deleting task:', error);
            alert('Error deleting task: ' + error);
        });
    };
    
    /**
     * Clear all task history
     */
    window.clearAllHistory = function() {
        if (!confirm('Are you sure you want to delete ALL tasks from history? This cannot be undone.')) {
            return;
        }
        
        console.log('Clearing all history...');
        
        fetch(MONITORING_CONFIG.clearHistoryUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': MONITORING_CONFIG.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                console.log('History cleared:', data.message);
                refreshTaskHistory();
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(function(error) {
            console.error('Error clearing history:', error);
            alert('Error clearing history: ' + error);
        });
    };
    
    /**
     * Cleanup completed tasks from history
     */
    window.cleanupCompletedTasks = function() {
        if (!confirm('Are you sure you want to clear all completed tasks (SUCCESS, FAILURE, REVOKED)?')) {
            return;
        }
        
        console.log('Cleaning up completed tasks...');
        
        fetch(MONITORING_CONFIG.cleanupCompletedUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': MONITORING_CONFIG.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                console.log('Completed tasks cleaned up:', data.message);
                refreshTaskHistory();
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(function(error) {
            console.error('Error cleaning up tasks:', error);
            alert('Error cleaning up tasks: ' + error);
        });
    };
    
    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        if (text === null || text === undefined) {
            return '';
        }
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Toggle custom task input based on dropdown selection
     */
    window.toggleTaskInputs = function() {
        var select = document.getElementById('trigger-task-select');
        var customInput = document.getElementById('trigger-task-custom');
        
        if (select && customInput) {
            if (select.value === 'custom') {
                customInput.disabled = false;
                customInput.focus();
            } else {
                customInput.disabled = true;
                customInput.value = '';
            }
        }
    };
    
    /**
     * Manually trigger a Celery task
     */
    window.triggerTask = function() {
        var select = document.getElementById('trigger-task-select');
        var customInput = document.getElementById('trigger-task-custom');
        var argsInput = document.getElementById('trigger-task-args');
        var resultDiv = document.getElementById('trigger-task-result');
        
        // Get task name
        var taskName = '';
        if (select) {
            if (select.value === 'custom') {
                taskName = customInput ? customInput.value.trim() : '';
            } else {
                taskName = select.value;
            }
        }
        
        if (!taskName) {
            showTriggerResult('error', 'Please select or enter a task name');
            return;
        }
        
        // Parse arguments
        var args = [];
        if (argsInput && argsInput.value.trim()) {
            try {
                args = JSON.parse(argsInput.value.trim());
                if (!Array.isArray(args)) {
                    showTriggerResult('error', 'Arguments must be a JSON array (e.g., ["arg1", 123])');
                    return;
                }
            } catch (e) {
                showTriggerResult('error', 'Invalid JSON arguments: ' + e.message);
                return;
            }
        }
        
        console.log('Triggering task:', taskName, 'with args:', args);
        
        // Show loading state
        showTriggerResult('info', 'Triggering task...');
        
        fetch(MONITORING_CONFIG.triggerUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': MONITORING_CONFIG.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                task_name: taskName,
                args: args,
                kwargs: {}
            })
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                showTriggerResult('success', 'Task triggered successfully! Task ID: ' + data.task_id);
                // Clear inputs after success
                if (select) select.value = '';
                if (customInput) customInput.value = '';
                if (argsInput) argsInput.value = '';
                if (customInput) customInput.disabled = true;
                // Refresh dashboard data and history
                refreshData();
                refreshTaskHistory();
            } else {
                showTriggerResult('error', 'Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(function(error) {
            console.error('Error triggering task:', error);
            showTriggerResult('error', 'Error triggering task: ' + error);
        });
    };
    
})();
