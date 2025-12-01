/**
 * Zyra Cycle - AI Coach Page JavaScript
 * Handles AI training recommendations
 * 
 * Note: DAY_TYPE_LABELS and DAY_TYPE_CLASSES are defined in cycle_shared.js
 */

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
    // Extract session plan for easier access
    const sessionPlan = rec.session_plan || {};
    const flags = rec.flags || {};
    
    // Day type badge
    const dayTypeBadge = document.getElementById('coachDayTypeBadge');
    if (dayTypeBadge) {
        const dayType = rec.day_type || 'other';
        dayTypeBadge.textContent = DAY_TYPE_LABELS[dayType] || dayType.replace(/_/g, ' ').toUpperCase();
        dayTypeBadge.className = `day-type-badge ${DAY_TYPE_CLASSES[dayType] || ''}`;
    }
    
    // Intensity tag - from session_plan.overall_intensity
    const intensityTag = document.getElementById('coachIntensityTag');
    if (intensityTag) {
        const intensity = sessionPlan.overall_intensity || 'moderate';
        intensityTag.textContent = intensity.replace(/_/g, ' ').toUpperCase();
        intensityTag.className = `intensity-tag ${intensity.replace(/_/g, '-')}`;
    }
    
    // Duration - from session_plan.duration_minutes
    const durationEl = document.getElementById('coachDuration');
    if (durationEl) {
        const duration = sessionPlan.duration_minutes;
        durationEl.textContent = duration ? `${duration} min` : '--';
    }
    
    // Date label
    const dateLabel = document.getElementById('coachDateLabel');
    if (dateLabel) {
        dateLabel.textContent = date;
    }
    
    // Reason/Description - use reason_short
    const reasonEl = document.getElementById('coachReason');
    if (reasonEl) {
        reasonEl.innerHTML = rec.reason_short || '';
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
    
    // Performance targets - from session_plan (Enhanced styling)
    const targetsCard = document.getElementById('coachTargetsCard');
    const targetsGrid = document.getElementById('coachTargetsGrid');
    if (targetsCard && targetsGrid) {
        const targets = [];
        
        // Power target from session_plan
        if (sessionPlan.session_target_power_w_min || sessionPlan.session_target_power_w_max) {
            const powerMin = sessionPlan.session_target_power_w_min || '?';
            const powerMax = sessionPlan.session_target_power_w_max || '?';
            targets.push({ label: 'Power Range', value: `${powerMin}-${powerMax}W`, icon: '⚡', type: 'power' });
        } else if (sessionPlan.expected_avg_power_w) {
            targets.push({ label: 'Target Power', value: `~${sessionPlan.expected_avg_power_w}W`, icon: '⚡', type: 'power' });
        }
        
        // HR target from session_plan
        if (sessionPlan.session_target_hr_bpm_min || sessionPlan.session_target_hr_bpm_max) {
            const hrMin = sessionPlan.session_target_hr_bpm_min || '?';
            const hrMax = sessionPlan.session_target_hr_bpm_max || '?';
            targets.push({ label: 'Heart Rate', value: `${hrMin}-${hrMax} bpm`, icon: '❤️', type: 'hr' });
        } else if (sessionPlan.expected_avg_hr_bpm) {
            targets.push({ label: 'Target HR', value: `~${sessionPlan.expected_avg_hr_bpm} bpm`, icon: '❤️', type: 'hr' });
        }
        
        // Zone info
        if (sessionPlan.primary_zone) {
            targets.push({ label: 'Primary Zone', value: sessionPlan.primary_zone, icon: '🎯', type: 'zone' });
        }
        
        if (targets.length > 0) {
            targetsGrid.innerHTML = targets.map(t => `
                <div class="target-item ${t.type}">
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
    
    // Intervals / Session plan - from session_plan.intervals (Enhanced segment cards)
    const intervalsSection = document.getElementById('coachIntervals');
    const intervalsList = document.getElementById('coachIntervalsList');
    if (intervalsSection && intervalsList) {
        const intervals = sessionPlan.intervals || [];
        if (intervals.length > 0) {
            intervalsList.innerHTML = intervals.map((int, idx) => {
                // Determine segment type for styling
                const kind = (int.kind || 'steady').toLowerCase();
                
                // Get icon based on segment type
                const getSegmentIcon = (type) => {
                    const icons = {
                        'warmup': '🔥',
                        'steady': '🚴',
                        'cooldown': '❄️',
                        'recovery': '💤',
                        'interval': '⚡',
                        'threshold': '⚡',
                        'vo2max': '🔥',
                        'progressive': '📈'
                    };
                    return icons[type] || '🚴';
                };
                
                // Power targets from interval
                let powerStr = '';
                if (int.target_power_w_min || int.target_power_w_max) {
                    const pMin = int.target_power_w_min || '?';
                    const pMax = int.target_power_w_max || '?';
                    powerStr = `${pMin}-${pMax}W`;
                }
                
                // HR targets from interval
                let hrStr = '';
                if (int.target_hr_bpm_min || int.target_hr_bpm_max) {
                    const hMin = int.target_hr_bpm_min || '?';
                    const hMax = int.target_hr_bpm_max || '?';
                    hrStr = `${hMin}-${hMax}`;
                } else if (int.expected_avg_hr_bpm) {
                    hrStr = `~${int.expected_avg_hr_bpm}`;
                }
                
                // Handle repeats structure (for interval blocks like 4x4)
                let durationDisplay = '';
                if (int.repeats && int.work_minutes) {
                    durationDisplay = `${int.repeats}×${int.work_minutes}min`;
                    if (int.rest_minutes) {
                        durationDisplay += ` / ${int.rest_minutes}min rest`;
                    }
                } else if (int.duration_minutes) {
                    durationDisplay = `${int.duration_minutes} min`;
                }
                
                // Zone pill
                const zone = int.target_zone || '';
                const zonePill = zone ? `<span class="zone-pill ${zone.toLowerCase()}">${zone}</span>` : '';
                
                // Segment name
                const segmentName = int.block_name || kind.charAt(0).toUpperCase() + kind.slice(1);
                
                return `
                    <div class="segment-card ${kind}">
                        <div class="segment-number">
                            ${getSegmentIcon(kind)}
                        </div>
                        <div class="segment-content">
                            <div class="segment-header">
                                <span class="segment-name">${segmentName}</span>
                                ${zonePill}
                            </div>
                            ${int.notes ? `<div class="segment-notes">${int.notes}</div>` : ''}
                        </div>
                        <div class="segment-metrics">
                            ${durationDisplay ? `
                                <div class="segment-metric duration">
                                    <span class="segment-metric-icon">⏱️</span>
                                    <span class="segment-metric-value">${durationDisplay}</span>
                                </div>
                            ` : ''}
                            ${hrStr ? `
                                <div class="segment-metric hr">
                                    <span class="segment-metric-icon">❤️</span>
                                    <span class="segment-metric-value">${hrStr} bpm</span>
                                </div>
                            ` : ''}
                            ${powerStr ? `
                                <div class="segment-metric power">
                                    <span class="segment-metric-icon">⚡</span>
                                    <span class="segment-metric-value">${powerStr}</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            }).join('');
            intervalsSection.style.display = 'block';
        } else {
            intervalsSection.style.display = 'none';
        }
    }
    
    // Flags - from rec.flags object
    const flagsEl = document.getElementById('coachFlags');
    if (flagsEl) {
        const flagsList = [];
        if (flags.ok_to_push) flagsList.push({ icon: '💪', text: 'OK to push today', class: 'positive' });
        if (flags.prioritize_sleep) flagsList.push({ icon: '😴', text: 'Prioritize sleep tonight', class: 'caution' });
        if (flags.consider_rest_day) flagsList.push({ icon: '🛌', text: 'Consider a rest day', class: 'rest' });
        if (flags.monitor_hrv) flagsList.push({ icon: '📊', text: 'Monitor HRV closely', class: 'info' });
        if (flags.high_fatigue_detected) flagsList.push({ icon: '⚠️', text: 'High fatigue detected', class: 'warning' });
        
        if (flagsList.length > 0) {
            flagsEl.innerHTML = flagsList.map(f => `
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

