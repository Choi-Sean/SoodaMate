import { LOCATIONS_JSON } from "./locationsData";

export interface LocationCountry {
  isoCode: string;
  name: string;
  flag: string;
}

export interface LocationState {
  isoCode: string;
  countryCode: string;
  name: string;
  latitude: string;
  longitude: string;
}

export interface LocationCity {
  name: string;
  countryCode: string;
  stateCode: string;
  latitude: string;
  longitude: string;
}

interface LocationsPayload {
  countries: LocationCountry[];
  states: LocationState[];
  cities: LocationCity[];
}

// Parsed once, lazily, on first real call — never at module load, so
// importing this file (e.g. transitively at app boot) never pays the
// ~2.2MB JSON.parse cost unless a screen that actually needs location data
// mounts. Same lazy-cache shape as CityAutocomplete's own getAllCities().
let cached: LocationsPayload | null = null;
function data(): LocationsPayload {
  if (!cached) cached = JSON.parse(LOCATIONS_JSON) as LocationsPayload;
  return cached;
}

export function getAllCountries(): LocationCountry[] {
  return data().countries;
}

export function getCountryByCode(isoCode: string | null | undefined): LocationCountry | undefined {
  return data().countries.find((c) => c.isoCode === isoCode);
}

export function getStatesOfCountry(countryCode: string | null | undefined): LocationState[] {
  return data().states.filter((s) => s.countryCode === countryCode);
}

export function getStateByCodeAndCountry(
  stateCode: string | null | undefined,
  countryCode: string | null | undefined
): LocationState | undefined {
  return data().states.find((s) => s.isoCode === stateCode && s.countryCode === countryCode);
}

export function getCitiesOfCountry(countryCode: string | null | undefined): LocationCity[] {
  return data().cities.filter((c) => c.countryCode === countryCode);
}

export function getCitiesOfState(
  countryCode: string | null | undefined,
  stateCode: string | null | undefined
): LocationCity[] {
  return data().cities.filter((c) => c.countryCode === countryCode && c.stateCode === stateCode);
}
