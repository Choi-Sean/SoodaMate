import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View, StyleSheet } from "react-native";
import * as Location from "expo-location";
import { Country, State, City } from "country-state-city";
import { useTranslation } from "react-i18next";

import SelectDropdown, { DropdownOption } from "./SelectDropdown";
import { SUPPORTED_COUNTRY_CODES } from "../constants/supportedCountries";
import { colors } from "../theme";
import { showAlert } from "../utils/alert";

interface Props {
  lat: number | null;
  lng: number | null;
  onChange: (lat: number, lng: number) => void;
  required?: boolean;
}

interface Place {
  city: string;
  region: string;
  country: string;
}

/** Reverse-geocodes lat/lng into a human "City, Region, Country" string via
 * BigDataCloud's free, no-API-key-required client geocoding endpoint — the
 * only thing users ever see is that label, never raw coordinates (lat/lng
 * still get sent to the backend for distance math, just not displayed). */
async function reverseGeocode(lat: number, lng: number): Promise<Place | null> {
  try {
    const resp = await fetch(
      `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lng}&localityLanguage=en`
    );
    if (!resp.ok) return null;
    const data = await resp.json();
    return {
      city: data.city || data.locality || "",
      region: data.principalSubdivision || "",
      country: data.countryName || "",
    };
  } catch {
    return null;
  }
}

interface ZipLookup {
  lat: number;
  lng: number;
  place: Place;
}

/** Zippopotam.us — free, no key, US ZIP -> place name + lat/lng. Used only
 * for the US (see below); every other supported country still goes through
 * the Country -> State -> City cascade, since "one ZIP-like code" isn't a
 * universal concept and the cascade dataset already covers them well. */
async function lookupUsZip(zip: string): Promise<ZipLookup | null> {
  try {
    const resp = await fetch(`https://api.zippopotam.us/us/${encodeURIComponent(zip)}`);
    if (!resp.ok) return null;
    const data = await resp.json();
    const place = data.places?.[0];
    if (!place) return null;
    return {
      lat: Number(place.latitude),
      lng: Number(place.longitude),
      place: { city: place["place name"], region: place["state abbreviation"], country: "United States" },
    };
  } catch {
    return null;
  }
}

function placeLabel(place: Place): string {
  return [place.city, place.region, place.country].filter(Boolean).join(", ");
}

