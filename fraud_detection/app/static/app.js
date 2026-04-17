const fmtINR = (v) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(v);
const fmtPerc = (v) => `${v.toFixed(1)}%`;
const fmtTime = () => `[${new Date().toLocaleTimeString('en-IN', { hour12: false })}]`;
const appendLog = (msg) => { const logs = document.getElementById('forensic-logs'); if (!logs) return; logs.innerHTML = `<div class="log-entry"><span class="log-timestamp">${fmtTime()}</span> <span class="log-msg">${msg}</span></div>` + logs.innerHTML; };

let riskChart = null;

const riskStatus = (score) => {
    if (score >= 70) return 'status-danger';
    if (score >= 40) return 'status-warning';
    return 'status-safe';
};



// --- Zoom Earth Integration ---
function generateZoomEarthUrl(lat, lon, dateStr) {
    const d = new Date(dateStr);
    const datePart = d.toISOString().split('T')[0];
    const timePart = d.getUTCHours().toString().padStart(2, '0') + ':' + d.getUTCMinutes().toString().padStart(2, '0');
    return `https://zoom.earth/maps/precipitation/#view=${lat.toFixed(4)},${lon.toFixed(4)},10z/model=icon/date=${datePart},${timePart},+5.5`;
}

// =====================================================

function updateSatellitePanel(oracle, processedAt) {
    const coords = document.getElementById('orbit-coords');
    const status = document.getElementById('orbit-status');
    const time = document.getElementById('orbit-time');
    const link = document.getElementById('satellite-link');
    if (!coords || !link) return;
    coords.innerText = `${oracle.latitude.toFixed(3)}, ${oracle.longitude.toFixed(3)}`;
    status.innerText = 'ORBITAL LOCK';
    time.innerText = `VERDICT: ${new Date(processedAt).toLocaleTimeString('en-IN')}`;
    link.href = generateZoomEarthUrl(oracle.latitude, oracle.longitude, processedAt);
}

async function updateDashboard() {
    const data = await fetch('/api/dashboard').then(r => r.json());
    const metricCards = document.getElementById('metric-cards');
    if (!metricCards) return;

    metricCards.innerHTML = `
        <div class="panel metric-card">
            <div class="metric-label">FORENSIC RISK SCORE</div>
            <div class="metric-value"><span class="status-indicator ${riskStatus(data.real_time_risk_score)}"></span>${data.real_time_risk_score}</div>
        </div>
        <div class="panel metric-card">
            <div class="metric-label">LOCAL VOLATILITY</div>
            <div class="metric-value" style="color: var(--neon-teal);">${data.local_volatility}</div>
        </div>
        <div class="panel metric-card">
            <div class="metric-label">TRAFFIC DENSITY</div>
            <div class="metric-value" style="color: var(--neon-amber);">${data.traffic_density}%</div>
        </div>
        <div class="panel metric-card">
            <div class="metric-label">PAYOUT EXPOSURE</div>
            <div class="metric-value">${fmtINR(data.payout_exposure_inr)}</div>
        </div>
    `;

    renderChart(data.risk_trend);

    const claims = await fetch('/api/claims').then(r => r.json());
    if (claims.length > 0) {
        updateSatellitePanel(claims[0].oracle, claims[0].processed_at);
    }
}

function renderChart(trend) {
    const ctx = document.getElementById('riskChart');
    if (!ctx) return;
    if (riskChart) riskChart.destroy();
    riskChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trend.map((_, i) => `T-${trend.length - i}`),
            datasets: [{
                label: 'Risk Telemetry', data: trend,
                borderColor: '#FFBF00', backgroundColor: 'rgba(255, 191, 0, 0.1)',
                borderWidth: 2, pointRadius: 0, tension: 0.4, fill: true
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#888', font: { family: 'DM Mono', size: 10 } } }
            }
        }
    });
}

async function updateDrivers() {
    const rows = document.getElementById('driver-rows');
    if (!rows) return;
    const drivers = await fetch('/api/drivers').then(r => r.json());
    rows.innerHTML = drivers.map(d => `
        <tr>
            <td>${d.driver_id}</td>
            <td>${d.display_name}</td>
            <td>${d.strikes} / 3</td>
            <td>${d.forensic_history_score}%</td>
            <td style="color: ${d.restricted ? 'var(--neon-crimson)' : 'var(--neon-teal)'}">
                ${d.restricted ? 'RESTRICTED' : 'ACTIVE'}
            </td>
        </tr>
    `).join('');
}

