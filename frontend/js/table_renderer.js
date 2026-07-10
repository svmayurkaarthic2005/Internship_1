/**
 * SIS Copilot Data Table Renderer
 * Professional, paginated HTML table renderer for structured data
 */

// Pagination state map
const tableStates = new Map();

/**
 * Render structured data as a professional HTML table
 * @param {HTMLElement} container - Container element for the table
 * @param {Object} data - Structured data from backend
 */
function renderDataTable(container, data) {
    if (!container || !data) return;

    console.log('Rendering data table:', data);

    // Clear container
    container.innerHTML = '';

    // Determine table type and prepare data
    let tableConfig = null;

    if (data.surveys_by_block) {
        tableConfig = prepareSurveyTable(data);
    } else if (data.applications) {
        tableConfig = prepareApplicationsTable(data);
    } else if (data.field_visits) {
        tableConfig = prepareFieldVisitsTable(data);
    } else if (data.owners) {
        tableConfig = prepareOwnersTable(data);
    } else if (data.workload) {
        tableConfig = prepareWorkloadTable(data);
    } else if (data.jurisdiction) {
        tableConfig = prepareJurisdictionTable(data);
    } else if (data.rejections) {
        tableConfig = prepareRejectionTable(data);
    } else if (data.history) {
        tableConfig = prepareWorkflowTable(data);
    } else if (data.application_number) {
        tableConfig = prepareApplicationDetailTable(data);
    }

    if (!tableConfig) {
        console.warn('Unknown data structure or empty results, cannot render table');
        container.innerHTML = '<div class="data-table-empty">No records found.</div>';
        return;
    }

    // Create table HTML
    const tableHTML = createTableHTML(tableConfig);
    container.innerHTML = tableHTML;

    // Add event listeners
    setupTableEventListeners(container);
}

/**
 * Prepare survey numbers table configuration
 */
function prepareSurveyTable(data) {
    const rows = [];
    const hasJurisdiction = !!data.jurisdiction;

    for (const [blockNumber, surveys] of Object.entries(data.surveys_by_block || {})) {
        for (const survey of surveys) {
            const rowData = {
                'Survey Number': survey.survey_no || 'N/A',
                'Area (sqm)': survey.area_sqm ? Number(survey.area_sqm).toLocaleString() : 'N/A',
                'Land Type': survey.land_type || 'N/A',
                'Sub-Divisions': survey.subdivisions && survey.subdivisions.length > 0
                    ? survey.subdivisions.join(', ')
                    : 'None'
            };

            if (hasJurisdiction) {
                const wardName = data.jurisdiction.ward || data.jurisdiction.ward_number || 'N/A';
                const townName = data.jurisdiction.town || 'N/A';
                rowData['Location Chain'] = `Town ${townName} → Ward ${wardName} → Block ${blockNumber}`;
            }

            rows.push(rowData);
        }
    }

    const columns = ['Survey Number', 'Area (sqm)', 'Land Type', 'Sub-Divisions'];
    if (hasJurisdiction) {
        columns.push('Location Chain');
    }

    return {
        title: data.query_type || 'Survey Number Details',
        columns: columns,
        rows: rows,
        icon: '📋'
    };
}

/**
 * Prepare applications table configuration
 */
