import { apiClient } from "./client";
import type { Gender, InterestedIn, Profile } from "../types";

export interface ProfileUpdateInput {
  display_name: string;
  legal_first_name: string;
  birth_date: string; // YYYY-MM-DD
  gender: Gender;
  interested_in: InterestedIn;
  bio?: string | null;
  location_lat?: number | null;
  location_lng?: number | null;
  min_age_pref?: number;
  max_age_pref?: number;
  max_distance_km?: number;
  race_ethnicity?: string | null;
  religion?: string | null;
  political_view?: string | null;
  height_cm?: number | null;
  occupation?: string | null;
  education?: string | null;
  hometown?: string | null;
  smoking?: string | null;
  cannabis?: string | null;
  exercise_frequency?: string | null;
  relationship_goal?: string | null;
  wants_kids?: string | null;
  has_kids?: string | null;
  interests?: string[];
  languages?: string[];
}

export async function getMyProfile(): Promise<Profile> {
  const resp = await apiClient.get<Profile>("/profiles/me");
  return resp.data;
}

export async function updateMyProfile(input: ProfileUpdateInput): Promise<Profile> {
  const resp = await apiClient.put<Profile>("/profiles/me", input);
  return resp.data;
}

export async function confirmPhoto(gcsObjectPath: string, position: number) {
  const resp = await apiClient.post("/profiles/me/photos/confirm", {
    gcs_object_path: gcsObjectPath,
    position,
  });
  return resp.data;
}

export async function deletePhoto(photoId: string): Promise<void> {
  await apiClient.delete(`/profiles/me/photos/${photoId}`);
}

export async function setIncognito(isIncognito: boolean): Promise<Profile> {
  const resp = await apiClient.post<Profile>("/profiles/me/incognito", { is_incognito: isIncognito });
  return resp.data;
}

export async function setTravelMode(lat: number, lng: number, durationHours = 24): Promise<Profile> {
  const resp = await apiClient.post<Profile>("/profiles/me/travel", {
    lat,
    lng,
    duration_hours: durationHours,
  });
  return resp.data;
}

export async function clearTravelMode(): Promise<Profile> {
  const resp = await apiClient.delete<Profile>("/profiles/me/travel");
  return resp.data;
}

export interface PremiumFilterInput {
  race_filter?: string[];
  religion_filter?: string[];
  political_view_filter?: string[];
  exercise_frequency_filter?: string[];
  smoking_filter?: string[];
  cannabis_filter?: string[];
  relationship_goal_filter?: string[];
  wants_kids_filter?: string[];
  has_kids_filter?: string[];
  height_min?: number | null;
  height_max?: number | null;
}

/** Full replace, not a merge — 402s if the caller isn't an active premium
 * member (see routers/profiles.py::set_premium_filters). Any field left
 * out of `input` is sent as empty/null and clears that dimension, so
 * callers that only mean to change one thing must spread the rest of the
 * profile's current premium_filters in too (see EditProfileScreen). */
export async function setPremiumFilters(input: PremiumFilterInput): Promise<Profile> {
  const resp = await apiClient.put<Profile>("/profiles/me/premium-filters", input);
  return resp.data;
}

/** Free for everyone, unlike setPremiumFilters above. */
export async function setAgeFilter(minAgePref: number, maxAgePref: number): Promise<Profile> {
  const resp = await apiClient.put<Profile>("/profiles/me/age-filter", {
    min_age_pref: minAgePref,
    max_age_pref: maxAgePref,
  });
  return resp.data;
}
