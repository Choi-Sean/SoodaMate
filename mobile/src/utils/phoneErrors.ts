import type { TFunction } from "i18next";

// Must match backend/app/services/phone_screening.py::VIRTUAL_NUMBER_DETAIL and
// the fixed English `detail` strings in services/auth_service.py /
// sms_verification_service.py / sms/twilio_verify.py.
const KNOWN_DETAILS: Record<string, string> = {
  "virtual phone numbers are not allowed": "phoneAuth.virtualNumberNotAllowed",
  "incorrect or expired code": "phoneAuth.incorrectCode",
  "account disabled": "phoneAuth.accountDisabled",
  "failed to send verification code": "phoneAuth.sendFailed",
  // backend/app/core/rate_limit.py::TOO_MANY
  "too many requests, please try again later": "common.tooManyRequests",
};

/** User-facing message for a failed phone start/confirm call. The backend
 * answers with fixed English `detail` strings; swap the ones we know for a
 * localized message and pass anything else through unchanged. */
export function phoneErrorMessage(e: any, t: TFunction): string {
  const detail = e?.response?.data?.detail;
  if (typeof detail === "string" && KNOWN_DETAILS[detail]) return t(KNOWN_DETAILS[detail]);
  return detail ?? e?.message ?? t("common.somethingWentWrong");
}