function prepareApplicationsTable(data) {
    const apps = data.applications || [];

    // FV detail style (from fv_unassigned_awaiting / immediate_action)
    const isFvDetail = apps.length > 0 && ('applicant_name' in apps[0] || 'days_pending' in apps[0]);

    if (isFvDetail) {
        // === Single record: show as full detail card ===
        if (apps.length === 1) {
            const app = apps[0];
            const rows = [
                { 'Field': 'Application No',          'Value': app.application_number  || 'N/A' },
                { 'Field': 'Applicant Name',           'Value': app.applicant_name      || 'N/A' },
                { 'Field': 'Survey No',                'Value': app.survey_no           || 'N/A' },
                { 'Field': 'Temp Sub Div No (SIS)',    'Value': app.sis_temp_sub_div    || 'N/A' },
                { 'Field': 'Fixed Sub Div No (DIS)',   'Value': app.dis_fixed_sub_div   || 'N/A' },
                { 'Field': 'Town',                     'Value': app.town_name           || 'N/A' },
                { 'Field': 'Ward',                     'Value': app.ward_number  ? `Ward ${app.ward_number}`   : 'N/A' },
                { 'Field': 'Block',                    'Value': app.block_number ? `Block ${app.block_number}` : 'N/A' },
                { 'Field': 'Current Stage',            'Value': app.current_stage   || 'N/A' },
                { 'Field': 'Current Status',           'Value': app.current_status  || 'N/A' },
                { 'Field': 'Submission Date',          'Value': app.submission_date ? new Date(app.submission_date).toLocaleDateString() : 'N/A' },
                { 'Field': 'Days Pending',             'Value': app.days_pending ?? 'N/A' },
                { 'Field': 'Priority',                 'Value': app.priority || 'Normal' },
            ];
            return {
                title: data.query_type || 'Application Details',
                columns: ['Field', 'Value'],
                rows: rows,
                icon: '📋',
                disablePagination: true
            };
        }

        // === Multiple records: show as wide table ===
        const rows = apps.map(app => ({
            'App No':                app.application_number || 'N/A',
            'Applicant':             app.applicant_name     || 'N/A',
            'Survey No':             app.survey_no          || 'N/A',
            'Temp Sub Div (SIS)':    app.sis_temp_sub_div   || 'N/A',
            'Fixed Sub Div (DIS)':   app.dis_fixed_sub_div  || 'N/A',
            'Town':                  app.town_name          || 'N/A',
            'Ward':                  app.ward_number  ? `Ward ${app.ward_number}`   : 'N/A',
            'Block':                 app.block_number ? `Block ${app.block_number}` : 'N/A',
            'Stage':                 app.current_stage  || 'N/A',
            'Status':                app.current_status || 'N/A',
            'Days Pending':          app.days_pending ?? 'N/A',
            'Priority':              app.priority || 'Normal'
        }));
        return {
            title: data.query_type || 'Applications',
            columns: ['App No', 'Applicant', 'Survey No', 'Temp Sub Div (SIS)', 'Fixed Sub Div (DIS)', 'Town', 'Ward', 'Block', 'Stage', 'Status', 'Days Pending', 'Priority'],
            rows: rows,
            icon: '🗓️'
        };
    }



    // Standard style (from pending / immediate action count queries)
    const rows = apps.map(app => ({
        'Application Number': app.application_number || 'N/A',
        'Type': app.type || 'N/A',
        'Town': app.town_name || 'N/A',
        'Ward': app.ward_number ? `Ward ${app.ward_number}` : 'N/A',
        'Status': app.status || 'Pending',
        'Stage': app.current_stage || app.stage || 'N/A',
        'Submitted Date': app.submission_date
            ? new Date(app.submission_date).toLocaleDateString()
            : 'N/A'
    }));

    return {
        title: data.query_type || 'Pending Applications',
        columns: ['Application Number', 'Type', 'Town', 'Ward', 'Status', 'Stage', 'Submitted Date'],
        rows: rows,
        icon: '📄'
    };
}

/**
 * Prepare field visits table configuration
 */
function prepareFieldVisitsTable(data) {
    const rows = data.field_visits.map(visit => ({
        'Application Number': visit.application_number || 'N/A',
        'Survey Number': visit.survey_no || 'N/A',
        'Block': visit.block_number ? `Block ${visit.block_number}` : 'N/A',
        'Type': visit.application_type || 'N/A',
        'Status': visit.status || 'N/A',
        'Scheduled Date': visit.field_visit_date 
            ? new Date(visit.field_visit_date).toLocaleDateString() 
            : 'Not Scheduled'
    }));

    return {
        title: data.query_type || 'Field Visits',
        columns: ['Application Number', 'Survey Number', 'Block', 'Type', 'Status', 'Scheduled Date'],
        rows: rows,
        icon: '🗓️'
    };
}

