import { useEffect, useRef } from "react";
import { Animated, Modal, Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import { BLIND_CHAT_CATEGORY_KEYS } from "../constants/blindChatCategories";
import { colors } from "../theme";

interface Props {
  visible: boolean;
  onClose: () => void;
  onSelectCategory: (key: string) => void;
}

/** The "cute pop" entry point into Blind Chat from the center nav button —
 * tapping a category closes this and drops the user straight into
 * BlindChatQueueScreen with that category preselected (they can still add
 * more categories/filters there before starting). A spring scale-in on the
 * card (not per-chip stagger — plenty of "뿅" on its own without the extra
 * complexity) is plain Animated, no new dependency. */
export default function BlindChatCategoryPopup({ visible, onClose, onSelectCategory }: Props) {
  const { t } = useTranslation();
  const scale = useRef(new Animated.Value(0.85)).current;
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible) {
      scale.setValue(0.85);
      opacity.setValue(0);
      Animated.parallel([
        Animated.spring(scale, { toValue: 1, friction: 6, tension: 80, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 1, duration: 160, useNativeDriver: true }),
      ]).start();
    }
  }, [visible, scale, opacity]);

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Animated.View style={[styles.card, { transform: [{ scale }], opacity }]} onStartShouldSetResponder={() => true}>
          <Pressable style={styles.closeButton} onPress={onClose} hitSlop={8}>
            <Ionicons name="close" size={20} color={colors.muted} />
          </Pressable>
          <Text style={styles.badge}>💬✨</Text>
          <Text style={styles.title}>{t("blindChat.popupTitle")}</Text>
          <Text style={styles.subtitle}>{t("blindChat.popupSubtitle")}</Text>
          <View style={styles.grid}>
            {BLIND_CHAT_CATEGORY_KEYS.map((key) => (
              <Pressable
                key={key}
                style={styles.chip}
                onPress={() => {
                  onClose();
                  onSelectCategory(key);
                }}
              >
                <Text style={styles.chipText}>{t(`blindChatCategories.${key}`)}</Text>
              </Pressable>
            ))}
          </View>
        </Animated.View>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(11,41,68,0.55)",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  card: {
    width: "100%",
    maxWidth: 400,
    backgroundColor: colors.white,
    borderRadius: 28,
    padding: 24,
    alignItems: "center",
  },
  closeButton: { position: "absolute", top: 14, right: 14, padding: 4 },
  badge: { fontSize: 34, marginBottom: 6 },
  title: { fontSize: 19, fontWeight: "800", color: colors.navy, textAlign: "center" },
  subtitle: { fontSize: 13, color: colors.muted, textAlign: "center", marginTop: 4, marginBottom: 18 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 8, justifyContent: "center" },
  chip: {
    backgroundColor: colors.creamDeep,
    borderRadius: 20,
    paddingVertical: 10,
    paddingHorizontal: 14,
  },
  chipText: { fontSize: 13.5, fontWeight: "700", color: colors.ink },
});
