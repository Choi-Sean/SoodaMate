import { Text, View, StyleSheet } from "react-native";

import { colors } from "../theme";

// react-native-google-mobile-ads has no web build at all — web only exists
// in this project for dev-time bundling checks, so a static placeholder
// card is enough here (same convention the old banner ad slot used).
export default function AdCard() {
  return (
    <View style={styles.card}>
      <Text style={styles.text}>Ad (native only)</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    borderRadius: 24,
    backgroundColor: colors.creamDeep,
    alignItems: "center",
    justifyContent: "center",
  },
  text: { color: colors.muted, fontSize: 13 },
});
