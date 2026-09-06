import { Pressable, Text, View, StyleSheet } from "react-native";
import { useTranslation } from "react-i18next";

import { colors } from "../theme";

interface Props {
  label: string;
  options: readonly string[];
  translatePrefix: string;
  values: string[];
  onChange: (values: string[]) => void;
}

/** Multi-select variant of ChipSelect, used for premium filters (you can
 * filter to more than one religion, more than one race/ethnicity, etc.) —
 * ChipSelect itself stays single-select since that's still correct for a
 * profile's own fields (you only have one religion). */
export default function MultiChipSelect({ label, options, translatePrefix, values, onChange }: Props) {
  const { t } = useTranslation();

  function toggle(key: string) {
    onChange(values.includes(key) ? values.filter((v) => v !== key) : [...values, key]);
  }

  return (
    <View>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.row}>
        {options.map((key) => {
          const selected = values.includes(key);
          return (
            <Pressable key={key} style={[styles.chip, selected && styles.chipSelected]} onPress={() => toggle(key)}>
              <Text style={selected ? styles.chipTextSelected : styles.chipText}>
                {t(`${translatePrefix}.${key}`)}
              </Text>
            </Pressable>
          );
        })}
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