/**
 * Prepare owners table configuration
 */
function prepareOwnersTable(data) {
    const rows = data.owners.map(owner => ({
        'Owner Name': owner.owner_name || owner.name || 'N/A',
        'Sub-Division': owner.sub_division || 'Survey Level',
        'Ownership Share': owner.ownership_share || 'N/A',
        'Ownership Type': owner.ownership_type || 'N/A',
        'Joint Owner': owner.is_joint_owner ? 'Yes' : 'No'
    }));

    return {
        title: data.query_type || `Survey ${data.survey_no || ''} Owners`,
        columns: ['Owner Name', 'Sub-Division', 'Ownership Share', 'Ownership Type', 'Joint Owner'],
        rows: rows,
        icon: '👤'
    };
}

/**
 * Renders the SIS officer's assigned jurisdiction as a table.
 * Hierarchy: District → Taluk → Town → Ward → Block
 */
function prepareJurisdictionTable(data) {
    const j = data.jurisdiction || {};
    const district = j.district || {};
    const taluk = j.taluk || {};
    const towns = j.towns || [];

    const rows = [];

    if (!towns.length) {
        rows.push({
            'Level': 'District',
            'Code / Number': district.code || 'N/A',
            'Name': district.name || 'N/A',
            'Count': '—'
        });
        rows.push({
            'Level': 'Taluk',
            'Code / Number': '—',
            'Name': taluk.name || 'N/A',
            'Count': '—'
        });
    } else {
        rows.push({
            'Level': 'District',
            'Code / Number': district.code || 'N/A',
            'Name': district.name || 'N/A',
            'Count': '—'
        });
        rows.push({
            'Level': 'Taluk',
            'Code / Number': '—',
            'Name': taluk.name || 'N/A',
            'Count': `${towns.length} Town(s)`
        });

        towns.forEach(town => {
            const wardCount = (town.wards || []).length;
            const blockCount = (town.wards || []).reduce(
                (sum, w) => sum + (w.blocks || []).length, 0
            );
            rows.push({
                'Level': 'Town',
                'Code / Number': '—',
                'Name': town.name || 'N/A',
                'Count': `${wardCount} Ward(s), ${blockCount} Block(s)`
            });
        });
    }

    if (j.survey_count !== undefined) {
        rows.push({
            'Level': 'Survey Numbers',
            'Code / Number': '—',
            'Name': '—',
            'Count': j.survey_count
        });
    }
    if (j.active_applications !== undefined) {
        rows.push({
            'Level': 'Active Applications',
            'Code / Number': '—',
            'Name': '—',
            'Count': j.active_applications
        });
    }

    return {
        title: data.query_type || 'Jurisdiction Summary',
        columns: ['Level', 'Code / Number', 'Name', 'Count'],
        rows: rows,
        icon: '🗺️',
        disablePagination: true
    };
}

/**
 * Renders rejection history for an application.
 */
function prepareRejectionTable(data) {
    const rows = (data.rejections || []).map(r => ({
        'Rejected By': r.source || 'N/A',
        'Reason': r.reason_text || 'N/A',
        'Rejected On': r.rejected_at 
            ? new Date(r.rejected_at).toLocaleDateString() 
            : 'N/A',
        'Resubmitted': r.resubmitted_at 
            ? new Date(r.resubmitted_at).toLocaleDateString() 
            : 'Not yet'
    }));

    return {
        title: data.query_type || `Rejections — ${data.application_number || ''}`,
        columns: ['Rejected By', 'Reason', 'Rejected On', 'Resubmitted'],
        rows: rows,
        icon: '❌',
        disablePagination: true
    };
}

/**
 * Renders workflow stage history for an application.
 */
