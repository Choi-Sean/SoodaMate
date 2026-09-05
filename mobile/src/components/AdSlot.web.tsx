import { Text, View, StyleSheet } from "react-native";

// react-native-google-mobile-ads has no web build at all — web gets a
// static placeholder instead (this app targets mobile; web is only used in
// this project for dev-time bundling checks).
export default function AdSlot() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>Ad (native only)</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    minHeight: 60,
    borderRadius: 10,
    backgroundColor: "#f2f2f2",
    alignItems: "center",
    justifyContent: "center",
    marginHorizontal: 16,
  },
  text: { color: "#aaa", fontSize: 12 },
});
