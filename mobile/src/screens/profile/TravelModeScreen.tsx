import { useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, Text, TextInput, View, StyleSheet } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { getMyProfile, setTravelMode, clearTravelMode } from "../../api/profiles";
import { colors } from "../../theme";

interface PresetCity {
  key: string;
  label: string;
  lat: number;
  lng: number;
}

// No geocoding API or GPS capture exists anywhere in the app yet, so v1
// travel mode is a short preset list + manual lat/lng entry rather than a
// map picker.
const PRESET_CITIES: PresetCity[] = [
  { key: "seoul", label: "Seoul", lat: 37.5665, lng: 126.978 },
  { key: "busan", label: "Busan", lat: 35.1796, lng: 129.0756 },
  { key: "incheon", label: "Incheon", lat: 37.4563, lng: 126.7052 },
  { key: "tokyo", label: "Tokyo", lat: 35.6762, lng: 139.6503 },
  { key: "osaka", label: "Osaka", lat: 34.6937, lng: 135.5023 },
  { key: "newyork", label: "New York", lat: 40.7128, lng: -74.006 },
  { key: "losangeles", label: "Los Angeles", lat: 34.0522, lng: -118.2437 },
  { key: "london", label: "London", lat: 51.5072, lng: -0.1276 },
  { key: "paris", label: "Paris", lat: 48.8566, lng: 2.3522 },
  { key: "beijing", label: "Beijing", lat: 39.9042, lng: 116.4074 },
  { key: "shanghai", label: "Shanghai", lat: 31.2304, lng: 121.4737 },
];