function prepareWorkflowTable(data) {
    const rows = (data.history || []).map((h, i) => ({
        'Step': i + 1,
        'From Stage': h.from_stage || '—',
        'To Stage': h.to_stage || 'N/A',
        'Date': h.changed_at 
            ? new Date(h.changed_at).toLocaleDateString() 
            : 'N/A',
        'Changed By': h.changed_by_name || 'System',
        'Note': h.note || '—'
    }));

    return {
        title: data.query_type || `Workflow — ${data.application_number || ''}`,
        columns: ['Step', 'From Stage', 'To Stage', 'Date', 'Changed By', 'Note'],
        rows: rows,
        icon: '🔄',
        disablePagination: rows.length <= 10
    };
}

/**
 * Prepare workload table configuration
 */
function prepareWorkloadTable(data) {
    const w = data.workload || {};
    const rows = [
        { 'Metric': 'Total Applications', 'Count': w.total_applications || 0 },
        { 'Metric': 'Pending Applications', 'Count': w.pending_applications || 0 },
        { 'Metric': 'Completed Applications', 'Count': w.completed_applications || 0 }
    ];

    return {
        title: data.query_type || 'Workload Summary',
        columns: ['Metric', 'Count'],
        rows: rows,
        icon: '📊',
        disablePagination: true
    };
}

/**
 * Prepare single application and applicant details table configuration
 */
function prepareApplicationDetailTable(data) {
    const rows = [
        { 'Field': 'Application Number', 'Details': data.application_number || 'N/A' },
        { 'Field': 'Application Type', 'Details': data.type || 'N/A' },
        { 'Field': 'Included Sub-divisions', 'Details': data.included_subdivisions || 'N/A' },
        { 'Field': 'Current Status', 'Details': data.status || 'N/A' },
        { 'Field': 'Current Stage', 'Details': data.stage || 'N/A' },
        { 'Field': 'Submission Date', 'Details': data.submission_date ? new Date(data.submission_date).toLocaleDateString() : 'N/A' },
        { 'Field': 'Field Visit Scheduled', 'Details': data.field_visit_scheduled ? `Yes (${data.field_visit_date ? new Date(data.field_visit_date).toLocaleDateString() : 'N/A'})` : 'No' },
        { 'Field': 'Overdue', 'Details': data.is_overdue ? 'Yes' : 'No' },
        { 'Field': 'Priority Flag', 'Details': data.priority_flag ? 'Yes' : 'No' },
        { 'Field': 'Applicant Name', 'Details': data.applicant_name || 'N/A' },
        { 'Field': 'Applicant Mobile', 'Details': data.applicant_mobile || 'N/A' },
        { 'Field': 'Applicant Email', 'Details': data.applicant_email || 'N/A' },
        { 'Field': 'Applicant Address', 'Details': data.applicant_address || 'N/A' },
        { 'Field': 'Aadhaar (Last 4)', 'Details': data.applicant_aadhaar_last4 || 'N/A' },
        { 'Field': 'Declared Reason', 'Details': data.declared_reason || 'N/A' }
    ];

    return {
        title: data.query_type || 'Application & Applicant Details',
        columns: ['Field', 'Details'],
        rows: rows,
        icon: '📋',
        disablePagination: true
    };
}

/**
 * Helper to build badge HTML for status columns
 */
