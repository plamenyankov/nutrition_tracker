/**
 * Zyra Cycle - Workouts Page JavaScript
 * Handles screenshot imports and workouts table
 */

// ============== Module State ==============
let selectedFiles = [];

// ============== File Upload ==============
function initFileUpload() {
    const uploadZone = document.getElementById('bundleUploadZone');
    const fileInput = document.getElementById('bundleImageInput');
    const fileListContainer = document.getElementById('fileListContainer');
    const uploadActions = document.getElementById('uploadActions');
    const form = document.getElementById('bundleUploadForm');

    if (!uploadZone || !fileInput) return;

    // Click to select files
    uploadZone.addEventListener('click', () => fileInput.click());

    // Drag and drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    // Form submit
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (selectedFiles.length === 0) return;

        showLoading('Extracting data from screenshots...');
        showStatus('loading', 'Processing screenshots...');

        const formData = new FormData();
        selectedFiles.forEach(file => formData.append('images', file));

        try {
            const response = await fetch('/cycling-readiness/api/extract-batch', {
                method: 'POST',
                body: formData
            });

            // Handle non-OK responses before trying to parse JSON
            if (!response.ok) {
                hideLoading();
                if (response.status === 404) {
                    showStatus('error', 'Upload endpoint not found. Please check server configuration.');
                } else {
                    showStatus('error', `Upload failed (${response.status}). Please try again.`);
                }
                console.error('Upload error: HTTP', response.status);
                return;
            }

            // Safely parse JSON response
            let result;
            const text = await response.text();
            try {
                result = JSON.parse(text);
            } catch (parseErr) {
                hideLoading();
                showStatus('error', 'Unexpected server response. Please try again.');
                console.error('Upload error: Invalid JSON response:', text.slice(0, 200));
                return;
            }
            
            hideLoading();

            if (result.success) {
                // Log the raw response for debugging
                console.log('[Extract] Raw API response:', result);
                
                // Get count from summary or extraction_results
                const count = result.summary?.cycling_images + result.summary?.sleep_images + result.summary?.cardio_images 
                           || result.extraction_results?.length 
                           || selectedFiles.length;
                showStatus('success', `Processed ${count} screenshot${count !== 1 ? 's' : ''}`);
                
                // Adapt response format for displayExtractionResults
                // The backend returns extraction_results, but the frontend expects extractions
                if (result.extraction_results && !result.extractions) {
                    result.extractions = result.extraction_results.map(r => {
                        const isCycling = r.type === 'cycling_power' || r.type === 'watch_workout';
                        const isSleep = r.type === 'sleep_summary';
                        const normalizedType = isCycling ? 'cycling' : isSleep ? 'sleep' : r.type;
                        
                        // Extract date from fields or canonical data
                        let extractedDate = r.fields?.date || r.fields?.workout_date;
                        if (!extractedDate && isCycling && result.canonical_workout?.date) {
                            extractedDate = result.canonical_workout.date;
                        }
                        if (!extractedDate && isSleep && result.canonical_sleep?.date) {
                            extractedDate = result.canonical_sleep.date;
                        }
                        
                        // Build payload from fields for easy access
                        const payload = { ...r.fields };
                        if (extractedDate) payload.date = extractedDate;
                        
                        // Map canonical values to payload for cycling
                        if (isCycling && result.canonical_workout) {
                            const cw = result.canonical_workout;
                            payload.date = payload.date || cw.date;
                            payload.avg_power_w = payload.avg_power_w || cw.avg_power;
                            payload.max_power_w = payload.max_power_w || cw.max_power;
                            payload.avg_heart_rate = payload.avg_heart_rate || cw.avg_hr;
                            payload.max_heart_rate = payload.max_heart_rate || cw.max_hr;
                            payload.duration_minutes = payload.duration_minutes || cw.duration_minutes;
                        }
                        
                        // Map canonical values to payload for sleep
                        if (isSleep && result.canonical_sleep) {
                            const cs = result.canonical_sleep;
                            payload.date = payload.date || cs.date;
                            payload.total_sleep_minutes = payload.total_sleep_minutes || cs.total_sleep_minutes;
                            payload.deep_sleep_minutes = payload.deep_sleep_minutes || cs.deep_sleep_minutes;
                            payload.awake_minutes = payload.awake_minutes || cs.awake_minutes;
                            payload.min_heart_rate = payload.min_heart_rate || cs.min_hr;
                            payload.avg_heart_rate = payload.avg_heart_rate || cs.avg_hr;
                            payload.max_heart_rate = payload.max_heart_rate || cs.max_hr;
                        }
                        
                        return {
                            filename: r.filename,
                            type: normalizedType,
                            confidence: r.confidence,
                            fields: r.fields,
                            payload: payload,
                            missing_fields: []
                        };
                    });
                    
                    // Sort extractions: cycling first, then sleep, then others
                    result.extractions.sort((a, b) => {
                        const order = { cycling: 0, sleep: 1 };
                        const aOrder = order[a.type] ?? 2;
                        const bOrder = order[b.type] ?? 2;
                        return aOrder - bOrder;
                    });
                }
                
                // Add missing fields info from backend
                if (result.has_missing_data && result.missing_fields) {
                    if (result.missing_fields.workout?.length > 0 && result.extractions) {
                        // Apply missing fields to all cycling extractions
                        result.extractions.filter(e => e.type === 'cycling').forEach(ext => {
                            ext.missing_fields = result.missing_fields.workout;
                        });
                    }
                    if (result.missing_fields.sleep?.length > 0 && result.extractions) {
                        // Apply missing fields to all sleep extractions
                        result.extractions.filter(e => e.type === 'sleep').forEach(ext => {
                            ext.missing_fields = result.missing_fields.sleep;
                        });
                    }
                }
                
                console.log('[Extract] Processed extractions:', result.extractions);
                displayExtractionResults(result);
            } else {
                showStatus('error', result.error || 'Extraction failed');
            }
        } catch (err) {
            hideLoading();
            showStatus('error', 'Failed to process screenshots');
            console.error('Upload error:', err);
        }
    });
}

