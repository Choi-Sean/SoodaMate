import { useState } from "react";
import { FlatList, Modal, Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { colors } from "../theme";

export interface DropdownOption {
  key: string;
  label: string;
}

interface Props {
  label: string;
  placeholder: string;
  options: DropdownOption[];
  values: string[];
  onChange: (values: string[]) => void;
  disabled?: boolean;
}

/** Same tap-to-open modal-sheet pattern as SelectDropdown, but each row
 * toggles in/out of `values` instead of closing the sheet — for "which of
 * these apply" fields (languages, ethnicity) rather than single-choice
 * ones. Selections are only committed on "Done" so backing out via the
 * backdrop discards an in-progress change, matching SelectDropdown's
 * closed-field summary style. */
export default function MultiSelectDropdown({ label, placeholder, options, values, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<string[]>(values);

  function openSheet() {
    if (disabled) return;
    setDraft(values);
    setOpen(true);
  }

  function toggle(key: string) {
    setDraft((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));
  }

  function confirm() {
    onChange(draft);
    setOpen(false);
  }

  const summary =
    values.length === 0
      ? placeholder
      : values.length === 1
        ? options.find((o) => o.key === values[0])?.label ?? placeholder
        : `${options.find((o) => o.key === values[0])?.label ?? values[0]} +${values.length - 1}`;

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <Pressable style={[styles.field, disabled && styles.fieldDisabled]} onPress={openSheet} disabled={disabled}>
        <Text style={values.length > 0 ? styles.fieldText : styles.placeholderText} numberOfLines={1}>
          {summary}
        </Text>
        <Ionicons name="chevron-down" size={18} color={colors.muted} />
      </Pressable>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <View style={styles.sheet} onStartShouldSetResponder={() => true}>
            <View style={styles.sheetHeader}>
              <Text style={styles.sheetTitle}>{label}</Text>
              <Pressable onPress={confirm} hitSlop={8}>
                <Text style={styles.doneText}>{"✓"}</Text>
              </Pressable>
            </View>
            <FlatList
              data={options}
              keyExtractor={(item) => item.key}
              style={styles.list}
              renderItem={({ item }) => {
                const selected = draft.includes(item.key);
                return (
                  <Pressable style={styles.option} onPress={() => toggle(item.key)}>
                    <Text style={selected ? styles.optionTextSelected : styles.optionText}>{item.label}</Text>
                    <Ionicons
                      name={selected ? "checkbox" : "square-outline"}
                      size={20}
                      color={selected ? colors.accent : colors.muted}
                    />
                  </Pressable>
                );
              }}
            />
            <Pressable style={styles.confirmButton} onPress={confirm}>
              <Text style={styles.confirmButtonText}>Done</Text>
            </Pressable>
          </View>
        </Pressable>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginBottom: 12 },
  label: { fontSize: 14, fontWeight: "600", marginTop: 12, marginBottom: 8, color: colors.muted },
  field: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 14,
  },
  fieldDisabled: { backgroundColor: colors.creamDeep },
  fieldText: { fontSize: 16, color: colors.ink, flex: 1, marginRight: 8 },
  placeholderText: { fontSize: 16, color: colors.muted, flex: 1, marginRight: 8 },
  backdrop: { flex: 1, backgroundColor: "rgba(11,41,68,0.4)", justifyContent: "flex-end" },
  sheet: { backgroundColor: colors.white, borderTopLeftRadius: 20, borderTopRightRadius: 20, maxHeight: "70%", padding: 20 },
  sheetHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  sheetTitle: { fontSize: 16, fontWeight: "700", color: colors.navy },
  doneText: { fontSize: 16, fontWeight: "700", color: colors.accentDark },
  list: { flexGrow: 0 },
  option: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  optionText: { fontSize: 15, color: colors.ink },
  optionTextSelected: { fontSize: 15, color: colors.accentDark, fontWeight: "700" },
  confirmButton: { backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: "center", marginTop: 16 },
  confirmButtonText: { color: "#fff", fontWeight: "700", fontSize: 15 },
});
