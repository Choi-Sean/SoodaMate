import { useState } from "react";
import { Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import { colors } from "../theme";

interface Props {
  valueCm: number;
  onChange: (valueCm: number) => void;
  min?: number;
  max?: number;
}

function cmToFtIn(cm: number): { ft: number; inch: number } {
  const totalInches = Math.round(cm / 2.54);
  return { ft: Math.floor(totalInches / 12), inch: totalInches % 12 };
}

function ftInToCm(ft: number, inch: number): number {
  return Math.round((ft * 12 + inch) * 2.54);
}

/** +/- stepper (no native slider — see NumberStepper's own note) with a
 * cm/ft toggle. Always stores/sends centimeters; ft/in is display-only,
 * converted at render and on each step. */
export default function HeightInput({ valueCm, onChange, min = 130, max = 220 }: Props) {
  const { t } = useTranslation();
  const [unit, setUnit] = useState<"cm" | "ft">("cm");
  const { ft, inch } = cmToFtIn(valueCm);

  function stepCm(delta: number) {
    onChange(Math.min(max, Math.max(min, valueCm + delta)));
  }

  function stepInches(delta: number) {
    const totalInches = Math.round(valueCm / 2.54) + delta;
    const nextCm = Math.round(totalInches * 2.54);
    onChange(Math.min(max, Math.max(min, nextCm)));
  }

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.label}>{t("profileSetup.heightCm")}</Text>
        <View style={styles.unitToggle}>
          <Pressable style={[styles.unitButton, unit === "cm" && styles.unitButtonActive]} onPress={() => setUnit("cm")}>
            <Text style={unit === "cm" ? styles.unitTextActive : styles.unitText}>cm</Text>
          </Pressable>
          <Pressable style={[styles.unitButton, unit === "ft" && styles.unitButtonActive]} onPress={() => setUnit("ft")}>
            <Text style={unit === "ft" ? styles.unitTextActive : styles.unitText}>ft</Text>
          </Pressable>
        </View>
      </View>

      <View style={styles.controls}>
        <Pressable style={styles.button} onPress={() => (unit === "cm" ? stepCm(-1) : stepInches(-1))} disabled={valueCm <= min}>
          <Ionicons name="remove" size={16} color={valueCm <= min ? colors.border : colors.accentDark} />
        </Pressable>
        <Text style={styles.value}>{unit === "cm" ? `${valueCm} cm` : `${ft}'${inch}"`}</Text>
        <Pressable style={styles.button} onPress={() => (unit === "cm" ? stepCm(1) : stepInches(1))} disabled={valueCm >= max}>
          <Ionicons name="add" size={16} color={valueCm >= max ? colors.border : colors.accentDark} />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { paddingVertical: 10 },
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  label: { fontSize: 15, color: colors.ink },
  unitToggle: { flexDirection: "row", borderWidth: 1, borderColor: colors.border, borderRadius: 8, overflow: "hidden" },
  unitButton: { paddingVertical: 4, paddingHorizontal: 10 },
  unitButtonActive: { backgroundColor: colors.accent },
  unitText: { fontSize: 12, color: colors.muted, fontWeight: "600" },
  unitTextActive: { fontSize: 12, color: "#fff", fontWeight: "700" },
  controls: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 16 },
  button: {
    width: 32,
    height: 32,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  value: { fontSize: 18, fontWeight: "700", color: colors.navy, minWidth: 84, textAlign: "center" },
});
