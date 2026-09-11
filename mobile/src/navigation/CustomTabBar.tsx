import { useState } from "react";
import { Pressable, Text, View, StyleSheet } from "react-native";
import type { BottomTabBarProps } from "@react-navigation/bottom-tabs";
import { useTranslation } from "react-i18next";

import BlindChatCategoryPopup from "../components/BlindChatCategoryPopup";
import { colors } from "../theme";

const REAL_TAB_ICONS: Record<string, string> = {
  Chat: "💬",
  Likes: "❤️",
  Profile: "👤",
};
const REAL_TAB_LABEL_KEYS: Record<string, string> = {
  Chat: "tabs.chat",
  Likes: "tabs.likes",
  Profile: "tabs.profile",
};

/** Blind Chat is the app's primary flow now (Discover/classic Matching were
 * demoted to a secondary link inside Profile — see ProfileStack), so it gets
 * an Instagram/Tinder-style elevated center button instead of being just
 * another tab. Tapping it doesn't navigate directly — it pops the cute
 * category picker (BlindChatCategoryPopup), and picking a category is what
 * navigates, straight into ChatStack's BlindChatQueue screen. */
export default function CustomTabBar({ state, navigation }: BottomTabBarProps) {
  const { t } = useTranslation();
  const [popupVisible, setPopupVisible] = useState(false);

  return (
    <View style={styles.wrap}>
      <View style={styles.bar}>
        {state.routes.map((route, index) => {
          const focused = state.index === index;
          return (
            <Pressable
              key={route.key}
              style={styles.tabButton}
              onPress={() => {
                const event = navigation.emit({ type: "tabPress", target: route.key, canPreventDefault: true });
                if (!focused && !event.defaultPrevented) navigation.navigate(route.name);
              }}
            >
              <View style={[styles.iconBubble, focused && styles.iconBubbleActive]}>
                <Text style={{ fontSize: 18 }}>{REAL_TAB_ICONS[route.name]}</Text>
              </View>
              <Text style={[styles.label, focused && styles.labelActive]} numberOfLines={1}>
                {t(REAL_TAB_LABEL_KEYS[route.name])}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Pressable style={styles.centerButton} onPress={() => setPopupVisible(true)}>
        <Text style={styles.centerButtonIcon}>🎭</Text>
      </Pressable>
      <Text style={styles.centerLabel}>{t("tabs.blindChat")}</Text>

      <BlindChatCategoryPopup
        visible={popupVisible}
        onClose={() => setPopupVisible(false)}
        onSelectCategory={(key) =>
          navigation.navigate("Chat", { screen: "BlindChatQueue", params: { initialCategories: [key] } } as never)
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: colors.white,
    borderTopWidth: 0,
    shadowColor: colors.navyDeep,
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: -2 },
    elevation: 8,
  },
  bar: { flexDirection: "row", height: 62, paddingTop: 6 },
  tabButton: { flex: 1, alignItems: "center", justifyContent: "center", gap: 2 },
  iconBubble: { width: 34, height: 26, borderRadius: 13, alignItems: "center", justifyContent: "center" },
  iconBubbleActive: { backgroundColor: colors.creamDeep },
  label: { fontSize: 11, fontWeight: "700", color: colors.muted },
  labelActive: { color: colors.accentDark },
  centerButton: {
    position: "absolute",
    alignSelf: "center",
    top: -26,
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 4,
    borderColor: colors.white,
    shadowColor: colors.navyDeep,
    shadowOpacity: 0.25,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 10,
  },
  centerButtonIcon: { fontSize: 26 },
  centerLabel: {
    position: "absolute",
    top: 36,
    alignSelf: "center",
    fontSize: 10.5,
    fontWeight: "800",
    color: colors.accentDark,
  },
});
