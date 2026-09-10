// "만 나이" (Korean international/actual age) is just standard calendar
// age — this file exists purely so every screen that needs to show it next
// to a birth date computes it the same way, rather than reimplementing the
// month/day rollover check inline each time.

/** Returns null for an unparsable/empty input rather than throwing, so
 * callers mid-typing a birth date (ProfileSetupScreen) can call this on
 * every keystroke without guarding first. */
export function calculateAge(birthDateIso: string): number | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(birthDateIso)) return null;
  const birth = new Date(birthDateIso + "T00:00:00");
  if (Number.isNaN(birth.getTime())) return null;

  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  return age >= 0 ? age : null;
}

export function formatDate(iso: string, language: string): string {
  return new Date(iso + "T00:00:00").toLocaleDateString(language, { year: "numeric", month: "long", day: "numeric" });
}

/** Formats a full ISO datetime (a server `created_at`/`published_at`, with
 * time and timezone) as a plain calendar date in the given locale. Unlike
 * formatDate above — which expects a bare "YYYY-MM-DD" and appends a
 * time — this parses the timestamp as-is. Returns "" for anything
 * unparsable rather than rendering "Invalid Date". */
export function formatTimestampDate(iso: string, language: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(language, { year: "numeric", month: "long", day: "numeric" });
}
