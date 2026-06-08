import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Helper component to center map on new coordinates
function ChangeView({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center && center[0] !== 0 && center[1] !== 0) {
      map.setView(center, zoom || map.getZoom());
    }
  }, [center, zoom, map]);
  return null;
}

export default function ClusterMap({ estimatedLocation, candidateLocations, clusterSummary }) {
  if (!estimatedLocation || !estimatedLocation.coordinates) {
    return (
      <div className="w-full h-96 flex items-center justify-center bg-[#09090b] border border-[#1f1f23] rounded-xl font-mono text-xs text-zinc-500">
        NO GEOGRAPHIC DATA FOR MAP VIEW
      </div>
    );
  }

  const { lat, lng, accuracy_radius_km } = estimatedLocation.coordinates;
  const centerPosition = [lat, lng];

  // Helper to construct custom div icons
  const createCentroidIcon = () => {
    return L.divIcon({
      className: 'custom-centroid-marker',
      html: `
        <div class="relative flex items-center justify-center w-6 h-6">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60"></span>
          <span class="relative inline-flex rounded-full h-3.5 w-3.5 bg-emerald-500 border-2 border-[#09090b] shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
        </div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });
  };

  const createCandidateIcon = (isDominantCluster) => {
    const colorClass = isDominantCluster ? 'bg-blue-500 shadow-[0_0_6px_rgba(59,130,246,0.6)] border-blue-200' : 'bg-purple-500 border-purple-200';
    return L.divIcon({
      className: 'custom-candidate-marker',
      html: `
        <div class="w-3.5 h-3.5 rounded-full ${colorClass} border-2 border-[#09090b]"></div>
      `,
      iconSize: [14, 14],
      iconAnchor: [7, 7]
    });
  };

  const createNoiseIcon = () => {
    return L.divIcon({
      className: 'custom-noise-marker',
      html: `
        <div class="w-3 h-3 rounded-full bg-zinc-500 opacity-60 border-2 border-[#09090b]"></div>
      `,
      iconSize: [12, 12],
      iconAnchor: [6, 6]
    });
  };

  const dominantClusterId = clusterSummary?.dominant_cluster_id ?? 0;

  return (
    <div className="w-full h-[420px] rounded-xl overflow-hidden border border-[#1f1f23] relative z-0 shadow-lg">
      <MapContainer 
        center={centerPosition} 
        zoom={11} 
        style={{ width: '100%', height: '100%', background: '#09090b' }}
      >
        <ChangeView center={centerPosition} zoom={11} />
        
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* Dominant Cluster Centroid Circle (Accuracy Radius) */}
        {accuracy_radius_km && (
          <Circle
            center={centerPosition}
            radius={accuracy_radius_km * 1000} // meters
            pathOptions={{
              fillColor: '#10b981',
              fillOpacity: 0.08,
              color: '#10b981',
              weight: 1.5,
              dashArray: '6, 6',
            }}
          />
        )}

        {/* Dominant Centroid Pin */}
        <Marker position={centerPosition} icon={createCentroidIcon()}>
          <Popup className="custom-leaflet-popup">
            <div className="p-2 font-mono text-[10px] text-zinc-300 bg-[#0c0c0e] border border-[#1f1f23] rounded p-2">
              <div className="font-bold text-emerald-400 border-b border-emerald-500/20 pb-1 mb-1.5 uppercase tracking-wider text-[11px]">
                Estimated Centroid
              </div>
              <div className="mb-0.5"><span className="text-zinc-500">RESOLVED:</span> {estimatedLocation.city}, {estimatedLocation.region}, {estimatedLocation.country}</div>
              <div className="mb-0.5"><span className="text-zinc-500">COORDS:</span> {lat.toFixed(6)}, {lng.toFixed(6)}</div>
              <div><span className="text-zinc-500">ACCURACY:</span> ±{accuracy_radius_km?.toFixed(2)} km</div>
            </div>
          </Popup>
        </Marker>

        {/* Candidate Pin Markers */}
        {candidateLocations && candidateLocations.map((candidate, idx) => {
          if (!candidate.lat || !candidate.lng) return null;
          
          const isNoise = candidate.cluster_id === -1;
          const isDominant = candidate.cluster_id === dominantClusterId;
          const pos = [candidate.lat, candidate.lng];
          
          let markerIcon;
          if (isNoise) {
            markerIcon = createNoiseIcon();
          } else {
            markerIcon = createCandidateIcon(isDominant);
          }

          return (
            <Marker key={idx} position={pos} icon={markerIcon}>
              <Popup className="custom-leaflet-popup">
                <div className="p-2 font-mono text-[10px] text-zinc-300 bg-[#0c0c0e] border border-[#1f1f23] rounded p-2">
                  <div className={`font-bold border-b pb-1 mb-1.5 uppercase tracking-wider text-[11px] ${
                    isNoise ? 'text-zinc-400 border-zinc-500/20' : isDominant ? 'text-blue-400 border-blue-500/20' : 'text-purple-400 border-purple-500/20'
                  }`}>
                    {isNoise ? 'Noise Signal' : isDominant ? 'Cluster Member (Dominant)' : 'Secondary Cluster'}
                  </div>
                  <div className="mb-0.5 font-semibold text-zinc-200">"{candidate.raw_signal}"</div>
                  <div className="mb-0.5"><span className="text-zinc-500">SOURCE:</span> {candidate.source}</div>
                  <div className="mb-0.5"><span className="text-zinc-500">FRAME:</span> {candidate.frame_id}</div>
                  <div className="mb-0.5"><span className="text-zinc-500">CONFIDENCE:</span> {(candidate.confidence * 100).toFixed(0)}%</div>
                  <div><span className="text-zinc-500">COORDS:</span> {candidate.lat.toFixed(5)}, {candidate.lng.toFixed(5)}</div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
