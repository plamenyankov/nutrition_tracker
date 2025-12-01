/**
 * Zyra Cycle - AI Coach Page JavaScript
 * Handles AI training recommendations
 */

// ============== Day Type Constants ==============
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

// ============== Initialize Coach Page ==============
function initCoachPage() {
    const analyzeBtn = document.getElementById('analyzeBtn');
    const refreshBtn = document.getElementById('coachRefreshBtn');
    
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', function() {
            const date = document.getElementById('coachDate').value;
            fetchCoachRecommendation(date, false);
        });
    }
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            const date = document.getElementById('coachDate').value;
            fetchCoachRecommendation(date, true);
        });
    }
    
    // Quick date buttons
    document.querySelectorAll('.quick-date-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const date = this.dataset.date;
            if (date) {
                document.getElementById('coachDate').value = date;
                fetchCoachRecommendation(date, false);
            }
        });
    });
    
    // Check for date in URL
    const urlParams = new URLSearchParams(window.location.search);
    const dateParam = urlParams.get('date');
    if (dateParam) {
        document.getElementById('coachDate').value = dateParam;
    }
    
    console.log('🧠 Coach page initialized');
}

// ============== Fetch Recommendation ==============
async function fetchCoachRecommendation(date, forceRefresh = false) {
    const loadingEl = document.getElementById('coachLoading');
    const emptyEl = document.getElementById('coachEmpty');
    const contentEl = document.getElementById('coachContent');
    
    if (loadingEl) loadingEl.style.display = 'flex';
    if (emptyEl) emptyEl.style.display = 'none';
    if (contentEl) contentEl.style.display = 'none';
    
    try {
        const url = forceRefresh 
            ? `/cycling-readiness/api/training-recommendation?date=${date}&force=true`
            : `/cycling-readiness/api/training-recommendation?date=${date}`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (loadingEl) loadingEl.style.display = 'none';
        
        if (data.success && data.recommendation) {
            renderCoachRecommendation(data.recommendation, date);
            if (contentEl) contentEl.style.display = 'block';
        } else {
            if (emptyEl) {
                emptyEl.innerHTML = `<i class="fas fa-exclamation-circle"></i><p>${data.error || 'Failed to generate recommendation'}</p>`;
                emptyEl.style.display = 'flex';
            }
        }
    } catch (err) {
        console.error('Error fetching recommendation:', err);
        if (loadingEl) loadingEl.style.display = 'none';
        if (emptyEl) {
            emptyEl.innerHTML = '<i class="fas fa-exclamation-circle"></i><p>Error connecting to AI coach</p>';
            emptyEl.style.display = 'flex';
        }
    }
}

