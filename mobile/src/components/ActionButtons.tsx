import { Pressable, Text, View, StyleSheet } from "react-native";
import { useTranslation } from "react-i18next";

import { colors } from "../theme";

interface Props {
  onPass: () => void;
  onLike: () => void;
  onSuperLike: () => void;
  disabled?: boolean;
}

// Buttons, not swipe gestures — a deliberate product choice for this app.
export default function ActionButtons({ onPass, onLike, onSuperLike, disabled }: Props) {
  const { t } = useTranslation();
  return (
    <View style={styles.row}>
      <Pressable
        style={[styles.button, styles.passButton]}
        onPress={onPass}
        disabled={disabled}
        accessibilityLabel={t("discover.pass", { defaultValue: "Pass" })}
      >
        <Text style={styles.passIcon}>✕</Text>
      </Pressable>

      <Pressable
        style={[styles.button, styles.superLikeButton]}
        onPress={onSuperLike}
        disabled={disabled}
        accessibilityLabel={t("discover.superLike", { defaultValue: "Super Like" })}
      >
        <Text style={styles.superLikeIcon}>★</Text>
      </Pressable>

      <Pressable
        style={[styles.button, styles.likeButton]}
        onPress={onLike}
        disabled={disabled}
        accessibilityLabel={t("discover.like", { defaultValue: "Like" })}
      >
        <Text style={styles.likeIcon}>♥</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 20, paddingVertical: 16 },
  button: {
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 999,
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  passButton: { width: 56, height: 56, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border },
  passIcon: { fontSize: 24, color: colors.muted },
  superLikeButton: { width: 48, height: 48, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border },
  superLikeIcon: { fontSize: 20, color: "#3B82F6" },
  likeButton: { width: 64, height: 64, backgroundColor: colors.accent },
  likeIcon: { fontSize: 28, color: "#fff" },
});