function getStatusBadge(val) {
    if (!val) return 'N/A';
    const s = String(val).toUpperCase();
    
    if (s.includes('PENDING')) {
        return `<span class="status-badge status-pending">${escapeHtml(val)}</span>`;
    } else if (s.includes('APPROVED') || s === 'COMPLETED') {
        return `<span class="status-badge status-approved">${escapeHtml(val)}</span>`;
    } else if (s.includes('REJECTED')) {
        return `<span class="status-badge status-rejected">${escapeHtml(val)}</span>`;
    } else if (s === 'SCHEDULED' || s === 'RESCHEDULED') {
        return `<span class="status-badge status-scheduled">${escapeHtml(val)}</span>`;
    } else if (s === 'OVERDUE') {
        return `<span class="status-badge status-overdue">${escapeHtml(val)}</span>`;
    } else if (s === 'SUBMITTED') {
        return `<span class="status-badge status-submitted">${escapeHtml(val)}</span>`;
    } else if (s.includes('SIS')) {
        return `<span class="status-badge status-sis">${escapeHtml(val)}</span>`;
    } else if (s.includes('SD')) {
        return `<span class="status-badge status-sd">${escapeHtml(val)}</span>`;
    } else if (s.includes('DIS')) {
        return `<span class="status-badge status-dis">${escapeHtml(val)}</span>`;
    } else if (s.includes('TAHSILDAR')) {
        return `<span class="status-badge status-tahsildar">${escapeHtml(val)}</span>`;
    } else if (s === 'PATTA_ORDER_GENERATED') {
        return `<span class="status-badge status-approved">${escapeHtml(val)}</span>`;
    } else if (s === 'CLOSED') {
        return `<span class="status-badge status-closed">${escapeHtml(val)}</span>`;
    }
    
    return escapeHtml(val);
}

/**
 * Create HTML string for the table config
 */
function createTableHTML(config) {
    const { title, columns, rows, icon, disablePagination } = config;

    if (!rows || rows.length === 0) {
        return `
            <div class="data-table-card">
                <div class="data-table-header">
                    <div class="data-table-title-section">
                        <span class="data-table-icon">${icon || '📋'}</span>
                        <h3 class="data-table-title">${escapeHtml(title)}</h3>
                    </div>
                </div>
                <div class="data-table-empty">
                    <span>No records found.</span>
                </div>
            </div>
        `;
    }

    const tableId = 'table-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
    const rowsPerPage = 10;
    const paginationEnabled = !disablePagination && rows.length > rowsPerPage;
    
    if (paginationEnabled) {
        tableStates.set(tableId, {
            currentPage: 1,
            totalPages: Math.ceil(rows.length / rowsPerPage),
            rowsPerPage: rowsPerPage,
            allRows: rows,
            columns: columns
        });
    }

    const visibleRows = paginationEnabled ? rows.slice(0, rowsPerPage) : rows;

    let headersHTML = columns.map(c => `<th>${escapeHtml(c)}</th>`).join('');
    
    let rowsHTML = visibleRows.map(row => {
        let cells = columns.map(col => {
            const val = row[col];
            if (col === 'Status' || col === 'Stage') {
                return `<td>${getStatusBadge(val)}</td>`;
            }
            return `<td>${escapeHtml(String(val !== undefined && val !== null ? val : 'N/A'))}</td>`;
        }).join('');
        return `<tr>${cells}</tr>`;
    }).join('');

    let footerHTML = '';
    if (paginationEnabled) {
        const total = rows.length;
        const toIndex = Math.min(rowsPerPage, total);
        footerHTML = `
            <div class="data-table-footer">
                <div class="data-table-pagination">
                    <span class="pagination-info">Showing 1-${toIndex} of ${total}</span>
                    <div class="pagination-controls">
                        <button class="btn-pagination btn-prev" disabled>Prev</button>
                        <span class="pagination-page">Page 1 of ${Math.ceil(total / rowsPerPage)}</span>
                        <button class="btn-pagination btn-next">Next</button>
                    </div>
                </div>
            </div>
        `;
    }

    return `
        <div class="data-table-card" data-table-id="${tableId}">
            <div class="data-table-header">
                <div class="data-table-title-section">
                    <span class="data-table-icon">${icon}</span>
                    <h3 class="data-table-title">${escapeHtml(title)}</h3>
                    <span class="data-table-count">${rows.length} records</span>
                </div>
                <button class="btn-copy-table" onclick="window.copyTableData(this)">Copy</button>
            </div>
            <div class="data-table-container">
                <table class="data-table">
                    <thead>
                        <tr>${headersHTML}</tr>
                    </thead>
                    <tbody class="table-body-rows">
                        ${rowsHTML}
                    </tbody>
                </table>
            </div>
            <div class="data-table-scroll-hint">← scroll to view more →</div>
            ${footerHTML}
        </div>
    `;
}

