import { Pressable, Text, View, StyleSheet } from "react-native";
import { useTranslation } from "react-i18next";

import { colors } from "../theme";

interface Props {
  label: string;
  options: readonly string[];
  translatePrefix: string;
  values: string[];
  onChange: (values: string[]) => void;
  /** Caps how many can be selected at once (shown as "label (n/max)") — used
   * for Interests so a profile reads as a few standout things, not a wall
   * of tags. Premium filters leave this unset (no cap). */
  max?: number;
}

/** Multi-select variant of ChipSelect, used for premium filters (you can
 * filter to more than one religion, more than one race/ethnicity, etc.) —
 * ChipSelect itself stays single-select since that's still correct for a
 * profile's own fields (you only have one religion). */
export default function MultiChipSelect({ label, options, translatePrefix, values, onChange, max }: Props) {
  const { t } = useTranslation();
  const atMax = max != null && values.length >= max;

  function toggle(key: string) {
    if (values.includes(key)) {
      onChange(values.filter((v) => v !== key));
    } else if (!atMax) {
      onChange([...values, key]);
    }
  }

  return (
    <View>
      <Text style={styles.label}>
        {label}
        {max != null ? ` (${values.length}/${max})` : ""}
      </Text>
      <View style={styles.row}>
        {options.map((key) => {
          const selected = values.includes(key);
          const disabled = !selected && atMax;
          return (
            <Pressable
              key={key}
              style={[styles.chip, selected && styles.chipSelected, disabled && styles.chipDisabled]}
              onPress={() => toggle(key)}
              disabled={disabled}
            >
              <Text style={selected ? styles.chipTextSelected : disabled ? styles.chipTextDisabled : styles.chipText}>
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
  chipDisabled: { opacity: 0.4 },
  chipText: { color: colors.ink },
  chipTextSelected: { color: "#fff" },
  chipTextDisabled: { color: colors.muted },
});
