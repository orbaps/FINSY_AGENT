// Finsy Frontend Application
// API Configuration
const API_URL = '';

// DOM Elements
const tabButtons = document.querySelectorAll('.nav-button');
const tabContents = document.querySelectorAll('.tab-content');

// Tab Navigation
tabButtons.forEach(button => {
    button.addEventListener('click', () => {
        const tabId = button.getAttribute('data-tab');
        
        // Update active button
        tabButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        
        // Show active tab
        tabContents.forEach(content => {
            content.classList.remove('active');
            if (content.id === tabId) {
                content.classList.add('active');
                // Load data for the active tab
                loadTabData(tabId);
            }
        });
    });
});

// Load data based on active tab
function loadTabData(tabId) {
    switch(tabId) {
        case 'dashboard':
            loadDashboardStats();
            break;
        case 'invoices':
            loadInvoices();
            break;
        case 'approvals':
            loadApprovals();
            break;
        case 'analytics':
            // Analytics tab - no data loading needed
            break;
    }
}

// Dashboard Functions
async function loadDashboardStats() {
    try {
        const response = await fetch(`${API_URL}/reports/summary`);
        const data = await response.json();
        
        document.getElementById('totalInvoices').textContent = data.total_invoices || 0;
        document.getElementById('pendingApprovals').textContent = data.pending_approvals || 0;
        document.getElementById('approvedCount').textContent = data.approved_approvals || 0;
        
        // Try to load total amount if endpoint exists
        try {
            const dashResponse = await fetch(`${API_URL}/dashboard/stats`);
            const dashData = await dashResponse.json();
            document.getElementById('totalAmount').textContent = 
                '$' + (dashData.total_amount ? dashData.total_amount.toLocaleString() : '0');
        } catch (e) {
            document.getElementById('totalAmount').textContent = '$0';
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

// Risk Scoring Form
document.getElementById('riskForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const resultDiv = document.getElementById('riskResult');
    resultDiv.style.display = 'block';
    resultDiv.className = 'result';
    resultDiv.innerHTML = '<div class="loading"></div> Calculating risk score...';
    
    try {
        const response = await fetch(`${API_URL}/risk/score`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                amount: parseFloat(document.getElementById('amount').value),
                vendor: document.getElementById('vendor').value,
                hasPO: document.getElementById('hasPO').value
            })
        });
        
        const data = await response.json();
        resultDiv.className = 'result success';
        resultDiv.innerHTML = `
            <h3>Risk Score Calculated!</h3>
            <p><strong>Score:</strong> ${data.score || 'N/A'}</p>
            <p><strong>Level:</strong> <span class="risk-badge risk-${data.level || 'medium'}">${data.level || 'Medium'}</span></p>
        `;
    } catch (error) {
        resultDiv.className = 'result error';
        resultDiv.innerHTML = `<strong>Error:</strong> ${error.message || 'Failed to calculate risk score'}`;
    }
});

// Invoice Submission Form
document.getElementById('invoiceForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const resultDiv = document.getElementById('invoiceResult');
    resultDiv.style.display = 'block';
    resultDiv.className = 'result';
    resultDiv.innerHTML = '<div class="loading"></div> Submitting invoice...';
    
    try {
        const response = await fetch(`${API_URL}/demo/invoices/parse`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                vendor: document.getElementById('invoiceVendor').value,
                amount: parseFloat(document.getElementById('invoiceAmount').value),
                po_number: document.getElementById('poNumber').value,
                invoice_text: document.getElementById('invoiceText').value
            })
        });
        
        const data = await response.json();
        resultDiv.className = 'result success';
        resultDiv.innerHTML = `
            <h3>Invoice Submitted Successfully!</h3>
            <p><strong>Invoice ID:</strong> ${data.invoice_id || 'N/A'}</p>
            <p><strong>Vendor:</strong> ${data.vendor || 'N/A'}</p>
            <p><strong>Amount:</strong> $${data.amount || '0'}</p>
        `;
        
        // Reset form
        e.target.reset();
        
        // Refresh dashboard stats
        loadDashboardStats();
    } catch (error) {
        resultDiv.className = 'result error';
        resultDiv.innerHTML = `<strong>Error:</strong> ${error.message || 'Failed to submit invoice'}`;
    }
});

// Invoices Tab Functions
async function loadInvoices() {
    try {
        // This would typically fetch actual invoice data
        // For now, we'll just show a placeholder
        const tableBody = document.querySelector('#invoicesTable tbody');
        tableBody.innerHTML = '<tr><td colspan="5" class="empty-state">No invoices found</td></tr>';
    } catch (error) {
        console.error('Error loading invoices:', error);
    }
}

// Approvals Tab Functions
async function loadApprovals() {
    try {
        const response = await fetch(`${API_URL}/approvals/pending`);
        const data = await response.json();
        const approvalsList = document.getElementById('approvalsList');
        
        if (data.pending_approvals && data.pending_approvals.length > 0) {
            approvalsList.innerHTML = data.pending_approvals.map(approval => `
                <div class="approval-item">
                    <h4>Invoice: ${approval.invoice_id || 'N/A'}</h4>
                    <p><strong>Reason:</strong> ${approval.reason || 'N/A'}</p>
                    <p><strong>Amount:</strong> $${approval.amount || '0'}</p>
                    <p><strong>Vendor:</strong> ${approval.vendor || 'N/A'}</p>
                    <p><strong>Created:</strong> ${approval.created_at ? new Date(approval.created_at).toLocaleString() : 'N/A'}</p>
                    <div class="approval-actions">
                        <button class="btn-approve" onclick="handleApproval('${approval.approval_id}', 'approve')">
                            ✅ Approve
                        </button>
                        <button class="btn-reject" onclick="handleApproval('${approval.approval_id}', 'reject')">
                            ❌ Reject
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            approvalsList.innerHTML = '<p class="empty-state">No pending approvals</p>';
        }
    } catch (error) {
        console.error('Error loading approvals:', error);
        document.getElementById('approvalsList').innerHTML = '<p class="empty-state">Error loading approvals</p>';
    }
}

// Handle Approval Actions
async function handleApproval(approvalId, action) {
    const comment = prompt(`Enter comment for ${action}:`);
    if (!comment) return;
    
    try {
        const response = await fetch(`${API_URL}/approvals/${approvalId}/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: action,
                approver: 'Dashboard User',
                comment: comment
            })
        });
        
        if (response.ok) {
            alert(`Successfully ${action}ed!`);
            // Refresh approvals and dashboard stats
            loadApprovals();
            loadDashboardStats();
        } else {
            alert('Error processing approval');
        }
    } catch (error) {
        alert('Error: ' + (error.message || 'Failed to process approval'));
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    // Load initial dashboard data
    loadDashboardStats();
    
    // Set up auto-refresh for dashboard stats
    setInterval(() => {
        const activeTab = document.querySelector('.tab-content.active');
        if (activeTab && activeTab.id === 'dashboard') {
            loadDashboardStats();
        }
    }, 30000); // Refresh every 30 seconds
});