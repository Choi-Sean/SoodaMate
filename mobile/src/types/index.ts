export type Gender = "male" | "female" | "other";
export type InterestedIn = Gender | "all";

export interface Photo {
  id: string;
  gcs_object_path: string;
  url: string;
  position: number;
  media_type: "photo" | "video";
}

export interface PremiumFilters {
  political_view_filter: string[];
  exercise_frequency_filter: string[];
  smoking_filter: string[];
  cannabis_filter: string[];
  relationship_goal_filter: string[];
  wants_kids_filter: string[];
  has_kids_filter: string[];
}

export interface Profile {
  user_id: string;
  display_name: string;
  legal_first_name: string;
  birth_date: string;
  gender: Gender;
  interested_in: InterestedIn;
  open_to_language_exchange: boolean;
  bio: string | null;
  bio2: string | null;
  bio3: string | null;
  location_lat: number | null;
  location_lng: number | null;
  min_age_pref: number;
  max_age_pref: number;
  max_distance_km: number;
  is_profile_complete: boolean;
  verified_badge: "work" | "school" | null;
  face_verified: boolean;
  superlike_credits: number;
  boost_credits: number;
  boost_active_until: string | null;
  is_incognito: boolean;
  travel_lat: number | null;
  travel_lng: number | null;
  travel_expires_at: string | null;
  race_ethnicity: string | null;
  religion: string | null;
  political_view: string | null;
  premium_until: string | null;
  is_premium_member: boolean;
  billing_cycle: "monthly" | "yearly" | null;
  subscription_price_cents: number | null;
  cancel_at_period_end: boolean;
  race_filter: string[];
  religion_filter: string[];
  height_filter_min: number | null;
  height_filter_max: number | null;
  languages_filter: string[];
  interests_filter: string[];
  verified_only: boolean;
  language_exchange_only: boolean;
  expand_distance_if_low: boolean;
  expand_others_if_low: boolean;
  premium_filters: PremiumFilters;
  height_cm: number | null;
  occupation: string | null;
  education: string | null;
  hometown: string | null;
  smoking: string | null;
  cannabis: string | null;
  exercise_frequency: string | null;
  relationship_goal: string | null;
  wants_kids: string | null;
  has_kids: string | null;
  interests: string[];
  languages: string[];
  k_content_tags: string[];
  k_content_filter: string[];
  updated_at: string;
  photos: Photo[];
}

export interface Candidate {
  user_id: string;
  display_name: string;
  age: number;
  gender: Gender;
  bio: string | null;
  bio2: string | null;
  bio3: string | null;
  photos: Photo[];
  distance_km: number | null;
  superliked_me: boolean;
  height_cm: number | null;
  occupation: string | null;
  education: string | null;
  hometown: string | null;
  race_ethnicity: string | null;
  religion: string | null;
  political_view: string | null;
  smoking: string | null;
  cannabis: string | null;
  exercise_frequency: string | null;
  relationship_goal: string | null;
  wants_kids: string | null;
  has_kids: string | null;
  interests: string[];
  languages: string[];
  k_content_tags: string[];
  verified_badge: "work" | "school" | null;
  face_verified: boolean;
  open_to_language_exchange: boolean;
}

export interface Match {
  id: string;
  other_user_id: string;
  other_display_name: string;
  other_photo_url: string | null;
  matched_at: string;
  is_message_restricted: boolean;
  can_send_first_message: boolean;
  first_message_deadline: string | null;
  is_active: boolean;
}

export interface ChatMessage {
  id: string;
  match_id: string;
  sender_id: string;
  content: string;
  message_type: "text" | "image";
  image_url: string | null;
  original_language: string | null;
  translated_content: string | null;
  translated_language: string | null;
  sent_at: string;
  delivered_at: string | null;
  read_at: string | null;
}

export interface Icebreaker {
  type: "shared_kcontent" | "shared_interest" | "shared_language_exchange" | "shared_language" | "generic";
  key: string | null;
}

export interface CoupleStory {
  id: string;
  match_id: string;
  author_id: string;
  peer_id: string;
  author_display_name: string;
  peer_display_name: string;
  story_text: string;
  photo_object_path: string | null;
  photo_url: string | null;
  status: "pending" | "published" | "declined" | "hidden";
  created_at: string;
  published_at: string | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
}