async function updateClaims() {
    const rows = document.getElementById('claim-rows');
    if (!rows) return;
    const claims = await fetch('/api/claims').then(r => r.json());
    rows.innerHTML = claims.map(c => {
        const satelliteLink = generateZoomEarthUrl(c.oracle.latitude, c.oracle.longitude, c.processed_at);
        return `
        <tr>
            <td>${c.claim_id}</td>
            <td>${c.driver_id}</td>
            <td style="color: ${c.status === 'APPROVED' ? 'var(--neon-teal)' : 'var(--neon-crimson)'}">
                ${c.status}
            </td>
            <td>${c.oracle.observed_condition}</td>
            <td style="color: var(--neon-amber);">${c.oracle.social_disruption_score}%</td>
            <td style="color: var(--neon-teal);">${c.oracle.traffic_congestion_score}%</td>
            <td>
                <a href="${satelliteLink}" target="_blank" style="color: var(--neon-amber); text-decoration: none; font-size: 0.75rem;">🛰️ UPLINK</a>
            </td>
            <td style="font-family: 'DM Mono';">${fmtINR(c.payout_inr)}</td>
        </tr>
    `}).join('');
}

async function bindClaimForm() {
    const form = document.getElementById('claim-form');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const output = document.getElementById('claim-output');
        if (!window.currentGPS) {
            output.innerHTML = `<span style="color: var(--neon-crimson)">GPS DENIED: Hardware location lock is strictly required. Please allow access and reload.</span>`;
            return;
        }

        output.innerHTML = '<span style="color: var(--neon-amber);">⏳ INITIATING CONSENSUS ENGINE...</span>';

        const payload = Object.fromEntries(new FormData(form).entries());
        payload.location_query = `${window.currentGPS.lat}, ${window.currentGPS.lon}`; // Hardware coordinates
        payload.telemetry = {
            latitude: window.currentGPS.lat,
            longitude: window.currentGPS.lon,
            altitude: window.currentGPS.alt,
            accuracy: window.currentGPS.acc,
            altitudeAccuracy: window.currentGPS.altAcc,
            heading: window.currentGPS.heading,
            speed: window.currentGPS.speed,
            timestamp: window.currentGPS.timestamp
        };
        payload.is_webdriver = navigator.webdriver || false;
        
        const photoInput = document.getElementById('photo-upload');
        if (photoInput && photoInput.files.length > 0) {
            const file = photoInput.files[0];
            const reader = new FileReader();
            payload.photo_b64 = await new Promise((resolve) => {
                reader.onload = () => resolve(reader.result.split(',')[1]);
                reader.readAsDataURL(file);
            });
        }

        try {
            const response = await fetch('/api/claims/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const err = await response.json();
                output.innerHTML = `<span style="color: var(--neon-crimson)">${err.detail}</span>`;
                return;
            }

            const decision = await response.json();
            const isApproved = decision.status === 'APPROVED';
            output.innerHTML = `<span style="color: ${isApproved ? 'var(--neon-teal)' : 'var(--neon-crimson)'}">${decision.status}</span>: ${decision.reason} | Payout: ${fmtINR(decision.payout_inr)}`;

            appendLog(`VERDICT: ${decision.claim_id} — ${decision.status} — ${fmtINR(decision.payout_inr)} — Strikes: ${decision.strikes_after_decision}/3`);

            // Verdict ledger card (claims page only)
            const ledger = document.getElementById('verdict-ledger');
            if (ledger) {
                const cls = isApproved ? 'approved' : 'denied';
                const color = isApproved ? 'var(--neon-teal)' : 'var(--neon-crimson)';
                const restricted = decision.restricted ? ' ⛔ RESTRICTED' : '';
                ledger.innerHTML = `
                    <div class="verdict-entry ${cls}">
                        <div class="verdict-id">${decision.claim_id} • ${new Date(decision.processed_at).toLocaleTimeString('en-IN')}</div>
                        <div class="verdict-status" style="color: ${color}">${decision.status}</div>
                        <div class="verdict-reason">${decision.reason}</div>
                        <div class="verdict-payout">${fmtINR(decision.payout_inr)} • Strikes: ${decision.strikes_after_decision}/3${restricted}</div>
                    </div>
                ` + (ledger.querySelector('.verdict-entry') ? ledger.innerHTML : '');
            }

            await Promise.all([updateDashboard(), updateDrivers(), updateClaims()]);
            updateSatellitePanel(decision.oracle, decision.processed_at);

        } catch (err) {
            output.innerHTML = `<span style="color: var(--neon-crimson)">SYSTEM ERROR: Oracle timeout.</span>`;
        }
    });
}

async function loadPolicy() {
    const container = document.getElementById('policy-content');
    if (!container) return;
    const policy = await fetch('/api/policy').then(r => r.json());

    container.innerHTML = `
        <div class="panel">
            <h3 style="color: var(--neon-teal); margin-bottom: 20px;">Payout Matrix (₹ INR)</h3>
            <ul style="list-style: none; font-family: 'DM Mono'; font-size: 0.9rem;">
                ${Object.entries(policy.payout_rules).map(([k, v]) => `
                    <li style="margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 5px;">
                        ${k.toUpperCase()}: <span style="float: right; color: var(--neon-amber);">${fmtINR(v)}/HR</span>
                    </li>
                `).join('')}
            </ul>
        </div>
        <div class="panel">
            <h3 style="color: var(--neon-amber); margin-bottom: 20px;">Strike Policy</h3>
            ${policy.strike_policy.map(r => `
                <div style="margin-bottom: 15px;">
                    <strong style="color: #FFF; font-size: 0.8rem;">${r.title}</strong><br>
                    <small style="color: var(--text-muted); font-size: 0.75rem;">${r.detail}</small>
                </div>
            `).join('')}
        </div>
        <div class="panel">
            <h3 style="color: var(--neon-crimson); margin-bottom: 20px;">Consensus Logic</h3>
            ${policy.consensus_description.map(r => `
                <div style="margin-bottom: 15px;">
                    <strong style="color: #FFF; font-size: 0.8rem;">${r.title}</strong><br>
                    <small style="color: var(--text-muted); font-size: 0.75rem;">${r.detail}</small>
                </div>
            `).join('')}
        </div>
    `;
}



