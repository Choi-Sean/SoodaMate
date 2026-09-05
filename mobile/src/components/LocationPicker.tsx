import { useState } from "react";
import { ActivityIndicator, Alert, Pressable, Text, TextInput, View, StyleSheet } from "react-native";
import * as Location from "expo-location";
import { useTranslation } from "react-i18next";

import { PRESET_CITIES, type PresetCity } from "../constants/presetCities";
import { colors } from "../theme";

interface Props {
  lat: number | null;
  lng: number | null;
  onChange: (lat: number, lng: number) => void;
}

export default function LocationPicker({ lat, lng, onChange }: Props) {
  const { t } = useTranslation();
  const [detecting, setDetecting] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [latInput, setLatInput] = useState(lat != null ? String(lat) : "");
  const [lngInput, setLngInput] = useState(lng != null ? String(lng) : "");

  async function handleAutoDetect() {
    setDetecting(true);
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted") {
        Alert.alert(t("location.permissionDeniedTitle"), t("location.permissionDeniedBody"));
        setManualOpen(true);
        return;
      }
      const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      onChange(position.coords.latitude, position.coords.longitude);
      setManualOpen(false);
    } catch {
      Alert.alert(t("common.somethingWentWrong"));
      setManualOpen(true);
    } finally {
      setDetecting(false);
    }
  }

  function handlePickCity(city: PresetCity) {
    onChange(city.lat, city.lng);
    setLatInput(String(city.lat));
    setLngInput(String(city.lng));
  }

  function handleManualSubmit() {
    const parsedLat = Number(latInput);
    const parsedLng = Number(lngInput);
    if (Number.isNaN(parsedLat) || Number.isNaN(parsedLng)) {
      Alert.alert(t("common.somethingWentWrong"));
      return;
    }
    onChange(parsedLat, parsedLng);
  }

  return (
    <View>
      <Text style={styles.label}>{t("location.title")}</Text>

      {lat != null && lng != null && (
        <Text style={styles.currentValue}>{t("location.currentValue", { lat: lat.toFixed(4), lng: lng.toFixed(4) })}</Text>
      )}

      <Pressable style={styles.detectButton} onPress={handleAutoDetect} disabled={detecting}>
        {detecting ? (
          <ActivityIndicator color={colors.white} />
        ) : (
          <Text style={styles.detectButtonText}>{t("location.useMyLocation")}</Text>
        )}
      </Pressable>

      <Pressable onPress={() => setManualOpen((v) => !v)}>
        <Text style={styles.manualToggle}>{t("location.enterManually")}</Text>
      </Pressable>

      {manualOpen && (
        <View style={styles.manualSection}>
          <View style={styles.cityGrid}>
            {PRESET_CITIES.map((city) => (
              <Pressable key={city.key} style={styles.cityChip} onPress={() => handlePickCity(city)}>
                <Text style={styles.cityChipText}>{city.label}</Text>
              </Pressable>
            ))}
          </View>

          <View style={styles.row}>
            <TextInput
              style={[styles.input, styles.smallInput]}
              keyboardType="numbers-and-punctuation"
              value={latInput}
              onChangeText={setLatInput}
              placeholder={t("location.latitude")}
            />
            <TextInput
              style={[styles.input, styles.smallInput]}
              keyboardType="numbers-and-punctuation"
              value={lngInput}
              onChangeText={setLngInput}
              placeholder={t("location.longitude")}
            />
            <Pressable style={styles.manualApplyButton} onPress={handleManualSubmit}>
              <Text style={styles.manualApplyText}>{t("location.apply")}</Text>
            </Pressable>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  label: { fontSize: 14, fontWeight: "600", marginTop: 12, marginBottom: 8, color: colors.muted },
  currentValue: { color: colors.ink, marginBottom: 8 },
  detectButton: {
    backgroundColor: colors.navy,
    borderRadius: 10,
    padding: 14,
    alignItems: "center",
    marginBottom: 10,
  },
  detectButtonText: { color: colors.white, fontSize: 15, fontWeight: "600" },
  manualToggle: { color: colors.accentDark, fontWeight: "500", marginBottom: 8 },
  manualSection: { marginBottom: 12 },
  cityGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 8 },
  cityChip: { borderWidth: 1, borderColor: colors.border, borderRadius: 20, paddingVertical: 8, paddingHorizontal: 14 },
  cityChipText: { color: colors.ink, fontSize: 13 },
  row: { flexDirection: "row", gap: 8, alignItems: "center" },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 12, fontSize: 14 },
  smallInput: { flex: 1 },
  manualApplyButton: { backgroundColor: colors.accent, borderRadius: 10, paddingVertical: 12, paddingHorizontal: 16 },
  manualApplyText: { color: colors.white, fontWeight: "600" },
});
