import { Image, StyleSheet, View } from "react-native";

import { colors } from "../theme";

/** In-JS loading placeholder shown while init work (i18n, ads) runs — a
 * static render of the splash artwork (icon + wordmark), matching the
 * native splash screen exactly so there's no visible hand-off. No native
 * splash-screen lifecycle tie-in (see App.tsx for why). */
export default function AnimatedSplash() {
  return (
    <View style={styles.container}>
      <Image source={require("../../assets/splash-icon.png")} style={styles.icon} resizeMode="contain" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.creamDeep },
  icon: { width: 320, height: 457 },
});