window.currentGPS = null;

async function runRealtimeScan(lat, lon) {
    const panel = document.getElementById('oracle-scan-panel');
    const spinner = document.getElementById('scan-spinner');
    const results = document.getElementById('scan-results');
    if (!panel) return;
    panel.style.display = 'block';
    if (spinner) spinner.style.display = 'block';
    if (results) results.style.display = 'none';
    try {
        const query = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
        const data = await fetch(`/api/realtime/scan?location=${encodeURIComponent(query)}`).then(r => r.json());
        if (spinner) spinner.style.display = 'none';
        if (results) results.style.display = 'block';
        const set = (id, val) => { const el = document.getElementById(id); if(el) el.innerText = val; };
        set('scan-location', `${data.latitude}, ${data.longitude}`);
        set('scan-precip', `${data.precipitation_mm} mm`);
        set('scan-wind', `${data.wind_speed_kmh} km/h`);
        set('scan-condition', data.detected_condition);
        set('scan-social', `${data.social_disruption_score}%`);
        set('scan-traffic', `${data.traffic_congestion_score}%`);
        set('scan-payout', data.estimated_payout_inr > 0 ? fmtINR(data.estimated_payout_inr) + ' /hr' : 'N/A');
        const badgeEl = document.getElementById('scan-can-claim');
        if (badgeEl) {
            badgeEl.innerHTML = data.can_claim
                ? `<span class="can-claim-badge yes">✓ CLAIMABLE</span>`
                : `<span class="can-claim-badge no">✗ NO EVENT</span>`;
        }
        // Auto-select best category suggestion
        const catEl = document.getElementById('input-category');
        if (catEl && data.recommended_claim_condition) {
            if (data.detected_condition.toLowerCase().includes('rain')) catEl.value = 'Extreme Rain Alert';
        }
        appendLog(`ORACLE SCAN: ${data.detected_condition} detected at (${lat.toFixed(3)}, ${lon.toFixed(3)}). Precip: ${data.precipitation_mm}mm, Wind: ${data.wind_speed_kmh}km/h.`);
    } catch (err) {
        if (spinner) spinner.innerText = '❌ Oracle scan failed. Submit claim to force re-scan.';
        appendLog(`ORACLE ERROR: Realtime scan failed — ${err.message}`);
    }
}

async function initializeGPS() {
    const statusEl = document.getElementById('gps-status-display');
    if (!statusEl) return;
    
    if (!navigator.geolocation) {
        statusEl.innerHTML = `❌ HARDWARE INCOMPATIBLE`;
        statusEl.style.color = 'var(--neon-crimson)';
        appendLog('GPS ERROR: navigator.geolocation not supported on this hardware.');
        return;
    }
    appendLog('GPS: Acquiring satellite lock...');
    
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            window.currentGPS = {
                lat: pos.coords.latitude,
                lon: pos.coords.longitude,
                acc: pos.coords.accuracy,
                alt: pos.coords.altitude,
                altAcc: pos.coords.altitudeAccuracy,
                heading: pos.coords.heading,
                speed: pos.coords.speed,
                timestamp: pos.timestamp
            };
            statusEl.innerHTML = `✅ ACTIVE LOCK: ${window.currentGPS.lat.toFixed(5)}, ${window.currentGPS.lon.toFixed(5)}`;
            statusEl.style.color = 'var(--neon-teal)';
            appendLog(`GPS: Lock acquired — (${window.currentGPS.lat.toFixed(5)}, ${window.currentGPS.lon.toFixed(5)}), accuracy ±${window.currentGPS.acc?.toFixed(0)}m`);
            runRealtimeScan(window.currentGPS.lat, window.currentGPS.lon);
        },
        (err) => {
            statusEl.innerHTML = `❌ GPS DENIED: ${err.message}`;
            statusEl.style.color = 'var(--neon-crimson)';
            appendLog(`GPS ERROR: ${err.message}`);
        },
        { enableHighAccuracy: true, timeout: 15000 }
    );
}

window.addEventListener('DOMContentLoaded', async () => {
    initializeGPS();
    await updateDashboard();
    await updateDrivers();
    await updateClaims();
    await loadPolicy();
    await bindClaimForm();
});