// ============== Render Recommendation ==============
function renderCoachRecommendation(rec, date) {
    // Day type badge
    const dayTypeBadge = document.getElementById('coachDayTypeBadge');
    if (dayTypeBadge) {
        const dayType = rec.day_type || rec.session_type || 'other';
        dayTypeBadge.textContent = DAY_TYPE_LABELS[dayType] || dayType;
        dayTypeBadge.className = `day-type-badge ${DAY_TYPE_CLASSES[dayType] || ''}`;
    }
    
    // Intensity tag
    const intensityTag = document.getElementById('coachIntensityTag');
    if (intensityTag) {
        const intensity = rec.intensity || 'moderate';
        intensityTag.textContent = intensity.toUpperCase();
        intensityTag.className = `intensity-tag ${intensity}`;
    }
    
    // Duration
    const durationEl = document.getElementById('coachDuration');
    if (durationEl) {
        durationEl.textContent = rec.duration_minutes ? `${rec.duration_minutes} min` : rec.duration || '--';
    }
    
    // Date label
    const dateLabel = document.getElementById('coachDateLabel');
    if (dateLabel) {
        dateLabel.textContent = date;
    }
    
    // Reason/Description
    const reasonEl = document.getElementById('coachReason');
    if (reasonEl) {
        reasonEl.innerHTML = rec.reason || rec.description || '';
    }
    
    // Analysis text (Coach Notes v2.5)
    const analysisCard = document.getElementById('coachAnalysisCard');
    const analysisText = document.getElementById('coachAnalysisText');
    if (analysisCard && analysisText) {
        if (rec.analysis_text) {
            analysisText.innerHTML = rec.analysis_text;
            analysisCard.style.display = 'block';
        } else {
            analysisCard.style.display = 'none';
        }
    }
    
    // Performance targets
    const targetsCard = document.getElementById('coachTargetsCard');
    const targetsGrid = document.getElementById('coachTargetsGrid');
    if (targetsCard && targetsGrid) {
        const targets = [];
        
        if (rec.power_target_w) {
            const power = Array.isArray(rec.power_target_w) 
                ? `${rec.power_target_w[0]}-${rec.power_target_w[1]}` 
                : rec.power_target_w;
            targets.push({ label: 'Power', value: `${power}W`, icon: '⚡' });
        }
        
        if (rec.hr_target_bpm) {
            const hr = Array.isArray(rec.hr_target_bpm) 
                ? `${rec.hr_target_bpm[0]}-${rec.hr_target_bpm[1]}` 
                : rec.hr_target_bpm;
            targets.push({ label: 'Heart Rate', value: `${hr} bpm`, icon: '❤️' });
        }
        
        if (rec.cadence_target) {
            const cadence = Array.isArray(rec.cadence_target) 
                ? `${rec.cadence_target[0]}-${rec.cadence_target[1]}` 
                : rec.cadence_target;
            targets.push({ label: 'Cadence', value: `${cadence} rpm`, icon: '🔄' });
        }
        
        if (targets.length > 0) {
            targetsGrid.innerHTML = targets.map(t => `
                <div class="target-item">
                    <span class="target-icon">${t.icon}</span>
                    <span class="target-label">${t.label}</span>
                    <span class="target-value">${t.value}</span>
                </div>
            `).join('');
            targetsCard.style.display = 'block';
        } else {
            targetsCard.style.display = 'none';
        }
    }
    
    // Intervals / Session plan
    const intervalsSection = document.getElementById('coachIntervals');
    const intervalsList = document.getElementById('coachIntervalsList');
    if (intervalsSection && intervalsList) {
        const intervals = rec.structure || rec.intervals || [];
        if (intervals.length > 0) {
            intervalsList.innerHTML = intervals.map((int, idx) => {
                const powerStr = int.power_target_w 
                    ? (Array.isArray(int.power_target_w) ? `${int.power_target_w[0]}-${int.power_target_w[1]}W` : `${int.power_target_w}W`)
                    : '';
                const hrStr = int.hr_target_bpm 
                    ? (Array.isArray(int.hr_target_bpm) ? `${int.hr_target_bpm[0]}-${int.hr_target_bpm[1]} bpm` : `${int.hr_target_bpm} bpm`)
                    : '';
                
                return `
                    <div class="interval-item-enhanced">
                        <div class="interval-number">${idx + 1}</div>
                        <div class="interval-content">
                            <div class="interval-name">${int.block_name || int.name || `Block ${idx + 1}`}</div>
                            <div class="interval-details">
                                ${int.duration_min ? `<span class="interval-duration">${int.duration_min} min</span>` : ''}
                                ${powerStr ? `<span class="interval-power">${powerStr}</span>` : ''}
                                ${hrStr ? `<span class="interval-hr">${hrStr}</span>` : ''}
                            </div>
                            ${int.notes ? `<div class="interval-notes">${int.notes}</div>` : ''}
                        </div>
                    </div>
                `;
            }).join('');
            intervalsSection.style.display = 'block';
        } else {
            intervalsSection.style.display = 'none';
        }
    }
    
    // Flags
    const flagsEl = document.getElementById('coachFlags');
    if (flagsEl) {
        const flags = [];
        if (rec.ok_to_push) flags.push({ icon: '💪', text: 'OK to push today', class: 'positive' });
        if (rec.prioritize_sleep) flags.push({ icon: '😴', text: 'Prioritize sleep tonight', class: 'caution' });
        if (rec.recovery_focus) flags.push({ icon: '🧘', text: 'Focus on recovery', class: 'rest' });
        if (rec.hydration_reminder) flags.push({ icon: '💧', text: 'Stay hydrated', class: 'info' });
        
        if (flags.length > 0) {
            flagsEl.innerHTML = flags.map(f => `
                <div class="rec-flag ${f.class}">
                    <span class="flag-icon">${f.icon}</span>
                    <span class="flag-text">${f.text}</span>
                </div>
            `).join('');
            flagsEl.style.display = 'flex';
        } else {
            flagsEl.style.display = 'none';
        }
    }
}

// Export for global use
window.initCoachPage = initCoachPage;
window.fetchCoachRecommendation = fetchCoachRecommendation;

