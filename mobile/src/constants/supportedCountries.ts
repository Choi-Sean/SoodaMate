// Location picker's country list is scoped to the app's actual current
// target markets, not all ~250 ISO countries or even every country where a
// supported UI language is spoken — deliberately narrowed to just these
// two for now, per explicit product direction. Widen this back out (the
// previous list covered every KR/JP/CN/EN/ES-speaking country) once the
// app expands beyond Korea + the US.
export const SUPPORTED_COUNTRY_CODES = ["KR", "US"] as const;
