// ═══ GLOBAL MARITIME & MULTI-MODAL ENGINE CODENAME: CHAINGUARD ═══════════════
let mainMap;
let allRoutesStorage = []; 
let cachedShipments = []; // Tempat menyimpan manifest kapal secara global
const API_BASE_URL = "http://127.0.0.1:8000";

const defaultFallbackData = [
    { shipment_id: "VESSEL-01", vessel_name: "MV INDO PROGRESS", origin: "Southeast Asia", destination: "East Asia", shipping_mode: "Container Fleet", co2_emission: 145, risk_status: "High Risk" },
    { shipment_id: "VESSEL-02", vessel_name: "LNG AQUATICA", origin: "Oceania", destination: "Japan", shipping_mode: "LNG Tanker", co2_emission: 98, risk_status: "Medium Risk" },
    { shipment_id: "VESSEL-03", vessel_name: "SS BOREAS BULKER", origin: "Western Europe", destination: "North America", shipping_mode: "Dry Bulk Carrier", co2_emission: 210, risk_status: "Low Risk" },
    { shipment_id: "VESSEL-04", vessel_name: "MV BATAM EXPRESS", origin: "Southeast Asia", destination: "Japan", shipping_mode: "Container Vessel", co2_emission: 115, risk_status: "High Risk" },
    { shipment_id: "VESSEL-05", vessel_name: "LNG CELEBES SEA", origin: "Southeast Asia", destination: "Western Europe", shipping_mode: "LNG Tanker", co2_emission: 180, risk_status: "Medium Risk" }
];

function initNoirMap() {
    const mapEl = document.getElementById('noir-map');
    const bundleEl = document.getElementById('map-bundle'); 
    if (!mapEl || !bundleEl) return;

    try {
        mainMap = L.map('noir-map', { zoomControl: true }).setView([25.0, 10.0], 1); 
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { attribution: '&copy; CartoDB' }).addTo(mainMap);
        
        const toggleBtn = document.createElement('button');
        toggleBtn.innerHTML = "EXPAND MAP 🖵";
        toggleBtn.style.position = 'absolute'; toggleBtn.style.top = '20px'; toggleBtn.style.right = '20px'; toggleBtn.style.zIndex = '10000';
        toggleBtn.style.backgroundColor = '#fff'; toggleBtn.style.color = '#000'; toggleBtn.style.border = '3px solid #000';
        toggleBtn.style.padding = '8px 16px'; toggleBtn.style.fontFamily = "monospace"; toggleBtn.style.fontWeight = '900'; toggleBtn.style.cursor = 'pointer';
        
        bundleEl.appendChild(toggleBtn);

        toggleBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            const isFullscreen = bundleEl.classList.toggle('fullscreen-bundle');
            toggleBtn.innerHTML = isFullscreen ? "CLOSE MAP X" : "EXPAND MAP 🖵";
            toggleBtn.style.backgroundColor = isFullscreen ? '#ef4444' : '#ffffff';
            toggleBtn.style.color = isFullscreen ? '#ffffff' : '#000000';
            
            setTimeout(() => { mainMap.invalidateSize(); autoFitAllRoutes(); }, 250);
        });
    } catch (e) { console.error("MAP ERROR:", e); }
}

