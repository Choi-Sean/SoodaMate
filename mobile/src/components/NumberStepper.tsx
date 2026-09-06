import { Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { colors } from "../theme";

interface Props {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
  formatValue?: (value: number) => string;
}

/** Plain +/- stepper instead of a slider — @react-native-community/slider
 * would be a new native dependency, and this app isn't rebuilding on every
 * change right now (see feedback_no_eas_builds_without_asking memory). */
export default function NumberStepper({ label, value, min, max, step = 1, onChange, formatValue }: Props) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.controls}>
        <Pressable
          style={styles.button}
          onPress={() => onChange(Math.max(min, value - step))}
          disabled={value <= min}
        >
          <Ionicons name="remove" size={16} color={value <= min ? colors.border : colors.accentDark} />
        </Pressable>
        <Text style={styles.value}>{formatValue ? formatValue(value) : value}</Text>
        <Pressable
          style={styles.button}
          onPress={() => onChange(Math.min(max, value + step))}
          disabled={value >= max}
        >
          <Ionicons name="add" size={16} color={value >= max ? colors.border : colors.accentDark} />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 10 },
  label: { fontSize: 15, color: colors.ink },
  controls: { flexDirection: "row", alignItems: "center", gap: 12 },
  button: {
    width: 32,
    height: 32,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  value: { fontSize: 15, fontWeight: "700", color: colors.navy, minWidth: 56, textAlign: "center" },
});
