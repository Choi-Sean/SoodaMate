import { Vibration } from "react-native";

// A short celebratory double-buzz, not the long repeating pattern used for an
// incoming call (services/CallContext.tsx) — this fires once and stops on its
// own. iOS only honors the wait gaps, not individual buzz lengths (fixed OS
// duration), so this still reads as "buzz, pause, buzz" there too.
const MATCH_VIBRATION_PATTERN = [0, 80, 60, 80];

/** Call the moment a match becomes visible to the user — the regular
 * swipe-match celebration screen and the blind-chat "you're paired up" reveal
 * both use this, so the feel is identical everywhere a match happens. */
export function vibrateOnMatch(): void {
  Vibration.vibrate(MATCH_VIBRATION_PATTERN);
}
