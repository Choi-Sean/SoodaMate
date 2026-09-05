export interface PresetCity {
  key: string;
  label: string;
  lat: number;
  lng: number;
}

// No geocoding API exists in the app, so manual location entry is a short
// preset list + freeform lat/lng rather than a map/address picker.
export const PRESET_CITIES: PresetCity[] = [
  { key: "seoul", label: "Seoul", lat: 37.5665, lng: 126.978 },
  { key: "busan", label: "Busan", lat: 35.1796, lng: 129.0756 },
  { key: "incheon", label: "Incheon", lat: 37.4563, lng: 126.7052 },
  { key: "tokyo", label: "Tokyo", lat: 35.6762, lng: 139.6503 },
  { key: "osaka", label: "Osaka", lat: 34.6937, lng: 135.5023 },
  { key: "newyork", label: "New York", lat: 40.7128, lng: -74.006 },
  { key: "losangeles", label: "Los Angeles", lat: 34.0522, lng: -118.2437 },
  { key: "london", label: "London", lat: 51.5072, lng: -0.1276 },
  { key: "paris", label: "Paris", lat: 48.8566, lng: 2.3522 },
  { key: "beijing", label: "Beijing", lat: 39.9042, lng: 116.4074 },
  { key: "shanghai", label: "Shanghai", lat: 31.2304, lng: 121.4737 },
];