export default function TravelModeScreen() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: profile, isLoading } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });

  const [mode, setMode] = useState<"preset" | "manual">("preset");
  const [selectedCity, setSelectedCity] = useState<PresetCity | null>(null);
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [durationHours, setDurationHours] = useState(24);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isActive = !!profile?.travel_expires_at && new Date(profile.travel_expires_at) > new Date();

  async function handleActivate() {
    setError(null);
    let targetLat: number;
    let targetLng: number;
    if (mode === "preset") {
      if (!selectedCity) return;
      targetLat = selectedCity.lat;
      targetLng = selectedCity.lng;
    } else {
      targetLat = Number(lat);
      targetLng = Number(lng);
      if (Number.isNaN(targetLat) || Number.isNaN(targetLng)) {
        setError(t("common.somethingWentWrong"));
        return;
      }
    }
    setSaving(true);
    try {
      await setTravelMode(targetLat, targetLng, durationHours);
      await queryClient.invalidateQueries({ queryKey: ["myProfile"] });
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setSaving(false);
    }
  }

  async function handleTurnOff() {
    setSaving(true);
    try {
      await clearTravelMode();
      await queryClient.invalidateQueries({ queryKey: ["myProfile"] });
    } catch (e: any) {
      Alert.alert(t("common.somethingWentWrong"));
    } finally {
      setSaving(false);
    }
  }

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>{t("travel.title")}</Text>
      <Text style={styles.subtitle}>{t("travel.subtitle")}</Text>

      {isActive && (
        <View style={styles.activeBanner}>
          <Text style={styles.activeBannerText}>{t("travel.active")}</Text>
          <Text style={styles.activeBannerSub}>
            {t("travel.activeUntil", { date: new Date(profile!.travel_expires_at!).toLocaleString() })}
          </Text>
          <Pressable style={styles.turnOffButton} onPress={handleTurnOff} disabled={saving}>
            {saving ? <ActivityIndicator color={colors.danger} /> : <Text style={styles.turnOffText}>{t("travel.turnOff")}</Text>}
          </Pressable>
        </View>
      )}

      {error && <Text style={styles.error}>{error}</Text>}

      <View style={styles.row}>
        <Pressable style={[styles.modeChip, mode === "preset" && styles.modeChipSelected]} onPress={() => setMode("preset")}>
          <Text style={mode === "preset" ? styles.modeChipTextSelected : styles.modeChipText}>{t("travel.presetCity")}</Text>
        </Pressable>
        <Pressable style={[styles.modeChip, mode === "manual" && styles.modeChipSelected]} onPress={() => setMode("manual")}>
          <Text style={mode === "manual" ? styles.modeChipTextSelected : styles.modeChipText}>{t("travel.manualEntry")}</Text>
        </Pressable>
      </View>

      {mode === "preset" ? (
        <View style={styles.cityGrid}>
          {PRESET_CITIES.map((city) => (
            <Pressable
              key={city.key}
              style={[styles.cityChip, selectedCity?.key === city.key && styles.cityChipSelected]}
              onPress={() => setSelectedCity(city)}
            >
              <Text style={selectedCity?.key === city.key ? styles.cityChipTextSelected : styles.cityChipText}>{city.label}</Text>
            </Pressable>
          ))}
        </View>
      ) : (
        <View>
          <Text style={styles.label}>{t("travel.latitude")}</Text>
          <TextInput style={styles.input} keyboardType="numbers-and-punctuation" value={lat} onChangeText={setLat} placeholder="37.5665" />
          <Text style={styles.label}>{t("travel.longitude")}</Text>
          <TextInput style={styles.input} keyboardType="numbers-and-punctuation" value={lng} onChangeText={setLng} placeholder="126.9780" />
        </View>
      )}

      <Text style={styles.label}>{t("travel.duration")}</Text>
      <View style={styles.row}>
        <Pressable style={[styles.modeChip, durationHours === 24 && styles.modeChipSelected]} onPress={() => setDurationHours(24)}>
          <Text style={durationHours === 24 ? styles.modeChipTextSelected : styles.modeChipText}>{t("travel.hours24")}</Text>
        </Pressable>
        <Pressable style={[styles.modeChip, durationHours === 168 && styles.modeChipSelected]} onPress={() => setDurationHours(168)}>
          <Text style={durationHours === 168 ? styles.modeChipTextSelected : styles.modeChipText}>{t("travel.days7")}</Text>
        </Pressable>
      </View>

      <Pressable style={styles.primaryButton} onPress={handleActivate} disabled={saving}>
        {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>{t("travel.activate")}</Text>}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, flexGrow: 1, backgroundColor: colors.white },
  centered: { flex: 1, alignItems: "center", justifyContent: "center" },
  title: { fontSize: 24, fontWeight: "700", marginTop: 8, marginBottom: 4, color: colors.navy },
  subtitle: { color: colors.muted, marginBottom: 20 },
  error: { color: colors.danger, marginBottom: 12 },
  activeBanner: { backgroundColor: colors.creamDeep, borderRadius: 12, padding: 16, marginBottom: 20 },
  activeBannerText: { fontWeight: "700", color: colors.navy, fontSize: 16, marginBottom: 4 },
  activeBannerSub: { color: colors.muted, marginBottom: 12 },
  turnOffButton: { alignSelf: "flex-start" },
  turnOffText: { color: colors.danger, fontWeight: "600" },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8, alignItems: "center", marginBottom: 12 },
  label: { fontSize: 14, fontWeight: "600", marginTop: 12, marginBottom: 8, color: colors.muted },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 14, marginBottom: 12, fontSize: 16 },
  modeChip: { borderWidth: 1, borderColor: colors.border, borderRadius: 20, paddingVertical: 8, paddingHorizontal: 16 },
  modeChipSelected: { backgroundColor: colors.navy, borderColor: colors.navy },
  modeChipText: { color: colors.ink },
  modeChipTextSelected: { color: "#fff", fontWeight: "600" },
  cityGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 8 },
  cityChip: { borderWidth: 1, borderColor: colors.border, borderRadius: 20, paddingVertical: 8, paddingHorizontal: 14 },
  cityChipSelected: { backgroundColor: colors.accent, borderColor: colors.accent },
  cityChipText: { color: colors.ink, fontSize: 13 },
  cityChipTextSelected: { color: "#fff", fontSize: 13, fontWeight: "600" },
  primaryButton: { backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: "center", marginTop: 16, marginBottom: 24 },
  primaryButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
});
