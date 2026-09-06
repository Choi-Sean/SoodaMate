import { useEffect, useState } from "react";
import { ActivityIndicator, Image, Platform, Text, View, StyleSheet } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import {
  NativeAd,
  NativeAdView,
  NativeAsset,
  NativeAssetType,
  NativeMediaView,
  TestIds,
} from "react-native-google-mobile-ads";
import { useTranslation } from "react-i18next";

import { env } from "../config/env";
import { colors } from "../theme";

const realUnitId = Platform.OS === "ios" ? env.admobIosNativeUnitId : env.admobAndroidNativeUnitId;
// Falls back to Google's test native ad unit ID until a real AdMob account
// exists and EXPO_PUBLIC_ADMOB_*_NATIVE_UNIT_ID is set (see docs/ENV_VARS.md)
// — same fallback convention the old banner/interstitial unit ids used.
const nativeUnitId = realUnitId || TestIds.NATIVE;

interface Props {
  /** Called when there's genuinely nothing to show (load failed) so the
   * swipe deck can drop straight to the next real card instead of leaving
   * a dead slot in the stack. */
  onUnavailable: () => void;
}

/** A full swipe-deck-sized card rendering a real Google native ad —
 * Tinder/Bumble/Hinge all slot sponsored cards directly into the swipe
 * stack (styled like content) rather than a banner strip below it; this is
 * the same pattern using react-native-google-mobile-ads' NativeAd API. */
export default function AdCard({ onUnavailable }: Props) {
  const { t } = useTranslation();
  const [nativeAd, setNativeAd] = useState<NativeAd | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let loadedAd: NativeAd | null = null;
    NativeAd.createForAdRequest(nativeUnitId)
      .then((ad) => {
        if (cancelled) {
          ad.destroy();
          return;
        }
        loadedAd = ad;
        setNativeAd(ad);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
      loadedAd?.destroy();
    };
  }, []);

  useEffect(() => {
    if (failed) onUnavailable();
  }, [failed, onUnavailable]);

  if (failed) return null;

  if (!nativeAd) {
    return (
      <View style={[styles.card, styles.centered]}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  return (
    <NativeAdView nativeAd={nativeAd} style={styles.card}>
      <NativeMediaView style={styles.media} resizeMode="cover" />

      <LinearGradient
        colors={["transparent", "rgba(11,41,68,0.2)", "rgba(11,41,68,0.94)"]}
        locations={[0, 0.45, 1]}
        style={styles.gradient}
      />

      <View style={styles.sponsoredBadge}>
        <Text style={styles.sponsoredText}>{t("swipe.sponsored")}</Text>
      </View>

      <View style={styles.infoOverlay}>
        <View style={styles.headlineRow}>
          {nativeAd.icon && (
            <NativeAsset assetType={NativeAssetType.ICON}>
              <Image source={{ uri: nativeAd.icon.url }} style={styles.icon} />
            </NativeAsset>
          )}
          <View style={styles.headlineTextWrap}>
            <NativeAsset assetType={NativeAssetType.HEADLINE}>
              <Text style={styles.headline} numberOfLines={1}>
                {nativeAd.headline}
              </Text>
            </NativeAsset>
            {!!nativeAd.advertiser && (
              <Text style={styles.advertiser} numberOfLines={1}>
                {nativeAd.advertiser}
              </Text>
            )}
          </View>
        </View>

        {!!nativeAd.body && (
          <NativeAsset assetType={NativeAssetType.BODY}>
            <Text style={styles.body} numberOfLines={2}>
              {nativeAd.body}
            </Text>
          </NativeAsset>
        )}

        <NativeAsset assetType={NativeAssetType.CALL_TO_ACTION}>
          <View style={styles.ctaButton}>
            <Text style={styles.ctaText} numberOfLines={1}>
              {nativeAd.callToAction}
            </Text>
          </View>
        </NativeAsset>
      </View>
    </NativeAdView>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    borderRadius: 24,
    overflow: "hidden",
    backgroundColor: colors.creamDeep,
    shadowColor: "#000",
    shadowOpacity: 0.2,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },
  centered: { alignItems: "center", justifyContent: "center" },
  media: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0, width: "100%", height: "100%" },
  gradient: { position: "absolute", left: 0, right: 0, bottom: 0, height: "55%" },
  sponsoredBadge: {
    position: "absolute",
    top: 18,
    left: 18,
    backgroundColor: "rgba(0,0,0,0.45)",
    borderRadius: 20,
    paddingVertical: 5,
    paddingHorizontal: 12,
  },
  sponsoredText: { color: "#fff", fontWeight: "700", fontSize: 11, letterSpacing: 0.5, textTransform: "uppercase" },
  infoOverlay: { position: "absolute", bottom: 0, left: 0, right: 0, padding: 20 },
  headlineRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  icon: { width: 36, height: 36, borderRadius: 8 },
  headlineTextWrap: { flex: 1 },
  headline: { color: "#fff", fontSize: 20, fontWeight: "800" },
  advertiser: { color: colors.accentSoft, fontSize: 12, marginTop: 1 },
  body: { color: "rgba(255,255,255,0.92)", fontSize: 14, marginTop: 8, lineHeight: 19 },
  ctaButton: {
    marginTop: 14,
    backgroundColor: colors.accent,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
  },
  ctaText: { color: "#fff", fontWeight: "700", fontSize: 15 },
});