export default function LocationPicker({ lat, lng, onChange, required }: Props) {
  const { t } = useTranslation();
  const [detecting, setDetecting] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [currentPlace, setCurrentPlace] = useState<Place | null>(null);
  const [resolvingCurrent, setResolvingCurrent] = useState(false);

  const [countryCode, setCountryCode] = useState<string | null>(null);
  const [stateCode, setStateCode] = useState<string | null>(null);
  const [cityName, setCityName] = useState<string | null>(null);

  const [zip, setZip] = useState("");
  const [zipLookingUp, setZipLookingUp] = useState(false);
  const [zipError, setZipError] = useState(false);

  // Resolve whatever lat/lng the profile already has into a readable label
  // on mount / whenever it changes from outside this component (e.g. after
  // "use my current location" is confirmed elsewhere).
  useEffect(() => {
    if (lat == null || lng == null) return;
    let cancelled = false;
    setResolvingCurrent(true);
    reverseGeocode(lat, lng).then((place) => {
      if (!cancelled) setCurrentPlace(place);
      setResolvingCurrent(false);
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lat, lng]);

  async function handleAutoDetect() {
    setDetecting(true);
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted") {
        showAlert(t("location.permissionDeniedTitle"), t("location.permissionDeniedBody"));
        setManualOpen(true);
        return;
      }
      const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      onChange(position.coords.latitude, position.coords.longitude);
      setManualOpen(false);
    } catch {
      showAlert(t("common.somethingWentWrong"));
      setManualOpen(true);
    } finally {
      setDetecting(false);
    }
  }

  const countryOptions: DropdownOption[] = Country.getAllCountries()
    .filter((c) => (SUPPORTED_COUNTRY_CODES as readonly string[]).includes(c.isoCode))
    .map((c) => ({ key: c.isoCode, label: `${c.flag} ${c.name}` }));
  const stateOptions: DropdownOption[] = countryCode
    ? State.getStatesOfCountry(countryCode).map((s) => ({ key: s.isoCode, label: s.name }))
    : [];
  const cityOptions: DropdownOption[] = (
    countryCode && stateCode ? City.getCitiesOfState(countryCode, stateCode) : []
  ).map((c) => ({ key: c.name, label: c.name }));

  function handlePickCity(name: string) {
    setCityName(name);
    if (!countryCode || !stateCode) return;
    const city = City.getCitiesOfState(countryCode, stateCode).find((c) => c.name === name);
    const country = Country.getCountryByCode(countryCode);
    const state = State.getStateByCodeAndCountry(stateCode, countryCode);
    if (city && city.latitude && city.longitude) {
      onChange(Number(city.latitude), Number(city.longitude));
      setCurrentPlace({ city: name, region: state?.name ?? "", country: country?.name ?? "" });
    } else if (state && state.latitude && state.longitude) {
      // Some cities in this dataset are missing coordinates — fall back to
      // the state's centroid rather than leaving location unset.
      onChange(Number(state.latitude), Number(state.longitude));
      setCurrentPlace({ city: name, region: state?.name ?? "", country: country?.name ?? "" });
    }
  }

  async function handleZipLookup() {
    if (!zip.trim()) return;
    setZipLookingUp(true);
    setZipError(false);
    const result = await lookupUsZip(zip.trim());
    setZipLookingUp(false);
    if (!result) {
      setZipError(true);
      return;
    }
    onChange(result.lat, result.lng);
    setCurrentPlace(result.place);
  }

  const isUs = countryCode === "US";

  return (
    <View>
      <Text style={styles.label}>
        {t("location.title")}
        {required && <Text style={styles.requiredStar}> *</Text>}
      </Text>

      {resolvingCurrent && <ActivityIndicator size="small" color={colors.accent} style={styles.resolvingSpinner} />}
      {!resolvingCurrent && currentPlace && <Text style={styles.currentValue}>{placeLabel(currentPlace)}</Text>}
      {!resolvingCurrent && !currentPlace && lat != null && lng != null && (
        <Text style={styles.currentValue}>{t("location.currentValueUnknown")}</Text>
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
          <SelectDropdown
            label={t("location.country")}
            placeholder={t("location.countryPlaceholder")}
            options={countryOptions}
            value={countryCode}
            onChange={(v) => {
              setCountryCode(v);
              setStateCode(null);
              setCityName(null);
              setZip("");
              setZipError(false);
            }}
          />

          {isUs ? (
            <View style={styles.zipRow}>
              <TextInput
                style={styles.zipInput}
                placeholder={t("location.zipPlaceholder")}
                value={zip}
                onChangeText={setZip}
                keyboardType="number-pad"
                maxLength={5}
              />
              <Pressable style={styles.zipApplyButton} onPress={handleZipLookup} disabled={zipLookingUp || zip.trim().length < 5}>
                {zipLookingUp ? <ActivityIndicator color={colors.white} /> : <Text style={styles.zipApplyText}>{t("location.apply")}</Text>}
              </Pressable>
            </View>
          ) : (
            <>
              <SelectDropdown
                label={t("location.state")}
                placeholder={t("location.statePlaceholder")}
                options={stateOptions}
                value={stateCode}
                disabled={!countryCode}
                onChange={(v) => {
                  setStateCode(v);
                  setCityName(null);
                }}
              />
              <SelectDropdown
                label={t("location.city")}
                placeholder={t("location.cityPlaceholder")}
                options={cityOptions}
                value={cityName}
                disabled={!stateCode}
                onChange={handlePickCity}
              />
            </>
          )}
          {zipError && <Text style={styles.zipError}>{t("location.zipNotFound")}</Text>}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  label: { fontSize: 14, fontWeight: "600", marginTop: 12, marginBottom: 8, color: colors.muted },
  requiredStar: { color: colors.danger },
  currentValue: { color: colors.ink, marginBottom: 8, fontWeight: "500" },
  resolvingSpinner: { alignSelf: "flex-start", marginBottom: 8 },
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
  zipRow: { flexDirection: "row", gap: 8, alignItems: "center", marginTop: 4 },
  zipInput: { flex: 1, borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 12, fontSize: 15 },
  zipApplyButton: { backgroundColor: colors.accent, borderRadius: 10, paddingVertical: 12, paddingHorizontal: 16 },
  zipApplyText: { color: colors.white, fontWeight: "600" },
  zipError: { color: colors.danger, fontSize: 12.5, marginTop: 6 },
});
