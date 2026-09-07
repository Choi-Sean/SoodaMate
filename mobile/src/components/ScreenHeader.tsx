import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors } from "../theme";

interface Props {
  title: string;
  right?: ReactNode;
}

/** The one header every top-level tab screen (Profile/Discover/Swipe/Likes/
 * Chat) renders, so font size, weight, color, and top spacing can never
 * drift apart screen-by-screen the way they did before — each screen used
 * to define its own near-identical `header` style by hand, and one of them
 * (Chat) only rendered it in the "has data" branch, so it silently
 * vanished on the empty/loading state. Screens must render this
 * unconditionally, before any loading/error/empty branch, not inside one.
 *
 * Top padding is insets.top + a small gap rather than a fixed magic
 * number — a fixed value either sits too low on a device with no notch
 * (web, older phones) or risks colliding with a real notch/status bar; the
 * safe-area inset is correct either way. */
export default function ScreenHeader({ title, right }: Props) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.row, { paddingTop: insets.top + 10 }]}>
      <Text style={styles.title}>{title}</Text>
      {right}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingBottom: 8,
  },
  title: { fontSize: 26, fontWeight: "800", color: colors.navy },
});
