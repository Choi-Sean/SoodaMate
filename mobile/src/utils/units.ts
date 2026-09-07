// The backend/API always stores and sends centimeters and kilometers
// (see docs/API.md and every Profile/Candidate field) - these are display-
// only conversions applied at render time, mirroring the pattern
// HeightInput.tsx already established for the edit-profile height stepper.
// Nothing here changes what's stored or sent over the wire.

export function cmToFtIn(cm: number): { ft: number; inch: number } {
  const totalInches = Math.round(cm / 2.54);
  return { ft: Math.floor(totalInches / 12), inch: totalInches % 12 };
}

export function ftInToCm(ft: number, inch: number): number {
  return Math.round((ft * 12 + inch) * 2.54);
}

export function formatHeightCm(cm: number): string {
  const { ft, inch } = cmToFtIn(cm);
  return `${ft}'${inch}"`;
}

export function kmToMiles(km: number): number {
  return km * 0.621371;
}

export function milesToKm(mi: number): number {
  return mi / 0.621371;
}

export function formatDistanceKm(km: number): number {
  return Math.round(kmToMiles(km));
}
