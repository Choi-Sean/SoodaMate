import type { Profile } from "../types";

/** Weighted-equal checklist behind the "profile strength" meter shown in
 * Edit Profile — required fields already exist by the time someone reaches
 * this screen, so this is really measuring how many *optional* fields and
 * how much photo/video variety they've filled in (the stuff that actually
 * correlates with getting more likes). */
export function calculateProfileCompleteness(profile: Profile): number {
  const checks: boolean[] = [
    !!profile.bio && profile.bio.trim().length > 0,
    profile.photos.length >= 3,
    profile.photos.some((p) => p.media_type === "video"),
    !!profile.race_ethnicity,
    !!profile.religion,
    !!profile.political_view,
    profile.height_cm != null,
    !!profile.occupation,
    !!profile.education,
    !!profile.hometown,
    !!profile.smoking,
    !!profile.exercise_frequency,
    !!profile.relationship_goal,
    !!profile.wants_kids,
    !!profile.has_kids,
    profile.interests.length > 0,
    profile.languages.length > 0,
    profile.face_verified,
  ];
  const filled = checks.filter(Boolean).length;
  return Math.round((filled / checks.length) * 100);
}