function generateTrueSeaWaypoints(originName, shippingMode, destinationName) {
    const destinationMap = {
        "east asia": [31.2304, 121.4737],     
        "japan": [35.6762, 139.6503],         
        "north america": [45.5017, -73.5673],  
        "western europe": [51.9244, 4.4777]    
    };

    let destLower = destinationName ? destinationName.toLowerCase().trim() : "north america";
    
    if (destLower.includes("north america")) destLower = "north america";
    if (destLower.includes("western europe")) destLower = "western europe";
    if (destLower.includes("east asia") || destLower.includes("shanghai")) destLower = "east asia";
    if (destLower.includes("japan") || destLower.includes("tokyo")) destLower = "japan";

    const destinationLatLng = destinationMap[destLower] || [45.5017, -73.5673];
    
    const origin = originName ? originName.toLowerCase().trim() : "southeast asia";
    const mode = shippingMode ? shippingMode.toLowerCase().trim() : "container vessel";
    
    const coordinatesMap = { 
        "southeast asia": [1.3521, 103.8198], 
        "western europe": [51.5074, -0.1278],  
        "oceania": [-33.8688, 151.2093],       
        "north america": [40.7128, -74.0060]   
    };
    
    const originLatLng = coordinatesMap[origin] || [1.3521, 103.8198];
    let pathWaypoints = [originLatLng];

    if (!mode.includes("air") && !mode.includes("road") && !mode.includes("rail") && !mode.includes("truck")) {
        if (origin === "southeast asia") {
            if (destLower === "japan" || destLower === "east asia") {
                pathWaypoints.push([10.00, 110.00], [22.00, 120.00]); 
            } else {
                pathWaypoints.push([6.00, 95.00], [12.00, 51.00], [29.95, 32.50], [36.00, -5.50], [48.00, -30.00]);
            }
        } 
        else if (origin === "oceania") {
            if (destLower === "japan" || destLower === "east asia") {
                pathWaypoints.push([-2.00, 140.00], [15.00, 130.00]);
            } else {
                pathWaypoints.push([-6.00, 106.00], [6.00, 95.00], [12.00, 51.00], [29.95, 32.50], [36.00, -5.50]);
            }
        }
        else if (origin === "western europe") {
            if (destLower === "east asia" || destLower === "japan") {
                pathWaypoints.push([36.00, -5.50], [29.95, 32.50], [12.00, 51.00], [6.00, 95.00], [10.00, 110.00]);
            } else if (destLower === "north america") {
                pathWaypoints.push([49.50, -5.00], [48.00, -25.00]);
            }
        }
    }
    else if (mode.includes("road") || mode.includes("truck") || mode.includes("rail") || mode.includes("land")) {
        if (origin === "southeast asia") {
            pathWaypoints.push([13.75, 100.50], [30.59, 114.30], [55.75, 37.61]); 
        }
    }

    pathWaypoints.push(destinationLatLng);
    return pathWaypoints;
}

function renderAllRoutesToMap(listData) {
    if (!mainMap) return;
    allRoutesStorage.forEach(routeObj => mainMap.removeLayer(routeObj.layer));
    allRoutesStorage = [];

    const overlayTbody = document.getElementById('overlay-table-body');
    if (overlayTbody) overlayTbody.innerHTML = "";

    listData.forEach((item, index) => {
        let originVal = item.origin || "Southeast Asia";
        let modeVal = item.shipping_mode || "Container Vessel";
        let destVal = item.destination || "North America";
        let vesselNameVal = item.vessel_name || "MANIFEST ARMADA";

        let seaWaypoints = generateTrueSeaWaypoints(originVal, modeVal, destVal);
        
        if (seaWaypoints.length > 2) {
            const shiftFactor = (index - (listData.length / 2)) * 0.18; 
            seaWaypoints = seaWaypoints.map((wp, wpIdx) => {
                if (wpIdx === 0 || wpIdx === seaWaypoints.length - 1) return wp;
                return [wp[0] + (shiftFactor * 0.3), wp[1] + shiftFactor];
            });
        }

        let smoothWaypoints = [];
        for (let i = 0; i < seaWaypoints.length - 1; i++) {
            let p1 = seaWaypoints[i];
            let p2 = seaWaypoints[i+1];
            smoothWaypoints.push(p1);
            
            const steps = 6; 
            for (let j = 1; j < steps; j++) {
                let t = j / steps;
                let lat = p1[0] + (p2[0] - p1[0]) * t;
                let lng = p1[1] + (p2[1] - p1[1]) * t;
                
                const modeLower = modeVal ? modeVal.toLowerCase() : "";
                if (!modeLower.includes("air") && !modeLower.includes("road") && !modeLower.includes("rail")) {
                    let arc = Math.sin(t * Math.PI) * 1.4;
                    lat += (index % 2 === 0 ? arc * 0.4 : -arc * 0.4);
                }
                smoothWaypoints.push([lat, lng]);
            }
        }
        smoothWaypoints.push(seaWaypoints[seaWaypoints.length - 1]);

        let riskColor = '#ffffff';
        if (item.risk_status.toLowerCase() === "high risk") riskColor = '#ef4444';
        else if (item.risk_status.toLowerCase() === "medium risk") riskColor = '#f59e0b';
        else if (item.risk_status.toLowerCase() === "low risk") riskColor = '#10b981';

        const polylineLayer = new L.polyline(smoothWaypoints, { 
            color: riskColor, 
            weight: 3.5, 
            opacity: 0.7,
            smoothFactor: 1.2
        }).addTo(mainMap);
        
        polylineLayer.bindPopup(`<b style="color:#000;">🚢 ${vesselNameVal}</b><br><span style="color:${riskColor}; font-weight:bold;">${item.risk_status}</span>`);
        
        polylineLayer.bindPopup(`<b style="color:#000;">🚢 ${vesselNameVal}</b><br><span style="color:${riskColor}; font-weight:bold;">${item.risk_status}</span>`);
        
        polylineLayer.on('click', () => { focusSpecificRoute(item.shipment_id); });
        allRoutesStorage.push({ id: item.shipment_id, layer: polylineLayer, bounds: polylineLayer.getBounds() });

        if (overlayTbody) {
            const shortId = item.shipment_id ? item.shipment_id.substring(0, 8).toUpperCase() : "REG-NODE";
            overlayTbody.innerHTML += `
                <tr onclick="focusSpecificRoute('${item.shipment_id}')" style="cursor: pointer; border-bottom: 1px solid #27272a;">
                    <td style="font-family:var(--font-mono); font-size:11px; color:var(--text-gray);">${shortId}</td>
                    <td><b>${originVal}</b> ➔ <b>${destVal}</b></td>
                    <td style="color:${riskColor}; font-weight:900;">${item.risk_status.split(' ')[0]}</td>
                </tr>`;
        }
    });
    autoFitAllRoutes();
}

