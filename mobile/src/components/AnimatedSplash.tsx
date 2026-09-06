import { useEffect, useRef } from "react";
import { Animated, Easing, Image, StyleSheet, View } from "react-native";

import { colors } from "../theme";

interface Props {
  /** Called on this view's first layout — the earliest safe point to hide
   * the native splash without a blank flash in between the two. */
  onReady: () => void;
}

/** Shown the instant JS takes over from the native splash screen (see
 * App.tsx — SplashScreen.hideAsync() fires via onReady once this has
 * actually painted), so the handoff is seamless: same background/icon, now
 * with a gentle bounce loop instead of sitting static while init work
 * (i18n, ads) finishes. */
export default function AnimatedSplash({ onReady }: Props) {
  const scale = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(scale, {
          toValue: 1.12,
          duration: 550,
          easing: Easing.out(Easing.back(2)),
          useNativeDriver: true,
        }),
        Animated.timing(scale, {
          toValue: 1,
          duration: 550,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [scale]);

  return (
    <View style={styles.container} onLayout={onReady}>
      <Animated.Image
        source={require("../../assets/splash-icon.png")}
        style={[styles.icon, { transform: [{ scale }] }]}
        resizeMode="contain"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.creamDeep },
  icon: { width: 220, height: 220 },
});
