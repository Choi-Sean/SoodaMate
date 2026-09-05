import { Platform, View, StyleSheet } from "react-native";
import { BannerAd, BannerAdSize, TestIds } from "react-native-google-mobile-ads";

import { env } from "../config/env";

const realUnitId = Platform.OS === "ios" ? env.admobIosBannerUnitId : env.admobAndroidBannerUnitId;
// Falls back to Google's test ad unit ID until a real AdMob account exists
// and EXPO_PUBLIC_ADMOB_*_BANNER_UNIT_ID is set (see docs/ENV_VARS.md).
const bannerUnitId = realUnitId || TestIds.BANNER;

export default function AdSlot() {
  return (
    <View style={styles.container}>
      <BannerAd unitId={bannerUnitId} size={BannerAdSize.BANNER} />
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
