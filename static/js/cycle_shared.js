/**
 * Zyra Cycle - Shared JavaScript Utilities
 * Common functions used across all pages
 */

// ============== Toast Helper ==============
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast-zyra ${type}`;
    toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} me-2"></i>${message}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ============== Loading Overlay ==============
function showLoading(text = 'Processing...') {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.querySelector('.loading-text').textContent = text;
        loadingOverlay.classList.add('active');
    }
}

function hideLoading() { 
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.classList.remove('active');
    }
}

// ============== Confirm Modal ==============
let deleteType = null;
let deleteId = null;

function showConfirmModal(type, id, title = 'Delete?') {
    deleteType = type;
    deleteId = id;
    document.getElementById('confirmModalTitle').textContent = title;
    document.getElementById('confirmModal').classList.add('active');
}

function closeConfirmModal() {
    document.getElementById('confirmModal').classList.remove('active');
    deleteType = null;
    deleteId = null;
}

// ============== Day View Modal ==============
function openDayViewModal(date) {
    document.getElementById('dayViewDate').textContent = date;
    document.getElementById('dayViewModal').classList.add('active');
    loadDayViewData(date);
}

function closeDayViewModal() {
    document.getElementById('dayViewModal').classList.remove('active');
}

async function loadDayViewData(date) {
    const content = document.getElementById('dayViewContent');
    content.innerHTML = '<div class="text-center" style="padding: 2rem; color: var(--color-muted);"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
    
    try {
        const response = await fetch(`/cycling-readiness/api/day-data?date=${date}`);
        const data = await response.json();
        
        if (data.success) {
            content.innerHTML = renderDayViewContent(data);
        } else {
            content.innerHTML = `<p class="text-danger">Error: ${data.error}</p>`;
        }
    } catch (err) {
        content.innerHTML = `<p class="text-danger">Error loading data</p>`;
    }
}

function renderDayViewContent(data) {
    let html = '<div class="day-view-grid">';
    
    // Workout section
    html += '<div class="day-view-section">';
    html += '<h4 class="day-view-section-title"><i class="fas fa-bicycle me-2" style="color: var(--color-green)"></i>Workout</h4>';
    if (data.workout) {
        html += `
            <div class="day-view-metrics">
                <div class="day-view-metric"><span class="label">Duration</span><span class="value">${formatDuration(data.workout.duration_sec)}</span></div>
                <div class="day-view-metric"><span class="label">Avg Power</span><span class="value">${data.workout.avg_power_w || '--'}W</span></div>
                <div class="day-view-metric"><span class="label">TSS</span><span class="value">${data.workout.tss || '--'}</span></div>
                <div class="day-view-metric"><span class="label">Avg HR</span><span class="value">${data.workout.avg_heart_rate || '--'} bpm</span></div>
                <div class="day-view-metric"><span class="label">Max HR</span><span class="value">${data.workout.max_heart_rate || '--'} bpm</span></div>
                <div class="day-view-metric"><span class="label">Distance</span><span class="value">${data.workout.distance_km ? data.workout.distance_km.toFixed(1) + ' km' : '--'}</span></div>
            </div>`;
    } else {
        html += '<p class="text-muted small">No workout data</p>';
    }
    html += '</div>';
    
    // Readiness section
    html += '<div class="day-view-section">';
    html += '<h4 class="day-view-section-title"><i class="fas fa-sun me-2" style="color: var(--color-teal)"></i>Readiness</h4>';
    if (data.readiness) {
        html += `
            <div class="day-view-metrics">
                <div class="day-view-metric"><span class="label">Energy</span><span class="value">${data.readiness.energy || '--'}/5</span></div>
                <div class="day-view-metric"><span class="label">Mood</span><span class="value">${data.readiness.mood || '--'}/5</span></div>
                <div class="day-view-metric"><span class="label">Fatigue</span><span class="value">${data.readiness.muscle_fatigue || '--'}/5</span></div>
                <div class="day-view-metric"><span class="label">Score</span><span class="value">${data.readiness.morning_score || '--'}%</span></div>
            </div>`;
    } else {
        html += '<p class="text-muted small">No readiness data</p>';
    }
    html += '</div>';
    
    // Sleep section
    html += '<div class="day-view-section">';
    html += '<h4 class="day-view-section-title"><i class="fas fa-moon me-2" style="color: var(--color-blue)"></i>Sleep</h4>';
    if (data.sleep) {
        const totalHrs = data.sleep.total_sleep_minutes ? (data.sleep.total_sleep_minutes / 60).toFixed(1) : '--';
        const deepHrs = data.sleep.deep_sleep_minutes ? (data.sleep.deep_sleep_minutes / 60).toFixed(1) : '--';
        html += `
            <div class="day-view-metrics">
                <div class="day-view-metric"><span class="label">Total Sleep</span><span class="value">${totalHrs}h</span></div>
                <div class="day-view-metric"><span class="label">Deep Sleep</span><span class="value">${deepHrs}h</span></div>
                <div class="day-view-metric"><span class="label">Min HR</span><span class="value">${data.sleep.min_heart_rate || '--'} bpm</span></div>
            </div>`;
    } else {
        html += '<p class="text-muted small">No sleep data</p>';
    }
    html += '</div>';
    
    // Cardio section
    html += '<div class="day-view-section">';
    html += '<h4 class="day-view-section-title"><i class="fas fa-heartbeat me-2" style="color: var(--color-red)"></i>Cardio Metrics</h4>';
    if (data.cardio) {
        const hrvAvg = (data.cardio.hrv_low_ms && data.cardio.hrv_high_ms) 
            ? Math.round((data.cardio.hrv_low_ms + data.cardio.hrv_high_ms) / 2) 
            : '--';
        html += `
            <div class="day-view-metrics">
                <div class="day-view-metric"><span class="label">RHR</span><span class="value">${data.cardio.rhr_bpm || '--'} bpm</span></div>
                <div class="day-view-metric"><span class="label">HRV Avg</span><span class="value">${hrvAvg} ms</span></div>
                <div class="day-view-metric"><span class="label">HRV Range</span><span class="value">${data.cardio.hrv_low_ms || '--'} - ${data.cardio.hrv_high_ms || '--'} ms</span></div>
            </div>`;
    } else {
        html += '<p class="text-muted small">No cardio data</p>';
    }
    html += '</div>';
    
    html += '</div>';
    return html;
}

function formatDuration(seconds) {
    if (!seconds) return '--';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// ============== Edit Workout Modal ==============
function openEditWorkoutModal(workoutId) {
    showLoading('Loading workout data...');
    
    fetch(`/cycling-readiness/api/workouts/${workoutId}`)
        .then(res => res.json())
        .then(data => {
            hideLoading();
            if (data.success && data.workout) {
                populateEditWorkoutModal(data.workout);
                document.getElementById('editWorkoutModal').classList.add('active');
            } else {
                showToast('Error loading workout', 'error');
            }
        })
        .catch(err => {
            hideLoading();
            showToast('Error loading workout', 'error');
        });
}

function populateEditWorkoutModal(workout) {
    document.getElementById('editWorkoutId').value = workout.id;
    document.getElementById('editDate').value = workout.date;
    
    // Convert duration seconds to mm:ss
    if (workout.duration_sec) {
        const mins = Math.floor(workout.duration_sec / 60);
        const secs = workout.duration_sec % 60;
        document.getElementById('editDuration').value = `${mins}:${secs.toString().padStart(2, '0')}`;
    } else {
        document.getElementById('editDuration').value = '';
    }
    
    document.getElementById('editAvgPower').value = workout.avg_power_w || '';
    document.getElementById('editMaxPower').value = workout.max_power_w || '';
    document.getElementById('editNormalizedPower').value = workout.normalized_power_w || '';
    document.getElementById('editIF').value = workout.intensity_factor || '';
    document.getElementById('editTSS').value = workout.tss || '';
    document.getElementById('editAvgHR').value = workout.avg_heart_rate || '';
    document.getElementById('editMaxHR').value = workout.max_heart_rate || '';
    document.getElementById('editCadence').value = workout.avg_cadence || '';
    document.getElementById('editDistance').value = workout.distance_km || '';
    document.getElementById('editKcalActive').value = workout.kcal_active || '';
    document.getElementById('editKcalTotal').value = workout.kcal_total || '';
    document.getElementById('editNotes').value = workout.notes || '';
}

function closeEditModal() {
    document.getElementById('editWorkoutModal').classList.remove('active');
}

async function saveEditedWorkout() {
    const workoutId = document.getElementById('editWorkoutId').value;
    const durationStr = document.getElementById('editDuration').value;
    
    // Parse duration mm:ss to seconds
    let durationSec = null;
    if (durationStr) {
        const parts = durationStr.split(':');
        if (parts.length === 2) {
            durationSec = parseInt(parts[0]) * 60 + parseInt(parts[1]);
        }
    }
    
    const data = {
        date: document.getElementById('editDate').value,
        duration_sec: durationSec,
        avg_power_w: parseFloat(document.getElementById('editAvgPower').value) || null,
        max_power_w: parseFloat(document.getElementById('editMaxPower').value) || null,
        normalized_power_w: parseFloat(document.getElementById('editNormalizedPower').value) || null,
        intensity_factor: parseFloat(document.getElementById('editIF').value) || null,
        tss: parseFloat(document.getElementById('editTSS').value) || null,
        avg_heart_rate: parseInt(document.getElementById('editAvgHR').value) || null,
        max_heart_rate: parseInt(document.getElementById('editMaxHR').value) || null,
        avg_cadence: parseInt(document.getElementById('editCadence').value) || null,
        distance_km: parseFloat(document.getElementById('editDistance').value) || null,
        kcal_active: parseInt(document.getElementById('editKcalActive').value) || null,
        kcal_total: parseInt(document.getElementById('editKcalTotal').value) || null,
        notes: document.getElementById('editNotes').value || null
    };
    
    try {
        const response = await fetch(`/cycling-readiness/api/workouts/${workoutId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Workout updated successfully');
            closeEditModal();
            setTimeout(() => location.reload(), 500);
        } else {
            showToast(result.error || 'Error updating workout', 'error');
        }
    } catch (err) {
        showToast('Error updating workout', 'error');
    }
}