function handleFiles(files) {
    const fileListContainer = document.getElementById('fileListContainer');
    const uploadActions = document.getElementById('uploadActions');

    selectedFiles = Array.from(files);

    if (selectedFiles.length > 0) {
        fileListContainer.classList.remove('d-none');
        uploadActions.classList.remove('d-none');

        fileListContainer.innerHTML = selectedFiles.map((file, i) => `
            <div class="file-item">
                <i class="fas fa-image"></i>
                <span class="file-name">${file.name}</span>
                <button type="button" class="file-remove" onclick="removeFile(${i})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
    } else {
        fileListContainer.classList.add('d-none');
        uploadActions.classList.add('d-none');
    }
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    handleFiles(selectedFiles);
}

// ============== Status Messages ==============
function showStatus(type, message) {
    const el = document.getElementById('statusMessage');
    if (!el) return;
    el.className = `status-msg ${type}`;
    const icon = type === 'loading' ? 'fa-spinner fa-spin' : type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    el.innerHTML = `<i class="fas ${icon}"></i><span>${message}</span>`;
    el.classList.remove('d-none');
}

function hideStatus() {
    const el = document.getElementById('statusMessage');
    if (el) el.classList.add('d-none');
}

// ============== Extraction Results ==============
function displayExtractionResults(result) {
    const container = document.getElementById('extractionResults');
    if (!container) return;

    container.classList.remove('d-none');
    container.innerHTML = '';

    // Check if any items need review
    const needsReview = result.extractions?.some(e => e.missing_fields?.length > 0);

    if (needsReview) {
        // Store for review modal
        reviewData = result.extractions;
        showReviewModal(result.extractions);
    } else {
        // Auto-save if no missing fields
        saveBatchData(result.extractions);
    }

    // Show summary
    result.extractions?.forEach(ext => {
        const typeClass = ext.type === 'cycling' ? 'cycling' : ext.type === 'sleep' ? 'sleep' : 'unknown';
        const icon = ext.type === 'cycling' ? 'fa-bicycle' : ext.type === 'sleep' ? 'fa-moon' : 'fa-question';
        const missing = ext.missing_fields?.length > 0 
            ? `<span class="badge bg-warning text-dark ms-2">${ext.missing_fields.length} missing</span>` 
            : '';

        container.innerHTML += `
            <div class="extraction-item ${typeClass}">
                <div class="extraction-icon"><i class="fas ${icon}"></i></div>
                <div class="extraction-details">
                    <div class="extraction-filename">${ext.filename || 'Screenshot'}</div>
                    <div class="extraction-type">${ext.type}${missing}</div>
                </div>
            </div>
        `;
    });
}

async function saveBatchData(extractions) {
    showLoading('Saving data...');

    try {
        const response = await fetch('/cycling-readiness/api/batch-save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ extractions })
        });

        const result = await response.json();
        hideLoading();

        if (result.success) {
            showToast(`Saved ${result.saved_count} items`);
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(result.error || 'Error saving data', 'error');
        }
    } catch (err) {
        hideLoading();
        showToast('Error saving data', 'error');
    }
}

function showReviewModal(extractions) {
    reviewData = extractions;
    const content = document.getElementById('reviewContent');
    if (!content) return;

    content.innerHTML = extractions.map((ext, idx) => {
        const typeLabel = ext.type === 'cycling' ? 'Cycling Workout' : ext.type === 'sleep' ? 'Sleep Data' : 'Unknown';
        const icon = ext.type === 'cycling' ? 'fa-bicycle' : ext.type === 'sleep' ? 'fa-moon' : 'fa-question';
        const iconColor = ext.type === 'cycling' ? 'var(--color-green)' : ext.type === 'sleep' ? 'var(--color-blue)' : 'var(--color-muted)';
        
        // Format date for display
        const dateStr = ext.payload?.date || ext.fields?.date || ext.fields?.workout_date;
        const displayDate = dateStr ? formatDisplayDate(dateStr) : 'Unknown date';
        
        // Build HTML for missing fields
        const missingHtml = ext.missing_fields?.map(field => `
            <div class="review-field missing" data-review-index="${idx}">
                <label>${formatFieldLabel(field)}</label>
                <input type="${getFieldInputType(field)}" 
                       data-field="${field}"
                       class="form-control form-control-sm"
                       placeholder="Enter ${formatFieldLabel(field).toLowerCase()}"
                       value="${ext.payload?.[field] ?? ''}">
            </div>
        `).join('') || '';

        return `
            <div class="review-item" data-review-index="${idx}">
                <h5><i class="fas ${icon}" style="color: ${iconColor}; margin-right: 0.5rem;"></i>${typeLabel} - ${displayDate}</h5>
                ${missingHtml || '<p class="text-muted small" style="color: var(--color-muted);">All fields extracted successfully</p>'}
            </div>
        `;
    }).join('<hr style="border-color: rgba(255,255,255,0.1); margin: 1rem 0;">');

    document.getElementById('reviewModal').classList.add('active');
}

function formatDisplayDate(dateStr) {
    if (!dateStr) return 'Unknown date';
    try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return dateStr;
        return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch (e) {
        return dateStr;
    }
}

function formatFieldLabel(field) {
    return field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function getFieldInputType(field) {
    if (field.includes('date')) return 'date';
    if (field.includes('time') && !field.includes('minutes')) return 'time';
    return 'number';
}

// ============== Delete Handlers ==============
function initDeleteHandlers() {
    // Workout delete buttons
    document.querySelectorAll('.btn-delete-workout').forEach(btn => {
        btn.addEventListener('click', function() {
            const id = this.dataset.id;
            showConfirmModal('workout', id, 'Delete this workout?');
        });
    });
}

// ============== Edit Handlers ==============
function initEditWorkout() {
    document.querySelectorAll('.btn-edit-workout').forEach(btn => {
        btn.addEventListener('click', function() {
            openEditWorkoutModal(this.dataset.id);
        });
    });
}

// ============== Day View ==============
function initDayView() {
    document.querySelectorAll('.btn-view-day').forEach(btn => {
        btn.addEventListener('click', function() {
            openDayViewModal(this.dataset.date);
        });
    });
}

// ============== Initialize ==============
document.addEventListener('DOMContentLoaded', function() {
    initFileUpload();
    initDeleteHandlers();
    initEditWorkout();
    initDayView();
    console.log('🚴 Workouts page initialized');
});

// Export for global use
window.removeFile = removeFile;

