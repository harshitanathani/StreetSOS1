const issueTypes = JSON.parse(document.getElementById('issueTypesData').textContent);
const category = document.getElementById('category');
const issueType = document.getElementById('issueType');
const locationType = document.getElementById('locationType');
const scoreEl = document.getElementById('severityScore');
const labelEl = document.getElementById('severityLabel');

const categoryBase = {Road: 6, Drainage: 6, Garbage: 4, Lighting: 3};
const locationWeight = {'Highway':3,'Main Road':2,'Residential Area':1,'Market / Public Area':2,'Other':1};
const issueWeight = {
    'Pothole':2,'Damaged Road':2,'Road Obstruction':1,
    'Overflowing Bin':1,'Illegal Dumping':2,'Uncollected Waste':1,
    'Blocked Drain':2,'Waterlogging':3,'Open Drain':2,
    'Broken Streetlight':1,'Flickering Light':0,'Dark Stretch':2
};

function updateIssueTypes() {
    const items = issueTypes[category.value] || [];
    issueType.innerHTML = '<option value="">Choose issue type</option>' + items.map(x => `<option value="${x}">${x}</option>`).join('');
    issueType.disabled = items.length === 0;
    updateSeverityPreview();
}
function updateSeverityPreview() {
    if (!category.value || !issueType.value || !locationType.value) {
        scoreEl.textContent = '—'; labelEl.textContent = 'Choose issue details'; return;
    }
    let score = (categoryBase[category.value] || 1) + (issueWeight[issueType.value] || 0) + (locationWeight[locationType.value] || 1);
    score = Math.max(1, Math.min(10, score));
    let label = score >= 9 ? 'Critical' : score >= 7 ? 'High' : score >= 4 ? 'Medium' : 'Low';
    scoreEl.textContent = `${score}/10`; labelEl.textContent = `${label} Priority`;
}
category.addEventListener('change', updateIssueTypes);
issueType.addEventListener('change', updateSeverityPreview);
locationType.addEventListener('change', updateSeverityPreview);

const defaultLat = 12.8231, defaultLng = 80.0442;
const map = L.map('map').setView([defaultLat, defaultLng], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'}).addTo(map);
let marker = null;
const latInput = document.getElementById('latitude');
const lngInput = document.getElementById('longitude');
const readout = document.getElementById('locationReadout');

function setLocation(lat, lng) {
    latInput.value = Number(lat).toFixed(7);
    lngInput.value = Number(lng).toFixed(7);
    if (!marker) marker = L.marker([lat, lng]).addTo(map);
    else marker.setLatLng([lat, lng]);
    readout.textContent = `Selected location: ${Number(lat).toFixed(6)}, ${Number(lng).toFixed(6)}`;
}
map.on('click', (e) => setLocation(e.latlng.lat, e.latlng.lng));

document.getElementById('gpsButton').addEventListener('click', function () {
    const button = this;
    if (!navigator.geolocation) { alert('Geolocation is not supported by this browser. Tap the map manually.'); return; }
    button.disabled = true; button.textContent = 'Locating…';
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude, lng = position.coords.longitude;
            setLocation(lat, lng); map.setView([lat, lng], 17);
            button.textContent = 'Location Selected'; button.disabled = false;
        },
        () => { alert('Location permission was unavailable. Tap the map manually.'); button.textContent = 'Use My Location'; button.disabled = false; },
        {enableHighAccuracy: true, timeout: 10000}
    );
});

document.getElementById('complaintForm').addEventListener('submit', (e) => {
    if (!latInput.value || !lngInput.value) { e.preventDefault(); alert('Please select the complaint location using GPS or the map.'); }
});


const issueImage = document.getElementById('issueImage');
if (issueImage) {
    issueImage.addEventListener('change', () => {
        const file = issueImage.files && issueImage.files[0];
        const wrap = document.getElementById('imagePreviewWrap');
        const img = document.getElementById('imagePreview');
        const name = document.getElementById('imageName');
        if (!file || !wrap || !img) return;
        img.src = URL.createObjectURL(file);
        if (name) name.textContent = file.name;
        wrap.classList.remove('d-none');
    });
}
