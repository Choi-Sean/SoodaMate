// Location picker's country list is scoped to countries where one of the
// app's supported languages (Korean, English, Japanese, Chinese, Spanish)
// is widely spoken, rather than all ~250 ISO countries — this app's target
// markets, not a general-purpose address form.
export const SUPPORTED_COUNTRY_CODES = [
  // Korean
  "KR",
  // Japanese
  "JP",
  // Chinese
  "CN", "TW", "HK", "MO", "SG",
  // English
  "US", "GB", "CA", "AU", "NZ", "IE", "ZA", "PH",
  // Spanish
  "ES", "MX", "AR", "CO", "CL", "PE", "VE", "EC", "GT", "CU",
  "BO", "DO", "HN", "PY", "SV", "NI", "CR", "PA", "UY",
] as const;