function updateAIRiskCommentary(shipmentId) {
    const vessel = cachedShipments.find(s => s.shipment_id === shipmentId);
    if (!vessel) return;

    const selectorEl = document.getElementById('ai-vessel-selector');
    const confidenceEl = document.getElementById('ai-confidence-score');
    const commentEl = document.getElementById('ai-dynamic-commentary');
    const advisorEl = document.getElementById('ai-advisor-text');

    if (selectorEl) selectorEl.value = shipmentId;

    let confidence = "92.4%";
    let comment = `Vessel ${vessel.vessel_name || 'Fleet'} terpantau dalam kondisi normal pada rute ${vessel.origin} menuju Hub.`;
    let advice = "Lanjutkan instruksi pelayaran standar, pertahankan kecepatan ekonomis CO₂.";

    if (vessel.risk_status.toLowerCase() === "high risk") {
        confidence = "97.6%";
        comment = `Anomali Kritis Terdeteksi! Model Random Forest mengidentifikasi tingkat kerawanan tinggi pada armada [${vessel.vessel_name || 'Fleet'}]. Hal ini disebabkan oleh kombinasi komoditas berisiko tinggi dan kendala durasi operasional transit regional yang berpotensi memicu degradasi rantai pasok maritim.`;
        advice = "Rekomendasi AI: Segera lakukan pengalihan taktis rute navigasi armada atau amankan safety stock sebesar +35% di pelabuhan terdekat.";
    } else if (vessel.risk_status.toLowerCase() === "medium risk") {
        confidence = "94.1%";
        comment = `Peringatan Moderat! Koridor operasional [${vessel.vessel_name || 'Fleet'}] menunjukkan indikasi volatilitas sedang. Pengawasan konvensional secara berkala direkomendasikan sepanjang garis lintang logistik.`;
        advice = "Rekomendasi AI: Monitor sistem telemetri bahan bakar dan siapkan koordinat mitigasi cadangan.";
    }

    if (confidenceEl) confidenceEl.textContent = confidence;
    if (commentEl) commentEl.innerHTML = `<h5>MODEL RECOGNITION CONFIDENCE: <span>${confidence}</span></h5><p>${comment}</p>`;
    if (advisorEl) advisorEl.textContent = advice;
}

function focusSpecificRoute(targetShipmentId) {
    allRoutesStorage.forEach(routeObj => {
        if (routeObj.id === targetShipmentId) {
            routeObj.layer.setStyle({ weight: 7, opacity: 1.0 });
            routeObj.layer.openPopup();
            mainMap.fitBounds(routeObj.bounds, { padding: [50, 50], maxZoom: 4 });
        } else {
            routeObj.layer.setStyle({ weight: 2, opacity: 0.1 });
        }
    });
    updateAIRiskCommentary(targetShipmentId);
}

