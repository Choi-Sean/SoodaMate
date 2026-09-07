import { Text, View, StyleSheet } from "react-native";
import { useTranslation } from "react-i18next";

import { colors } from "../theme";

interface Props {
  percent: number;
}

export default function ProfileCompletenessBar({ percent }: Props) {
  const { t } = useTranslation();
  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.label}>{t("editProfile.completenessLabel")}</Text>
        <Text style={styles.percent}>{percent}%</Text>
      </View>
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${percent}%` }]} />
      </View>
      <Text style={styles.hint}>{t("editProfile.completenessHint")}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 16, marginBottom: 8 },
  headerRow: { flexDirection: "row", justifyContent: "space-between", marginBottom: 6 },
  label: { fontSize: 13, fontWeight: "700", color: colors.navy },
  percent: { fontSize: 13, fontWeight: "800", color: colors.accentDark },
  track: { height: 8, borderRadius: 4, backgroundColor: colors.creamDeep, overflow: "hidden" },
  fill: { height: 8, borderRadius: 4, backgroundColor: colors.accent },
  hint: { fontSize: 12, color: colors.muted, marginTop: 6 },
});
