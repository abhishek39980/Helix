import React from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet marker icon issue in build
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

// Helper component to center map on new coordinates
function ChangeView({ center }) {
  const map = useMap();
  map.setView(center, map.getZoom());
  return null;
}

export default function MapWidget({ analysis }) {
  if (!analysis) return null;

  // Coordinate parsing helper
  const parseExifCoordinate = (coordStr) => {
    if (!coordStr) return null;
    
    // Check if it's already a decimal number
    const num = Number(coordStr);
    if (!isNaN(num)) return num;
    
    // Regex for D M S format (e.g., 35 41 22.2 N)
    const match = coordStr.match(/([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([NSEW])/i);
    if (match) {
      const deg = parseFloat(match[1]);
      const min = parseFloat(match[2]);
      const sec = parseFloat(match[3]);
      const ref = match[4].toUpperCase();
      
      let decimal = deg + min / 60 + sec / 3600;
      if (ref === 'S' || ref === 'W') {
        decimal = -decimal;
      }
      return decimal;
    }

    // Try a simpler split
    const clean = coordStr.replace(/[\[\]]/g, '').trim();
    const parts = clean.split(/\s+/);
    if (parts.length >= 1) {
      const degVal = parseFloat(parts[0]);
      if (!isNaN(degVal)) {
        let val = degVal;
        if (parts.length >= 2) {
          const minVal = parseFloat(parts[1]);
          if (!isNaN(minVal)) val += minVal / 60;
        }
        if (parts.length >= 3) {
          const secVal = parseFloat(parts[2]);
          if (!isNaN(secVal)) val += secVal / 3600;
        }
        const lastPart = parts[parts.length - 1].toUpperCase();
        if (lastPart === 'S' || lastPart === 'W' || coordStr.includes('S') || coordStr.includes('W')) {
          val = -val;
        }
        return val;
      }
    }
    return null;
  };

  const exif = analysis.exif || {};
  let lat = parseExifCoordinate(exif.latitude);
  let lon = parseExifCoordinate(exif.longitude);

  const locIntel = analysis.location_intelligence || {};
  
  const countryCenters = {
    "Japan": [36.2048, 138.2529],
    "India": [20.5937, 78.9629],
    "United States": [37.0902, -95.7129],
    "United Kingdom": [55.3781, -3.4360],
    "Germany": [51.1657, 10.4515],
    "France": [46.2276, 2.2137],
    "Brazil": [-14.2350, -51.9253],
    "Canada": [56.1304, -106.3468],
    "Australia": [-25.2744, 133.7751],
    "Russia": [61.5240, 105.3188],
  };

  let markerText = "Asset Location Prior";
  let hasMarker = false;

  if (lat !== null && lon !== null) {
    hasMarker = true;
    markerText = `EXIF GPS: ${lat.toFixed(4)}, ${lon.toFixed(4)} (${exif.camera_model || "Device"})`;
  } else if (locIntel.country && countryCenters[locIntel.country]) {
    [lat, lon] = countryCenters[locIntel.country];
    markerText = `Estimated Country Center: ${locIntel.country}`;
    hasMarker = true;
  } else {
    lat = 20.0;
    lon = 0.0;
  }

  const centerPosition = [lat, lon];

  return (
    <div className="w-full h-80 rounded-xl overflow-hidden border border-[#1f1f23] relative z-0">
      <MapContainer 
        center={centerPosition} 
        zoom={hasMarker ? 5 : 2} 
        style={{ width: '100%', height: '100%', background: '#070708' }}
      >
        <ChangeView center={centerPosition} />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        {hasMarker && (
          <Marker position={centerPosition}>
            <Popup>
              <div className="text-xs font-mono font-bold text-slate-800">
                {markerText}
                {locIntel.city && <div className="mt-1 font-normal">City: {locIntel.city}</div>}
              </div>
            </Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
}