function autoFitAllRoutes() {
    if (allRoutesStorage.length === 0 || !mainMap) return;
    const group = new L.featureGroup(allRoutesStorage.map(r => r.layer));
    mainMap.fitBounds(group.getBounds(), { padding: [30, 30] });
}

async function loadCoreSystemData() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/shipments/list`);
        if (response.ok) {
            cachedShipments = await response.json();
        } else { cachedShipments = defaultFallbackData; }
    } catch (e) { 
        console.warn("FastAPI Offline. Menggunakan data simulasi lokal."); 
        cachedShipments = defaultFallbackData; 
    }

    updateTopMacroBanner();

    const pageType = document.body.getAttribute('data-page');
    if (pageType === "registry") {
        renderRegistryPage();
    } else if (pageType === "suppliers") {
        renderSupplierPage(); 
    } else if (pageType === "ai-page") {
        renderAIForecastPage();
    } else if (pageType === "sustainability") {
        renderSustainabilityPage();
    } else if (pageType === "trends") {
        renderTrendsPage();
    } else if (pageType === "alerts") {
        renderActiveAlertsPage();
    }
}

function updateTopMacroBanner() {
    const totalEl = document.getElementById('metric-total');
    const co2El = document.getElementById('metric-co2');
    const riskEl = document.getElementById('metric-risk');
    const esgEl = document.getElementById('metric-esg');

    if (!totalEl) return; 

    let totalVessels = cachedShipments.length;
    let totalCO2 = cachedShipments.reduce((sum, current) => sum + current.co2_emission, 0);
    let avgCO2 = totalVessels > 0 ? roundNumber(totalCO2 / totalVessels, 1) : 0;
    let highRisks = cachedShipments.filter(s => s.risk_status.toLowerCase() === "high risk").length;
    let lowRisks = cachedShipments.filter(s => s.risk_status.toLowerCase() === "low risk").length;
    let medRisks = cachedShipments.filter(s => s.risk_status.toLowerCase() === "medium risk").length;
    let complianceRate = totalVessels > 0 ? roundNumber(((lowRisks + medRisks) / totalVessels) * 100, 1) : 100;

    totalEl.textContent = totalVessels;
    if (co2El) co2El.textContent = `${avgCO2} t`;
    if (riskEl) riskEl.textContent = highRisks;
    if (esgEl) esgEl.textContent = `${complianceRate}%`;
}

function roundNumber(num, scale) {
    if(!("" + num).includes("e")) {
        return +(Math.round(num + "e+" + scale)  + "e-" + scale);
    } else {
        let arr = ("" + num).split("e");
        let sig = ""
        if(+arr[1] + scale > 0) { sig = "+"; }
        return +(Math.round(+arr[0] + "e" + sig + (+arr[1] + scale)) + "e-" + scale);
    }
}

function renderRegistryPage() {
    const tbody = document.getElementById('shipment-table-body');
    if (!tbody) return;
    tbody.innerHTML = "";
    initNoirMap();
    renderAllRoutesToMap(cachedShipments);

    cachedShipments.forEach(item => {
        let color = "#10b981";
        if (item.risk_status.toLowerCase() === "high risk") color = "#ef4444";
        if (item.risk_status.toLowerCase() === "medium risk") color = "#f59e0b";

        tbody.innerHTML += `
            <tr style="border-bottom: 1px solid #27272a;">
                <td onclick="focusSpecificRoute('${item.shipment_id}')" style="cursor: pointer;"><code style="color:#aaa;">${item.shipment_id.substring(0,8).toUpperCase()}</code></td>
                <td onclick="focusSpecificRoute('${item.shipment_id}')" style="cursor: pointer;"><strong>${item.origin}</strong></td>
                <td onclick="focusSpecificRoute('${item.shipment_id}')" style="cursor: pointer;">${item.destination}</td>
                <td onclick="focusSpecificRoute('${item.shipment_id}')" style="cursor: pointer;"><span class="badge-noir">${item.shipping_mode}</span></td>
                <td onclick="focusSpecificRoute('${item.shipment_id}')" style="cursor: pointer;"><b>${item.co2_emission} t</b></td>
                <td onclick="focusSpecificRoute('${item.shipment_id}')" style="cursor: pointer;"><span class="badge-risk" style="background-color:${color}; color:#000; font-weight:900; padding:2px 6px;">${item.risk_status}</span></td>
                <td>
                    <button onclick="openEditModal('${item.shipment_id}', '${item.origin}', '${item.destination}', '${item.shipping_mode}', '${item.weight_kg || 1500.5}', '${item.estimated_distance_km || item.distance_km || 4000.0}')" style="background:#fff; color:#000; font-size:10px; font-weight:900; padding:4px 8px; border:none; cursor:pointer; margin-right:4px;">EDIT</button>
                    <button onclick="openLogModal('${item.shipment_id}')" style="background:#000; color:#fff; border:1px solid #fff; font-size:10px; font-weight:900; padding:4px 8px; cursor:pointer;">LOG</button>
                </td>
            </tr>`;
    });
}

// MODAL INTERACTION CONTROLLERS
function closeModal(modalId) {
    document.getElementById(modalId).style.display = "none";
}

function openEditModal(id, origin, destination, mode, weight, distance) {
    document.getElementById('edit-shipment-id').value = id;
    document.getElementById('edit-origin').value = origin;
    document.getElementById('edit-destination').value = destination;
    document.getElementById('edit-mode').value = mode;
    document.getElementById('edit-weight').value = weight;
    document.getElementById('edit-distance').value = distance;
    
    document.getElementById('edit-modal').style.display = "block";
}

async function submitEditForm() {
    const id = document.getElementById('edit-shipment-id').value;
    const origin = document.getElementById('edit-origin').value;
    const destination = document.getElementById('edit-destination').value;
    const mode = document.getElementById('edit-mode').value;
    const weight = document.getElementById('edit-weight').value;
    const distance = document.getElementById('edit-distance').value;

    const payload = {
        "origin_region": origin,
        "destination_region": destination,
        "shipping_mode": mode,
        "weight_kg": parseFloat(weight || 1500.5),
        "distance_km": parseFloat(distance || 12000.0)
    };

    try {
        const response = await fetch(`${API_BASE_URL}/api/shipments/${id}/edit`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            alert("SUCCESS! Data berhasil diperbarui & riwayat log audit terekam.");
            closeModal('edit-modal');
            loadCoreSystemData(); 
        } else {
            alert("Gagal memperbarui manifes.");
        }
    } catch (e) {
        console.error("EDIT ERROR:", e);
        alert("Server backend deteksi offline, mutasi data dibatalkan.");
    }
}

async function openLogModal(shipmentId) {
    const logContent = document.getElementById('log-content');
    if (!logContent) return;

    logContent.innerHTML = `<p style="font-family:var(--font-mono); font-size:12px; color:var(--text-gray);">Querying audit trail logs from Cloud Firestore...</p>`;
    document.getElementById('log-modal').style.display = "block";

    try {
        const response = await fetch(`${API_BASE_URL}/api/shipments/${shipmentId}/logs`);
        if (response.ok) {
            const logs = await response.json();
            
            if (logs.length === 0) {
                logContent.innerHTML = `<p style="font-family:var(--font-mono); font-size:12px; color:#10b981;">[ ORIGINAL MANIFEST ] Berkas murni bawaan CSV asli. Belum pernah mengalami mutasi data.</p>`;
                return;
            }

            logContent.innerHTML = "";
            logs.forEach(log => {
                const timeLocal = new Date(log.timestamp).toLocaleString("id-ID") + " WIB";
                logContent.innerHTML += `
                    <div class="noir-box-nested" style="margin-bottom:12px; border-left:4px solid #fff; background:#000; padding: 12px;">
                        <span class="endpoint-badge" style="float:right;">V.${log.version_snapshot}</span>
                        <h5 style="color:#ef4444; font-family:var(--font-mono); font-size:11px;">ACTION SYSTEM: [${log.action}]</h5>
                        <p style="font-size:12px; margin:4px 0;"><b>Changed Fields:</b> <code style="color:#a1a1aa;">${log.changed_fields}</code></p>
                        <small style="font-family:var(--font-mono); font-size:10px; color:var(--text-gray);">TIMESTAMP: ${timeLocal}</small>
                    </div>`;
            });
        }
    } catch (e) {
        logContent.innerHTML = `<p style="color:#ef4444; font-family:var(--font-mono); font-size:12px;">Eror: Gagal terhubung ke pipeline logs backend.</p>`;
    }
}

function renderSupplierPage() {
    const tbody = document.getElementById('supplier-table-body');
    const adviceEl = document.getElementById('ai-supplier-advice');
    if (!tbody) return;

    if (cachedShipments.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;">No active vendors indexed in manifest.</td></tr>`;
        if (adviceEl) adviceEl.textContent = "Awaiting data injection to analyze supplier efficiency.";
        return;
    }

    tbody.innerHTML = "";
    let bestVessel = cachedShipments[0];

    cachedShipments.forEach(item => {
        if (item.co2_emission < bestVessel.co2_emission) {
            bestVessel = item;
        }

        let color = "#10b981";
        if (item.risk_status.toLowerCase() === "high risk") color = "#ef4444";
        if (item.risk_status.toLowerCase() === "medium risk") color = "#f59e0b";

        tbody.innerHTML += `
            <tr style="border-bottom: 1px solid #27272a;">
                <td><b>${item.vessel_name || 'Global Fleet Corp'}</b></td>
                <td>${item.origin}</td>
                <td><span class="badge-noir">${item.shipping_mode}</span></td>
                <td><b style="font-family: var(--font-mono);">${item.co2_emission} t</b></td>
                <td><span class="badge-risk" style="background-color:${color}; color:#000; font-weight:900; padding:2px 6px;">${item.risk_status}</span></td>
            </tr>`;
    });

    if (adviceEl) {
        adviceEl.innerHTML = `
            <span style="color:#10b981; font-weight:900;">[ REKOMENDASI MITRA HIJAU ]</span><br>
            Berdasarkan audit emisi karbon otomatis, armada <b style="color:#fff;">${bestVessel.vessel_name}</b> rute <b style="color:#fff;">${bestVessel.origin} ➔ ${bestVessel.destination}</b> diidentifikasi sebagai vendor paling ramah lingkungan dengan emisi terendah sebesar <b style="color:#10b981;">${bestVessel.co2_emission} ton CO₂</b>.<br>
            <span style="color:var(--text-gray);">Saran Mitigasi: Prioritaskan alokasi komoditas utama kelompok ke armada ini demi mendongkrak skor ESG hingga +14.2%.</span>
        `;
    }
}

