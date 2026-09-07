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
  value: string | null;
  onChange: (value: string) => void;
  disabled?: boolean;
}

/** Tap-to-open modal picker — used instead of free-text inputs or
 * @react-native-picker/picker (a native module we'd need to rebuild for;
 * see feedback_no_eas_builds_without_asking) wherever a field has a fixed
 * set of choices. */
export default function SelectDropdown({ label, placeholder, options, value, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const selected = options.find((o) => o.key === value);

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <Pressable
        style={[styles.field, disabled && styles.fieldDisabled]}
        onPress={() => !disabled && setOpen(true)}
        disabled={disabled}
      >
        <Text style={selected ? styles.fieldText : styles.placeholderText}>{selected ? selected.label : placeholder}</Text>
        <Ionicons name="chevron-down" size={18} color={colors.muted} />
      </Pressable>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <View style={styles.sheet} onStartShouldSetResponder={() => true}>
            <Text style={styles.sheetTitle}>{label}</Text>
            <FlatList
              data={options}
              keyExtractor={(item) => item.key}
              style={styles.list}
              renderItem={({ item }) => (
                <Pressable
                  style={styles.option}
                  onPress={() => {
                    onChange(item.key);
                    setOpen(false);
                  }}
                >
                  <Text style={item.key === value ? styles.optionTextSelected : styles.optionText}>{item.label}</Text>
                  {item.key === value && <Ionicons name="checkmark" size={18} color={colors.accent} />}
                </Pressable>
              )}
            />
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
  fieldText: { fontSize: 16, color: colors.ink },
  placeholderText: { fontSize: 16, color: colors.muted },
  backdrop: { flex: 1, backgroundColor: "rgba(11,41,68,0.4)", justifyContent: "flex-end" },
  sheet: { backgroundColor: colors.white, borderTopLeftRadius: 20, borderTopRightRadius: 20, maxHeight: "70%", padding: 20 },
  sheetTitle: { fontSize: 16, fontWeight: "700", color: colors.navy, marginBottom: 12 },
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
});
