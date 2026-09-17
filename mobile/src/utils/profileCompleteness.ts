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

// An account only goes "active" (can use Blind Chat — see CustomTabBar,
// BlindChatQueueScreen, MyProfileScreen) once ID+selfie verification is
// approved *and* the profile itself is filled in enough to be worth
// matching on. face_verified is already one of the checks above, so a
// verified account is never more than one unfilled field away from this
// bar — the two conditions rarely disagree in practice, but are still
// checked independently since they mean different things.
export const MIN_COMPLETENESS_FOR_ACTIVE = 70;

export function isAccountActive(profile: Profile): boolean {
  return profile.face_verified && calculateProfileCompleteness(profile) >= MIN_COMPLETENESS_FOR_ACTIVE;
}