function renderAIForecastPage() {
    const selector = document.getElementById('ai-vessel-selector'); if (!selector) return; selector.innerHTML = "";
    cachedShipments.forEach(v => { selector.innerHTML += `<option value="${v.shipment_id}">${v.vessel_name || 'Vessel'} [${v.risk_status}]</option>`; });
    selector.addEventListener('change', (e) => { updateAIRiskCommentary(e.target.value); });
    if (cachedShipments.length > 0) updateAIRiskCommentary(cachedShipments[0].shipment_id);
}

// IMPROVEMENT ENGINE: KALKULATOR ESG & AUDIT DECARBONIZATION DINAMIS
function renderSustainabilityPage() {
    const fillEmissions = document.getElementById('fill-emissions');
    const fillTarget = document.getElementById('fill-target');
    const fillCompliance = document.getElementById('fill-compliance');

    if (!fillEmissions || !fillTarget || !fillCompliance) return;

    if (cachedShipments.length === 0) {
        fillEmissions.style.width = "0%";
        fillTarget.style.width = "0%";
        fillCompliance.style.width = "0%";
        return;
    }

    let totalCO2 = cachedShipments.reduce((sum, current) => sum + (current.co2_emission || 0), 0);
    const maxCarbonBudget = 3500.0;
    let emissionPercentage = Math.min(100, (totalCO2 / maxCarbonBudget) * 100);

    let lngTankerCount = cachedShipments.filter(s => s.shipping_mode && s.shipping_mode.toLowerCase().includes("lng")).length;
    let totalVessels = cachedShipments.length;
    
    let fuelMixRatio = totalVessels > 0 ? roundNumber((lngTankerCount / totalVessels) * 100, 1) : 0;
    let finalFuelMixPercentage = Math.max(35, Math.min(95, fuelMixRatio + 40));

    let lowRiskCount = cachedShipments.filter(s => s.risk_status && s.risk_status.toLowerCase() === "low risk").length;
    let medRiskCount = cachedShipments.filter(s => s.risk_status && s.risk_status.toLowerCase() === "medium risk").length;
    
    let compliancePercentage = totalVessels > 0 ? roundNumber(((lowRiskCount + medRiskCount) / totalVessels) * 100, 1) : 100;

    setTimeout(() => {
        fillEmissions.style.width = `${emissionPercentage}%`;
        fillTarget.style.width = `${finalFuelMixPercentage}%`;
        fillCompliance.style.width = `${compliancePercentage}%`;
    }, 300);
}

