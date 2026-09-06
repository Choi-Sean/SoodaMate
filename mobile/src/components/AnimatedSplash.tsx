import { useEffect, useRef } from "react";
import { Animated, Easing, Image, StyleSheet, View } from "react-native";

import { colors } from "../theme";

/** In-JS loading placeholder shown while init work (i18n, ads) runs —
 * replaces a plain spinner with the mascot bouncing in a gentle spring
 * loop. Purely a React view with no native splash-screen lifecycle tie-in
 * (see App.tsx for why). */
export default function AnimatedSplash() {
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
    <View style={styles.container}>
      <Animated.View style={{ transform: [{ scale }] }}>
        <Image source={require("../../assets/splash-icon.png")} style={styles.icon} resizeMode="contain" />
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.creamDeep },
  icon: { width: 220, height: 220 },
});