/**
 * Setup event listeners for the table container
 */
function setupTableEventListeners(container) {
    if (!container) return;
    
    // Add event listeners for prev/next buttons
    const prevBtn = container.querySelector('.btn-prev');
    const nextBtn = container.querySelector('.btn-next');
    
    if (prevBtn) {
        prevBtn.addEventListener('click', handlePagination);
    }
    if (nextBtn) {
        nextBtn.addEventListener('click', handlePagination);
    }
}

/**
 * Handle table pagination events
 */
function handlePagination(event) {
    const button = event.target;
    const isNext = button.classList.contains('btn-next');
    const card = button.closest('.data-table-card');
    if (!card) return;
    
    const tableId = card.getAttribute('data-table-id');
    const state = tableStates.get(tableId);
    if (!state) return;
    
    // Calculate page change
    let newPage = state.currentPage;
    if (isNext) {
        newPage = Math.min(state.currentPage + 1, state.totalPages);
    } else {
        newPage = Math.max(state.currentPage - 1, 1);
    }
    
    if (newPage === state.currentPage) return;
    
    // Update state
    state.currentPage = newPage;
    tableStates.set(tableId, state);
    
    // Re-render table body rows
    const tbody = card.querySelector('.table-body-rows');
    const fromIdx = (newPage - 1) * state.rowsPerPage;
    const toIdx = Math.min(fromIdx + state.rowsPerPage, state.allRows.length);
    const visibleRows = state.allRows.slice(fromIdx, toIdx);
    
    tbody.innerHTML = visibleRows.map(row => {
        let cells = state.columns.map(col => {
            const val = row[col];
            if (col === 'Status' || col === 'Stage') {
                return `<td>${getStatusBadge(val)}</td>`;
            }
            return `<td>${escapeHtml(String(val !== undefined && val !== null ? val : 'N/A'))}</td>`;
        }).join('');
        return `<tr>${cells}</tr>`;
    }).join('');
    
    // Update pagination labels
    const info = card.querySelector('.pagination-info');
    if (info) {
        info.textContent = `Showing ${fromIdx + 1}-${toIdx} of ${state.allRows.length}`;
    }
    
    const pageText = card.querySelector('.pagination-page');
    if (pageText) {
        pageText.textContent = `Page ${newPage} of ${state.totalPages}`;
    }
    
    // Enable/disable buttons
    const prevBtn = card.querySelector('.btn-prev');
    const nextBtn = card.querySelector('.btn-next');
    
    if (prevBtn) prevBtn.disabled = newPage === 1;
    if (nextBtn) nextBtn.disabled = newPage === state.totalPages;
}

/**
 * Copy data table contents as TSV
 */
window.copyTableData = function(button) {
    const card = button.closest('.data-table-card');
    if (!card) return;
    
    const table = card.querySelector('table');
    if (!table) return;
    
    let tsv = [];
    // Get headers
    const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
    tsv.push(headers.join('\t'));
    
    // Get all rows from stored state if available, or fall back to DOM
    const tableId = card.getAttribute('data-table-id');
    const state = tableStates.get(tableId);
    
    if (state && state.allRows && state.columns) {
        state.allRows.forEach(row => {
            const rowData = state.columns.map(col => String(row[col] !== undefined && row[col] !== null ? row[col] : 'N/A'));
            tsv.push(rowData.join('\t'));
        });
    } else {
        const rows = Array.from(table.querySelectorAll('tbody tr'));
        rows.forEach(tr => {
            const cells = Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim());
            tsv.push(cells.join('\t'));
        });
    }
    
    const textToCopy = tsv.join('\n');
    navigator.clipboard.writeText(textToCopy).then(() => {
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.style.borderColor = 'var(--primary, #1E40AF)';
        button.style.color = 'var(--primary, #1E40AF)';
        
        setTimeout(() => {
            button.textContent = originalText;
            button.style.borderColor = '';
            button.style.color = '';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy table data:', err);
    });
};

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
