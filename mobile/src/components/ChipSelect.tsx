import { Pressable, Text, View, StyleSheet } from "react-native";
import { useTranslation } from "react-i18next";

import { colors } from "../theme";

interface Props {
  label: string;
  options: readonly string[];
  translatePrefix: string;
  value: string | null;
  onChange: (value: string | null) => void;
}

/** Single-select chip row shared by the race/ethnicity and religion pickers
 * in ProfileSetupScreen and EditProfileScreen. Tapping the already-selected
 * chip clears it (these fields are optional). */
export default function ChipSelect({ label, options, translatePrefix, value, onChange }: Props) {
  const { t } = useTranslation();

  return (
    <View>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.row}>
        {options.map((key) => (
          <Pressable
            key={key}
            style={[styles.chip, value === key && styles.chipSelected]}
            onPress={() => onChange(value === key ? null : key)}
          >
            <Text style={value === key ? styles.chipTextSelected : styles.chipText}>
              {t(`${translatePrefix}.${key}`)}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  label: { fontSize: 14, fontWeight: "600", marginTop: 12, marginBottom: 8, color: colors.muted },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { borderWidth: 1, borderColor: colors.border, borderRadius: 20, paddingVertical: 8, paddingHorizontal: 16 },
  chipSelected: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipText: { color: colors.ink },
  chipTextSelected: { color: "#fff" },
});
