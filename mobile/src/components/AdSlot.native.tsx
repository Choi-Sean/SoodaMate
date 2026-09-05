import { View, StyleSheet } from "react-native";
import { BannerAd, BannerAdSize, TestIds } from "react-native-google-mobile-ads";

// Test ad unit ID until a real AdMob account exists (TestIds.BANNER
// auto-picks the right platform-specific test ID); swapping in a real unit
// ID later is a one-line change.
export default function AdSlot() {
  return (
    <View style={styles.container}>
      <BannerAd unitId={TestIds.BANNER} size={BannerAdSize.BANNER} />
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
    overflow: "hidden",
  },
});
