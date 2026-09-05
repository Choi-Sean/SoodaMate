export type Gender = "male" | "female" | "other";
export type InterestedIn = Gender | "all";

export interface Photo {
  id: string;
  gcs_object_path: string;
  url: string;
  position: number;
}

export interface Profile {
  user_id: string;
  display_name: string;
  birth_date: string;
  gender: Gender;
  interested_in: InterestedIn;
  bio: string | null;
  location_lat: number | null;
  location_lng: number | null;
  min_age_pref: number;
  max_age_pref: number;
  max_distance_km: number;
  is_profile_complete: boolean;
  verified_badge: "work" | "school" | null;
  superlike_credits: number;
  boost_credits: number;
  boost_active_until: string | null;
  is_incognito: boolean;
  travel_lat: number | null;
  travel_lng: number | null;
  travel_expires_at: string | null;
  updated_at: string;
  photos: Photo[];
}

export interface Candidate {
  user_id: string;
  display_name: string;
  age: number;
  bio: string | null;
  photos: Photo[];
  distance_km: number | null;
  superliked_me: boolean;
}

export interface Match {
  id: string;
  other_user_id: string;
  other_display_name: string;
  matched_at: string;
  is_message_restricted: boolean;
  can_send_first_message: boolean;
  first_message_deadline: string | null;
}

export interface ChatMessage {
  id: string;
  match_id: string;
  sender_id: string;
  content: string;
  sent_at: string;
  delivered_at: string | null;
  read_at: string | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
}