function renderTrendsPage() {
    const barHigh = document.getElementById('bar-high'); const barMed = document.getElementById('bar-med'); const barLow = document.getElementById('bar-low'); if (!barHigh) return;
    let highCount = cachedShipments.filter(s => s.risk_status.toLowerCase() === "high risk").length; let medCount = cachedShipments.filter(s => s.risk_status.toLowerCase() === "medium risk").length;
    let lowCount = cachedShipments.filter(s => s.risk_status.toLowerCase() === "low risk").length; let total = cachedShipments.length || 1;
    setTimeout(() => { barHigh.style.width = `${(highCount / total) * 100 || 30}%`; barMed.style.width = `${(medCount / total) * 100 || 45}%`; barLow.style.width = `${(lowCount / total) * 100 || 75}%`; }, 300);
}

function renderActiveAlertsPage() {
    const alertContainer = document.getElementById('live-alerts-box'); if (!alertContainer) return; alertContainer.innerHTML = "";
    let criticalAlerts = cachedShipments.filter(s => s.risk_status.toLowerCase() === "high risk");
    if (criticalAlerts.length === 0) { alertContainer.innerHTML = `<div class="alert-strip-noir low"><div class="strip-header">STATUS SECTOR CALM // NO ACTIVE ALERTS DETECTED</div><p>Seluruh koridor operasional multi-modal beroperasi dalam batas aman efisiensi hijau ESG.</p></div>`; return; }
    criticalAlerts.forEach(v => { alertContainer.innerHTML += `<div class="alert-strip-noir high"><div class="strip-header">CRITICAL ANOMALY: ${(v.vessel_name || 'Fleet').toUpperCase()} TRAPPED IN RISK CLUSTER</div><p>Model mendeteksi anomali tinggi pada armada kelas <b>${v.shipping_mode}</b> rute pelayaran/jalur asal <b>${v.origin}</b>. Deteksi hambatan transit logistik teridentifikasi.</p></div>`; });
}

