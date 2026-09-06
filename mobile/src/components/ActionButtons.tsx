import { Pressable, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
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
        style={({ pressed }) => [styles.button, styles.passButton, pressed && styles.pressed]}
        onPress={onPass}
        disabled={disabled}
        accessibilityLabel={t("discover.pass", { defaultValue: "Pass" })}
      >
        <Ionicons name="close" size={30} color={colors.heart} />
      </Pressable>

      <Pressable
        style={({ pressed }) => [styles.button, styles.superLikeButton, pressed && styles.pressed]}
        onPress={onSuperLike}
        disabled={disabled}
        accessibilityLabel={t("discover.superLike", { defaultValue: "Super Like" })}
      >
        <Ionicons name="star" size={22} color="#3B82F6" />
      </Pressable>

      <Pressable
        style={({ pressed }) => [styles.button, styles.likeButton, pressed && styles.pressed]}
        onPress={onLike}
        disabled={disabled}
        accessibilityLabel={t("discover.like", { defaultValue: "Like" })}
      >
        <Ionicons name="heart" size={30} color="#fff" />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 22, paddingVertical: 18 },
  button: {
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 999,
    shadowColor: "#000",
    shadowOpacity: 0.18,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
    elevation: 4,
  },
  pressed: { transform: [{ scale: 0.92 }], opacity: 0.85 },
  passButton: { width: 58, height: 58, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border },
  superLikeButton: { width: 48, height: 48, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border },
  likeButton: { width: 68, height: 68, backgroundColor: colors.accent },
});