// ============== Edit Readiness Modal ==============
function openEditReadinessModal(entryId, date) {
    showLoading('Loading readiness data...');
    
    fetch(`/cycling-readiness/api/readiness-with-cardio?date=${date}`)
        .then(res => res.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                populateEditReadinessModal(data.readiness, data.cardio);
                document.getElementById('editReadinessId').value = entryId;
                document.getElementById('editReadinessDate').value = date;
                document.getElementById('editReadinessModal').classList.add('active');
            } else {
                showToast('Error loading readiness data', 'error');
            }
        })
        .catch(err => {
            hideLoading();
            showToast('Error loading readiness data', 'error');
        });
}

function populateEditReadinessModal(readiness, cardio) {
    // Populate readiness fields
    if (readiness) {
        document.getElementById('editReadinessEnergy').value = readiness.energy || '';
        document.getElementById('editReadinessMood').value = readiness.mood || '';
        document.getElementById('editReadinessFatigue').value = readiness.muscle_fatigue || '';
        document.getElementById('editReadinessHrvStatus').value = readiness.hrv_status || '';
        document.getElementById('editReadinessRhrStatus').value = readiness.rhr_status || '';
        document.getElementById('editReadinessMinHrStatus').value = readiness.min_hr_status || '';
        document.getElementById('editReadinessSymptoms').checked = readiness.symptoms_flag || false;
        document.getElementById('editReadinessNotes').value = readiness.notes || '';
    }
    
    // Show cardio data if available
    const cardioDisplay = document.getElementById('editCardioDisplay');
    if (cardio && (cardio.rhr_bpm || cardio.hrv_low_ms)) {
        cardioDisplay.style.display = 'block';
        document.getElementById('editDisplayRhr').textContent = cardio.rhr_bpm ? `${cardio.rhr_bpm} bpm` : '--';
        const hrvAvg = (cardio.hrv_low_ms && cardio.hrv_high_ms) 
            ? Math.round((cardio.hrv_low_ms + cardio.hrv_high_ms) / 2) 
            : null;
        document.getElementById('editDisplayHrv').textContent = hrvAvg ? `${hrvAvg} ms` : '--';
    } else {
        cardioDisplay.style.display = 'none';
    }
}