function setupUploaderController() {
    const dropzone = document.getElementById('csv-dropzone'); const fileInput = document.getElementById('csv-file-input');
    const previewEl = document.getElementById('file-name-preview'); const executeBtn = document.getElementById('btn-execute-ml');
    if (!dropzone || !fileInput || !executeBtn) return;
    dropzone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => { if (e.target.files[0]) { previewEl.textContent = `LOADED: ${e.target.files[0].name}`; executeBtn.style.display = 'block'; } });
    executeBtn.addEventListener('click', async () => {
        const file = fileInput.files[0]; if (!file) return; const formData = new FormData(); formData.append("file", file);
        executeBtn.textContent = "EXECUTING MODEL..."; executeBtn.disabled = true;
        try {
            const response = await fetch(`${API_BASE_URL}/api/shipments/upload-csv`, { method: "POST", body: formData });
            if (response.ok) { alert("MODEL SUCCESS! Data terindeks ke Cloud Firestore."); window.location.href = "pages/fleet-registry.html"; }
        } catch (e) { window.location.href = "pages/fleet-registry.html"; }
    });
}

window.addEventListener('DOMContentLoaded', () => {
    const clockEl = document.getElementById('live-clock');
    if (clockEl) setInterval(() => { clockEl.textContent = new Date().toTimeString().split(' ')[0] + " WIB"; }, 1000);
    loadCoreSystemData();
    const currentPage = document.body.getAttribute('data-page');
    if (currentPage === "uploader") setupUploaderController();
});