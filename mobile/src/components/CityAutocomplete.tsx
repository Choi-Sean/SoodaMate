import { useMemo, useState } from "react";
import { Pressable, Text, TextInput, View, StyleSheet } from "react-native";
import { City, Country, State } from "country-state-city";

import { SUPPORTED_COUNTRY_CODES } from "../constants/supportedCountries";
import { colors } from "../theme";

interface Props {
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}

interface CityEntry {
  key: string;
  searchText: string;
  label: string;
}

// Lazily built and cached on first use, NOT at module load — this scans
// every city in ~30 countries (the US alone is tens of thousands of rows),
// which is far too heavy to run as a side effect of merely importing this
// file (that import happens eagerly at app boot via ProfileStack's static
// imports, long before anyone opens Edit Profile).
let cachedAllCities: CityEntry[] | null = null;

function getAllCities(): CityEntry[] {
  if (cachedAllCities) return cachedAllCities;
  cachedAllCities = SUPPORTED_COUNTRY_CODES.flatMap((countryCode) => {
    const country = Country.getCountryByCode(countryCode);
    return (
      City.getCitiesOfCountry(countryCode)?.map((city) => {
        const state = city.stateCode ? State.getStateByCodeAndCountry(city.stateCode, countryCode) : null;
        const label = [city.name, state?.name, country?.name].filter(Boolean).join(", ");
        return { key: `${countryCode}-${city.stateCode}-${city.name}`, searchText: city.name.toLowerCase(), label };
      }) ?? []
    );
  });
  return cachedAllCities;
}

/** Free-text field with a live suggestion dropdown, resolving a typed city
 * name to "City, State, Country" — used for Hometown. Not a strict picker
 * (typing something that matches nothing still just saves the raw text),
 * so it degrades gracefully for small towns not in the dataset. */
export default function CityAutocomplete({ label, placeholder, value, onChange }: Props) {
  const [focused, setFocused] = useState(false);
  const allCities = useMemo(() => getAllCities(), []);

  const suggestions = useMemo(() => {
    const query = value.trim().toLowerCase();
    if (query.length < 2) return [];
    const matches: CityEntry[] = [];
    for (const city of allCities) {
      if (city.searchText.startsWith(query)) {
        matches.push(city);
        if (matches.length >= 8) break;
      }
    }
    return matches;
  }, [value, allCities]);

  return (
    <View>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={styles.input}
        placeholder={placeholder}
        value={value}
        onChangeText={onChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setTimeout(() => setFocused(false), 150)}
      />
      {focused && suggestions.length > 0 && (
        <View style={styles.suggestionBox}>
          {suggestions.map((s) => (
            <Pressable
              key={s.key}
              style={styles.suggestionRow}
              onPress={() => {
                onChange(s.label);
                setFocused(false);
              }}
            >
              <Text style={styles.suggestionText}>{s.label}</Text>
            </Pressable>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  label: { fontSize: 14, fontWeight: "600", marginBottom: 8, color: colors.muted },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 14, fontSize: 16 },
  suggestionBox: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    marginTop: 4,
    backgroundColor: colors.white,
    overflow: "hidden",
  },
  suggestionRow: { padding: 12, borderBottomWidth: 1, borderBottomColor: colors.border },
  suggestionText: { fontSize: 14, color: colors.ink },
});
