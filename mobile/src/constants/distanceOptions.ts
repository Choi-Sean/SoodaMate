// Dropdown choices for "max distance" — replaces the old free-number
// TextInput. 500 is treated as "no limit" (the widest practical value; the
// backend's distance filter still applies, just at a radius nobody's
// realistically outside of).
export const DISTANCE_OPTIONS_KM = [5, 10, 25, 50, 100, 200, 500] as const;