function closeEditReadinessModal() {
    document.getElementById('editReadinessModal').classList.remove('active');
}

async function saveEditedReadiness() {
    const entryId = document.getElementById('editReadinessId').value;
    
    const data = {
        energy: parseInt(document.getElementById('editReadinessEnergy').value) || null,
        mood: parseInt(document.getElementById('editReadinessMood').value) || null,
        muscle_fatigue: parseInt(document.getElementById('editReadinessFatigue').value) || null,
        hrv_status: document.getElementById('editReadinessHrvStatus').value || null,
        rhr_status: document.getElementById('editReadinessRhrStatus').value || null,
        min_hr_status: document.getElementById('editReadinessMinHrStatus').value || null,
        symptoms_flag: document.getElementById('editReadinessSymptoms').checked,
        notes: document.getElementById('editReadinessNotes').value || null
    };
    
    try {
        const response = await fetch(`/cycling-readiness/api/readiness/${entryId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Readiness entry updated successfully');
            closeEditReadinessModal();
            setTimeout(() => location.reload(), 500);
        } else {
            showToast(result.error || 'Error updating readiness entry', 'error');
        }
    } catch (err) {
        showToast('Error updating readiness entry', 'error');
    }
}

// ============== Delete Handlers ==============
async function deleteWorkout(id) {
    try {
        const response = await fetch(`/cycling-readiness/api/workouts/${id}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (result.success) {
            showToast('Workout deleted');
            closeConfirmModal();
            setTimeout(() => location.reload(), 500);
        } else {
            showToast(result.error || 'Error deleting workout', 'error');
        }
    } catch (err) {
        showToast('Error deleting workout', 'error');
    }
}

async function deleteReadiness(id) {
    try {
        const response = await fetch(`/cycling-readiness/api/readiness/${id}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (result.success) {
            showToast('Readiness entry deleted');
            closeConfirmModal();
            setTimeout(() => location.reload(), 500);
        } else {
            showToast(result.error || 'Error deleting readiness entry', 'error');
        }
    } catch (err) {
        showToast('Error deleting readiness entry', 'error');
    }
}

// ============== Review Modal (for screenshot extraction) ==============
let reviewData = null;

function closeReviewModal() {
    document.getElementById('reviewModal').classList.remove('active');
    reviewData = null;
}

async function skipReviewAndSave() {
    if (!reviewData) return;
    
    showLoading('Saving data...');
    
    try {
        const response = await fetch('/cycling-readiness/api/batch-save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ extractions: reviewData })
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showToast(`Saved ${result.saved_count} items`);
            closeReviewModal();
            setTimeout(() => location.reload(), 500);
        } else {
            showToast(result.error || 'Error saving data', 'error');
        }
    } catch (err) {
        hideLoading();
        showToast('Error saving data', 'error');
    }
}

async function saveReviewedData() {
    if (!reviewData) return;
    
    // Collect corrected values from form
    reviewData.forEach((item, idx) => {
        const container = document.querySelector(`[data-review-index="${idx}"]`);
        if (!container) return;
        
        container.querySelectorAll('input, select').forEach(input => {
            const field = input.dataset.field;
            if (field && item.payload) {
                const value = input.type === 'checkbox' ? input.checked : input.value;
                if (value !== '' && value !== null) {
                    item.payload[field] = input.type === 'number' ? parseFloat(value) : value;
                }
            }
        });
    });
    
    await skipReviewAndSave();
}

// ============== Day Type Helpers ==============
const DAY_TYPE_LABELS = {
    'rest': 'Rest Day',
    'recovery_spin_z1': 'Recovery Z1',
    'easy_endurance_z1': 'Easy Z1',
    'steady_endurance_z2': 'Endurance Z2',
    'progressive_endurance': 'Progressive',
    'norwegian_4x4': '4×4 VO2max',
    'threshold_3x8': '3×8 Threshold',
    'vo2max_intervals': 'VO2max Intervals',
    'cadence_drills': 'Cadence Drills',
    'hybrid_endurance': 'Hybrid',
    'other': 'Training'
};

const DAY_TYPE_CLASSES = {
    'rest': 'rest',
    'recovery_spin_z1': 'z1',
    'easy_endurance_z1': 'z1',
    'steady_endurance_z2': 'z2',
    'progressive_endurance': 'z2',
    'norwegian_4x4': 'hard',
    'threshold_3x8': 'hard',
    'vo2max_intervals': 'hard',
    'cadence_drills': 'z2',
    'hybrid_endurance': 'z2',
    'other': ''
};

function getDayTypeLabel(dayType) {
    return DAY_TYPE_LABELS[dayType] || dayType || 'Unknown';
}

function getDayTypeClass(dayType) {
    return DAY_TYPE_CLASSES[dayType] || '';
}

// ============== Initialize Delete Confirm Button ==============
document.addEventListener('DOMContentLoaded', function() {
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function() {
            if (deleteType === 'workout' && deleteId) {
                deleteWorkout(deleteId);
            } else if (deleteType === 'readiness' && deleteId) {
                deleteReadiness(deleteId);
            }
        });
    }
});

// Export for global use
window.showToast = showToast;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.showConfirmModal = showConfirmModal;
window.closeConfirmModal = closeConfirmModal;
window.openDayViewModal = openDayViewModal;
window.closeDayViewModal = closeDayViewModal;
window.openEditWorkoutModal = openEditWorkoutModal;
window.closeEditModal = closeEditModal;
window.saveEditedWorkout = saveEditedWorkout;
window.openEditReadinessModal = openEditReadinessModal;
window.closeEditReadinessModal = closeEditReadinessModal;
window.saveEditedReadiness = saveEditedReadiness;
window.closeReviewModal = closeReviewModal;
window.skipReviewAndSave = skipReviewAndSave;
window.saveReviewedData = saveReviewedData;
window.getDayTypeLabel = getDayTypeLabel;
window.getDayTypeClass = getDayTypeClass;

