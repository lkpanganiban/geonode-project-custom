(function() {
    'use strict';

    // ============================================================
    // Configuration
    // ============================================================
    const METRO_MANILA_CENTER = [121.03, 14.58];
    const METRO_MANILA_BOUNDS = {
        latMin: 14.45,
        latMax: 14.75,
        lonMin: 120.95,
        lonMax: 121.15
    };

    // ============================================================
    // Random Data Generators
    // ============================================================
    function randFloat(min, max) {
        return Math.random() * (max - min) + min;
    }

    function randInt(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    function pick(arr) {
        return arr[Math.floor(Math.random() * arr.length)];
    }

    function randomDate(start, end) {
        const d = new Date(start.getTime() + Math.random() * (end.getTime() - start.getTime()));
        return d.toISOString().split('T')[0];
    }

    function generateProperties(type) {
        const names = ['Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo', 'Foxtrot', 'Golf', 'Hotel', 'India', 'Juliet', 'Kilo', 'Lima', 'Mike', 'November', 'Oscar'];
        const categories = ['Residential', 'Commercial', 'Industrial', 'Government', 'Park', 'Transport'];
        const statuses = ['Active', 'Pending', 'Under Review', 'Completed', 'Archived'];
        return {
            id: Math.random().toString(36).substr(2, 9),
            name: pick(names) + ' ' + type + ' ' + randInt(1, 99),
            type: type,
            category: pick(categories),
            value: randInt(10000, 999999),
            status: pick(statuses),
            date: randomDate(new Date(2020, 0, 1), new Date()),
            description: 'Randomly generated feature in Metro Manila area.'
        };
    }

    function generateRandomPoint() {
        return {
            type: 'Feature',
            geometry: {
                type: 'Point',
                coordinates: [
                    randFloat(METRO_MANILA_BOUNDS.lonMin, METRO_MANILA_BOUNDS.lonMax),
                    randFloat(METRO_MANILA_BOUNDS.latMin, METRO_MANILA_BOUNDS.latMax)
                ]
            },
            properties: generateProperties('Point')
        };
    }

    function generateRandomPolygon() {
        const centerLon = randFloat(METRO_MANILA_BOUNDS.lonMin, METRO_MANILA_BOUNDS.lonMax);
        const centerLat = randFloat(METRO_MANILA_BOUNDS.latMin, METRO_MANILA_BOUNDS.latMax);
        const numVertices = randInt(4, 6);
        const radius = 0.008 + Math.random() * 0.012;
        const coordinates = [];
        for (let i = 0; i < numVertices; i++) {
            const angle = (i / numVertices) * 2 * Math.PI + randFloat(-0.3, 0.3);
            coordinates.push([
                centerLon + Math.cos(angle) * radius * (0.7 + Math.random() * 0.6),
                centerLat + Math.sin(angle) * radius * (0.7 + Math.random() * 0.6)
            ]);
        }
        coordinates.push(coordinates[0]);
        return {
            type: 'Feature',
            geometry: {
                type: 'Polygon',
                coordinates: [coordinates]
            },
            properties: generateProperties('Polygon')
        };
    }

    const pointsGeoJSON = {
        type: 'FeatureCollection',
        features: Array.from({ length: 10 }, generateRandomPoint)
    };

    const polygonsGeoJSON = {
        type: 'FeatureCollection',
        features: Array.from({ length: 5 }, generateRandomPolygon)
    };

    // ============================================================
    // State
    // ============================================================
    let map;
    let selectedFeatures = [];
    let measureMode = null; // 'line' | 'area' | null
    let measurePoints = [];
    let measureGeoJSON = {
        type: 'FeatureCollection',
        features: []
    };
    let isBoxSelecting = false;
    let boxStart = null;
    let boxOverlay = null;
    let currentPage = 0;

    // ============================================================
    // Map Initialization
    // ============================================================
    function initMap() {
        map = new maplibregl.Map({
            container: 'map',
            style: {
                version: 8,
                sources: {
                    'osm': {
                        type: 'raster',
                        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                        tileSize: 256,
                        attribution: '&copy; OpenStreetMap Contributors'
                    }
                },
                layers: [{
                    id: 'osm-layer',
                    type: 'raster',
                    source: 'osm',
                    minzoom: 0,
                    maxzoom: 22
                }]
            },
            center: METRO_MANILA_CENTER,
            zoom: 12,
            maxZoom: 18,
            minZoom: 10
        });

        map.addControl(new maplibregl.NavigationControl(), 'top-right');
        map.addControl(new maplibregl.FullscreenControl(), 'top-right');
        map.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: 'metric' }), 'bottom-left');

        // Disable default box zoom to allow shift+drag selection
        map.boxZoom.disable();

        map.on('load', function() {
            addDataLayers();
            setupInteractions();
            setupGeocode();
            setupLayerToggles();
            setupMeasureTools();
            setupSelectionTools();
        });
    }

    function addDataLayers() {
        // Points source & layers
        map.addSource('points-source', {
            type: 'geojson',
            data: pointsGeoJSON
        });

        map.addLayer({
            id: 'points-layer',
            type: 'circle',
            source: 'points-source',
            paint: {
                'circle-radius': 8,
                'circle-color': '#0d6efd',
                'circle-stroke-color': '#ffffff',
                'circle-stroke-width': 2
            }
        });

        map.addLayer({
            id: 'points-selected',
            type: 'circle',
            source: 'points-source',
            filter: ['in', ['get', 'id'], ['literal', []]],
            paint: {
                'circle-radius': 12,
                'circle-color': '#ffc107',
                'circle-stroke-color': '#ffffff',
                'circle-stroke-width': 3
            }
        });

        map.addLayer({
            id: 'points-active',
            type: 'circle',
            source: 'points-source',
            filter: ['==', ['get', 'id'], ''],
            paint: {
                'circle-radius': 14,
                'circle-color': '#dc3545',
                'circle-stroke-color': '#ffffff',
                'circle-stroke-width': 3
            }
        });

        // Polygons source & layers
        map.addSource('polygons-source', {
            type: 'geojson',
            data: polygonsGeoJSON
        });

        map.addLayer({
            id: 'polygons-layer',
            type: 'fill',
            source: 'polygons-source',
            paint: {
                'fill-color': '#198754',
                'fill-opacity': 0.4
            }
        });

        map.addLayer({
            id: 'polygons-outline',
            type: 'line',
            source: 'polygons-source',
            paint: {
                'line-color': '#198754',
                'line-width': 2
            }
        });

        map.addLayer({
            id: 'polygons-selected',
            type: 'fill',
            source: 'polygons-source',
            filter: ['in', ['get', 'id'], ['literal', []]],
            paint: {
                'fill-color': '#ffc107',
                'fill-opacity': 0.6
            }
        });

        map.addLayer({
            id: 'polygons-selected-outline',
            type: 'line',
            source: 'polygons-source',
            filter: ['in', ['get', 'id'], ['literal', []]],
            paint: {
                'line-color': '#ffc107',
                'line-width': 3
            }
        });

        map.addLayer({
            id: 'polygons-active',
            type: 'fill',
            source: 'polygons-source',
            filter: ['==', ['get', 'id'], ''],
            paint: {
                'fill-color': '#dc3545',
                'fill-opacity': 0.5
            }
        });

        map.addLayer({
            id: 'polygons-active-outline',
            type: 'line',
            source: 'polygons-source',
            filter: ['==', ['get', 'id'], ''],
            paint: {
                'line-color': '#dc3545',
                'line-width': 4
            }
        });

        // Measure source & layers
        map.addSource('measure-source', {
            type: 'geojson',
            data: measureGeoJSON
        });

        map.addLayer({
            id: 'measure-line',
            type: 'line',
            source: 'measure-source',
            filter: ['==', ['get', 'type'], 'line'],
            paint: {
                'line-color': '#dc3545',
                'line-width': 3,
                'line-dasharray': [4, 2]
            }
        });

        map.addLayer({
            id: 'measure-fill',
            type: 'fill',
            source: 'measure-source',
            filter: ['==', ['get', 'type'], 'area'],
            paint: {
                'fill-color': '#dc3545',
                'fill-opacity': 0.2
            }
        });

        map.addLayer({
            id: 'measure-fill-outline',
            type: 'line',
            source: 'measure-source',
            filter: ['==', ['get', 'type'], 'area'],
            paint: {
                'line-color': '#dc3545',
                'line-width': 2,
                'line-dasharray': [4, 2]
            }
        });

        map.addLayer({
            id: 'measure-points',
            type: 'circle',
            source: 'measure-source',
            filter: ['==', ['get', 'type'], 'vertex'],
            paint: {
                'circle-radius': 5,
                'circle-color': '#dc3545',
                'circle-stroke-color': '#fff',
                'circle-stroke-width': 2
            }
        });
    }

    // ============================================================
    // Layer Toggles
    // ============================================================
    function setupLayerToggles() {
        document.getElementById('toggle-points').addEventListener('change', function(e) {
            const visibility = e.target.checked ? 'visible' : 'none';
            map.setLayoutProperty('points-layer', 'visibility', visibility);
            map.setLayoutProperty('points-selected', 'visibility', visibility);
            map.setLayoutProperty('points-active', 'visibility', visibility);
        });

        document.getElementById('toggle-polygons').addEventListener('change', function(e) {
            const visibility = e.target.checked ? 'visible' : 'none';
            map.setLayoutProperty('polygons-layer', 'visibility', visibility);
            map.setLayoutProperty('polygons-outline', 'visibility', visibility);
            map.setLayoutProperty('polygons-selected', 'visibility', visibility);
            map.setLayoutProperty('polygons-selected-outline', 'visibility', visibility);
            map.setLayoutProperty('polygons-active', 'visibility', visibility);
            map.setLayoutProperty('polygons-active-outline', 'visibility', visibility);
        });
    }

    // ============================================================
    // Geocode (Nominatim)
    // ============================================================
    function setupGeocode() {
        const input = document.getElementById('geocode-input');
        const btn = document.getElementById('btn-geocode');
        const resultsContainer = document.getElementById('geocode-results');

        async function doSearch() {
            const query = input.value.trim();
            if (!query) return;
            try {
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&viewbox=${METRO_MANILA_BOUNDS.lonMin},${METRO_MANILA_BOUNDS.latMax},${METRO_MANILA_BOUNDS.lonMax},${METRO_MANILA_BOUNDS.latMin}&bounded=1`);
                const data = await res.json();
                resultsContainer.innerHTML = '';
                if (data.length === 0) {
                    resultsContainer.innerHTML = '<div class="geocode-result-item">No results found</div>';
                } else {
                    data.slice(0, 5).forEach(function(item) {
                        const div = document.createElement('div');
                        div.className = 'geocode-result-item';
                        div.textContent = item.display_name;
                        div.addEventListener('click', function() {
                            const lon = parseFloat(item.lon);
                            const lat = parseFloat(item.lat);
                            map.flyTo({ center: [lon, lat], zoom: 15 });
                            resultsContainer.style.display = 'none';
                        });
                        resultsContainer.appendChild(div);
                    });
                }
                resultsContainer.style.display = 'block';
            } catch (err) {
                console.error('Geocode error:', err);
            }
        }

        btn.addEventListener('click', doSearch);
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') doSearch();
        });

        document.addEventListener('click', function(e) {
            if (!document.getElementById('map-tools-overlay').contains(e.target)) {
                resultsContainer.style.display = 'none';
            }
        });
    }

    // ============================================================
    // Measure Tools
    // ============================================================
    function setupMeasureTools() {
        const btnLine = document.getElementById('btn-measure-line');
        const btnArea = document.getElementById('btn-measure-area');
        const btnClear = document.getElementById('btn-clear-measure');
        const resultDiv = document.getElementById('measure-result');

        function setActiveBtn(btn) {
            [btnLine, btnArea].forEach(function(b) { b.classList.remove('active'); });
            if (btn) btn.classList.add('active');
        }

        function startMeasure(mode) {
            measureMode = mode;
            measurePoints = [];
            updateMeasureSource();
            resultDiv.classList.remove('visible');
            resultDiv.textContent = '';
            map.getCanvas().style.cursor = 'crosshair';
        }

        btnLine.addEventListener('click', function() {
            if (measureMode === 'line') {
                measureMode = null;
                setActiveBtn(null);
                map.getCanvas().style.cursor = '';
            } else {
                setActiveBtn(btnLine);
                startMeasure('line');
            }
        });

        btnArea.addEventListener('click', function() {
            if (measureMode === 'area') {
                measureMode = null;
                setActiveBtn(null);
                map.getCanvas().style.cursor = '';
            } else {
                setActiveBtn(btnArea);
                startMeasure('area');
            }
        });

        btnClear.addEventListener('click', function() {
            measureMode = null;
            measurePoints = [];
            updateMeasureSource();
            setActiveBtn(null);
            resultDiv.classList.remove('visible');
            resultDiv.textContent = '';
            map.getCanvas().style.cursor = '';
        });

        map.on('click', function(e) {
            if (!measureMode) return;
            measurePoints.push([e.lngLat.lng, e.lngLat.lat]);
            updateMeasureSource();
            if (measureMode === 'line' && measurePoints.length > 1) {
                const line = turf.lineString(measurePoints);
                const len = turf.length(line, { units: 'kilometers' });
                resultDiv.textContent = 'Distance: ' + len.toFixed(3) + ' km';
                resultDiv.classList.add('visible');
            }
        });

        map.on('dblclick', function(e) {
            if (!measureMode) return;
            e.preventDefault();
            if (measureMode === 'area' && measurePoints.length >= 3) {
                const coords = measurePoints.slice();
                if (coords[0][0] !== coords[coords.length - 1][0] || coords[0][1] !== coords[coords.length - 1][1]) {
                    coords.push(coords[0]);
                }
                const poly = turf.polygon([coords]);
                const area = turf.area(poly);
                resultDiv.textContent = 'Area: ' + (area / 10000).toFixed(4) + ' ha (' + area.toFixed(2) + ' m²)';
                resultDiv.classList.add('visible');
            }
            measureMode = null;
            setActiveBtn(null);
            map.getCanvas().style.cursor = '';
        });
    }

    function updateMeasureSource() {
        const features = [];
        measurePoints.forEach(function(pt) {
            features.push({
                type: 'Feature',
                geometry: { type: 'Point', coordinates: pt },
                properties: { type: 'vertex' }
            });
        });
        if (measurePoints.length > 1) {
            features.push({
                type: 'Feature',
                geometry: { type: 'LineString', coordinates: measurePoints },
                properties: { type: 'line' }
            });
        }
        if (measurePoints.length > 2) {
            const coords = measurePoints.slice();
            if (coords[0][0] !== coords[coords.length - 1][0] || coords[0][1] !== coords[coords.length - 1][1]) {
                coords.push(coords[0]);
            }
            features.push({
                type: 'Feature',
                geometry: { type: 'Polygon', coordinates: [coords] },
                properties: { type: 'area' }
            });
        }
        measureGeoJSON.features = features;
        if (map.getSource('measure-source')) {
            map.getSource('measure-source').setData(measureGeoJSON);
        }
    }

    // ============================================================
    // Selection & Identify
    // ============================================================
    function setupInteractions() {
        const hint = document.getElementById('selection-hint');

        // Show hint when shift is pressed
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Shift') hint.classList.remove('hidden');
        });
        document.addEventListener('keyup', function(e) {
            if (e.key === 'Shift') hint.classList.add('hidden');
        });

        // Click identify / shift+click add
        map.on('click', function(e) {
            if (measureMode) return;

            const point = e.point;
            const features = map.queryRenderedFeatures(point, {
                layers: ['points-layer', 'polygons-layer']
            });

            if (features.length === 0) {
                if (!e.originalEvent.shiftKey) {
                    clearSelection();
                }
                return;
            }

            const feature = features[0];
            if (e.originalEvent.shiftKey) {
                toggleFeatureSelection(feature);
            } else {
                selectSingleFeature(feature);
            }
        });

        // Box select with shift+drag
        map.getCanvas().addEventListener('mousedown', function(e) {
            if (e.shiftKey && !measureMode) {
                e.preventDefault();
                isBoxSelecting = true;
                boxStart = { x: e.clientX, y: e.clientY };
                createBoxOverlay(e.clientX, e.clientY);
            }
        });

        document.addEventListener('mousemove', function(e) {
            if (isBoxSelecting) {
                updateBoxOverlay(e.clientX, e.clientY);
            }
        });

        document.addEventListener('mouseup', function(e) {
            if (isBoxSelecting) {
                finishBoxSelect(e.clientX, e.clientY);
            }
        });

        // Change cursor on hover over features
        map.on('mousemove', function(e) {
            const features = map.queryRenderedFeatures(e.point, {
                layers: ['points-layer', 'polygons-layer']
            });
            map.getCanvas().style.cursor = features.length > 0 ? 'pointer' : '';
        });
    }

    function createBoxOverlay(x, y) {
        if (boxOverlay) boxOverlay.remove();
        boxOverlay = document.createElement('div');
        boxOverlay.className = 'box-select-overlay';
        boxOverlay.style.left = x + 'px';
        boxOverlay.style.top = y + 'px';
        boxOverlay.style.width = '0px';
        boxOverlay.style.height = '0px';
        document.body.appendChild(boxOverlay);
    }

    function updateBoxOverlay(x, y) {
        if (!boxOverlay) return;
        const left = Math.min(boxStart.x, x);
        const top = Math.min(boxStart.y, y);
        const width = Math.abs(x - boxStart.x);
        const height = Math.abs(y - boxStart.y);
        boxOverlay.style.left = left + 'px';
        boxOverlay.style.top = top + 'px';
        boxOverlay.style.width = width + 'px';
        boxOverlay.style.height = height + 'px';
    }

    function finishBoxSelect(x, y) {
        isBoxSelecting = false;
        if (!boxOverlay) return;

        const rect = boxOverlay.getBoundingClientRect();
        const mapContainer = map.getContainer().getBoundingClientRect();

        // Calculate coordinates relative to map container
        const minX = Math.max(0, rect.left - mapContainer.left);
        const minY = Math.max(0, rect.top - mapContainer.top);
        const maxX = Math.min(mapContainer.width, rect.right - mapContainer.left);
        const maxY = Math.min(mapContainer.height, rect.bottom - mapContainer.top);

        boxOverlay.remove();
        boxOverlay = null;

        if (maxX - minX < 5 || maxY - minY < 5) return;

        const features = map.queryRenderedFeatures(
            [[minX, minY], [maxX, maxY]],
            { layers: ['points-layer', 'polygons-layer'] }
        );

        const added = [];
        features.forEach(function(f) {
            if (!isFeatureSelected(f)) {
                added.push(f);
            }
        });

        if (added.length > 0) {
            selectedFeatures = selectedFeatures.concat(added);
            currentPage = selectedFeatures.length - added.length;
            updateSelectionDisplay();
        }
    }

    function setupSelectionTools() {
        document.getElementById('btn-clear-selection').addEventListener('click', clearSelection);
    }

    function isFeatureSelected(feature) {
        const id = feature.properties.id;
        return selectedFeatures.some(function(f) { return f.properties.id === id; });
    }

    function toggleFeatureSelection(feature) {
        const id = feature.properties.id;
        const idx = selectedFeatures.findIndex(function(f) { return f.properties.id === id; });
        if (idx >= 0) {
            selectedFeatures.splice(idx, 1);
            if (currentPage >= selectedFeatures.length && selectedFeatures.length > 0) {
                currentPage = selectedFeatures.length - 1;
            }
        } else {
            selectedFeatures.push(feature);
            currentPage = selectedFeatures.length - 1;
        }
        updateSelectionDisplay();
    }

    function selectSingleFeature(feature) {
        selectedFeatures = [feature];
        currentPage = 0;
        updateSelectionDisplay();
    }

    function clearSelection() {
        selectedFeatures = [];
        currentPage = 0;
        updateSelectionDisplay();
    }

    function renderFeatureCard(feature) {
        const p = feature.properties;
        const icon = feature.geometry.type === 'Point' ? 'fa-map-marker' : 'fa-draw-polygon';
        return `
            <div class="feature-card">
                <div class="feature-card-header">
                    <i class="fa ${icon} feature-type-icon"></i>
                    <span>${escapeHtml(p.name)}</span>
                </div>
                <div class="feature-card-body">
                    <div class="attribute-row"><span class="attribute-key">Type</span><span class="attribute-value">${escapeHtml(p.type)}</span></div>
                    <div class="attribute-row"><span class="attribute-key">Category</span><span class="attribute-value">${escapeHtml(p.category)}</span></div>
                    <div class="attribute-row"><span class="attribute-key">Value</span><span class="attribute-value">${Number(p.value).toLocaleString()}</span></div>
                    <div class="attribute-row"><span class="attribute-key">Status</span><span class="attribute-value">${escapeHtml(p.status)}</span></div>
                    <div class="attribute-row"><span class="attribute-key">Date</span><span class="attribute-value">${escapeHtml(p.date)}</span></div>
                    <div class="attribute-row"><span class="attribute-key">ID</span><span class="attribute-value">${escapeHtml(p.id)}</span></div>
                    <div class="attribute-row"><span class="attribute-key">Description</span><span class="attribute-value">${escapeHtml(p.description)}</span></div>
                </div>
            </div>
        `;
    }

    function renderPagination() {
        const total = selectedFeatures.length;
        if (total <= 1) return '';
        const page = currentPage + 1;
        return `
            <div class="feature-pagination">
                <button id="btn-prev-feature" class="pagination-btn" ${currentPage === 0 ? 'disabled' : ''}>
                    <i class="fa fa-chevron-left"></i> Prev
                </button>
                <span class="pagination-counter">${page} / ${total}</span>
                <button id="btn-next-feature" class="pagination-btn" ${currentPage >= total - 1 ? 'disabled' : ''}>
                    Next <i class="fa fa-chevron-right"></i>
                </button>
            </div>
        `;
    }

    function updateSelectionDisplay() {
        // Update map highlights
        const ids = selectedFeatures.map(function(f) { return f.properties.id; });
        map.setFilter('points-selected', ['in', ['get', 'id'], ['literal', ids]]);
        map.setFilter('polygons-selected', ['in', ['get', 'id'], ['literal', ids]]);
        map.setFilter('polygons-selected-outline', ['in', ['get', 'id'], ['literal', ids]]);

        const activeId = selectedFeatures.length > 0 ? selectedFeatures[currentPage].properties.id : '';
        map.setFilter('points-active', ['==', ['get', 'id'], activeId]);
        map.setFilter('polygons-active', ['==', ['get', 'id'], activeId]);
        map.setFilter('polygons-active-outline', ['==', ['get', 'id'], activeId]);

        // Update count badge
        document.getElementById('selection-count').textContent = selectedFeatures.length + ' selected';

        // Update attributes panel
        const container = document.getElementById('attributes-container');
        if (selectedFeatures.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fa fa-mouse-pointer"></i>
                    <p>Click on a feature to view its attributes.</p>
                    <p class="hint">Hold <kbd>Shift</kbd> to select multiple features.</p>
                </div>
            `;
            return;
        }

        // Clamp current page
        if (currentPage >= selectedFeatures.length) {
            currentPage = selectedFeatures.length - 1;
        }
        if (currentPage < 0) {
            currentPage = 0;
        }

        let html = renderPagination();
        html += renderFeatureCard(selectedFeatures[currentPage]);
        container.innerHTML = html;

        // Bind pagination events
        if (selectedFeatures.length > 1) {
            const prevBtn = document.getElementById('btn-prev-feature');
            const nextBtn = document.getElementById('btn-next-feature');
            if (prevBtn) {
                prevBtn.addEventListener('click', function() {
                    if (currentPage > 0) {
                        currentPage--;
                        updateSelectionDisplay();
                    }
                });
            }
            if (nextBtn) {
                nextBtn.addEventListener('click', function() {
                    if (currentPage < selectedFeatures.length - 1) {
                        currentPage++;
                        updateSelectionDisplay();
                    }
                });
            }
        }
    }

    function escapeHtml(text) {
        if (text == null) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    // ============================================================
    // Boot
    // ============================================================
    initMap();
})();
