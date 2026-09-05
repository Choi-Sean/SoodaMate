import { useState } from "react";
import { ActivityIndicator, Alert, Linking, Pressable, Switch, Text, View, StyleSheet } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import { deleteAccount } from "../../api/account";
import { getMyProfile, setIncognito } from "../../api/profiles";
import { useAuthStore } from "../../store/authStore";
import { env } from "../../config/env";
import { SUPPORTED_LANGUAGES, setLanguage, type SupportedLanguage } from "../../i18n";
import type { ProfileStackParamList } from "../../navigation/ProfileStack";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ProfileStackParamList, "Settings">;

const LANGUAGE_LABELS: Record<SupportedLanguage, string> = {
  ko: "한국어",
  en: "English",
  es: "Español",
  zh: "中文",
  ja: "日本語",
};

export default function SettingsScreen({ navigation }: Props) {
  const { t, i18n } = useTranslation();
  const logout = useAuthStore((s) => s.logout);
  const queryClient = useQueryClient();
  const { data: profile } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });
  const [deleting, setDeleting] = useState(false);
  const [togglingIncognito, setTogglingIncognito] = useState(false);

  async function handleToggleIncognito(value: boolean) {
    setTogglingIncognito(true);
    try {
      await setIncognito(value);
      await queryClient.invalidateQueries({ queryKey: ["myProfile"] });
    } catch (e: any) {
      Alert.alert(t("common.somethingWentWrong"));
    } finally {
      setTogglingIncognito(false);
    }
  }

  function confirmDeleteAccount() {
    Alert.alert(t("settings.deleteConfirmTitle"), t("settings.deleteConfirmBody"), [
      { text: t("common.cancel"), style: "cancel" },
      { text: t("common.delete"), style: "destructive", onPress: handleDeleteAccount },
    ]);
  }

  async function handleDeleteAccount() {
    setDeleting(true);
    try {
      await deleteAccount();
      await logout();
    } catch (e: any) {
      Alert.alert(t("settings.deleteFailed"), e?.response?.data?.detail ?? e?.message ?? t("settings.tryAgainLater"));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.sectionLabel}>Language / 언어</Text>
      <View style={styles.langRow}>
        {SUPPORTED_LANGUAGES.map((lang) => (
          <Pressable
            key={lang}
            style={[styles.langChip, i18n.language === lang && styles.langChipActive]}
            onPress={() => setLanguage(lang)}
          >
            <Text style={i18n.language === lang ? styles.langChipTextActive : styles.langChipText}>
              {LANGUAGE_LABELS[lang]}
            </Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.switchRow}>
        <Text style={styles.rowText}>{t("settings.incognito")}</Text>
        <Switch
          value={profile?.is_incognito ?? false}
          onValueChange={handleToggleIncognito}
          disabled={togglingIncognito}
          trackColor={{ true: colors.navy }}
        />
      </View>
      <Text style={styles.rowHint}>{t("settings.incognitoDesc")}</Text>

      <Pressable style={styles.row} onPress={() => navigation.navigate("TravelMode")}>
        <Text style={styles.rowText}>{t("settings.travelMode")}</Text>
      </Pressable>
      <Pressable style={styles.row} onPress={() => navigation.navigate("Verification")}>
        <Text style={styles.rowText}>{t("settings.verification")}</Text>
      </Pressable>

      <Pressable style={styles.row} onPress={() => Linking.openURL(`${env.marketingSiteUrl}/privacy-policy.html`)}>
        <Text style={styles.rowText}>{t("settings.privacyPolicy")}</Text>
      </Pressable>
      <Pressable style={styles.row} onPress={() => Linking.openURL(`${env.marketingSiteUrl}/terms.html`)}>
        <Text style={styles.rowText}>{t("settings.termsOfService")}</Text>
      </Pressable>

      <Pressable style={styles.row} onPress={() => logout()}>
        <Text style={styles.rowText}>{t("settings.logOut")}</Text>
      </Pressable>

      <Pressable style={styles.row} onPress={confirmDeleteAccount} disabled={deleting}>
        {deleting ? <ActivityIndicator color={colors.danger} /> : <Text style={styles.dangerText}>{t("settings.deleteAccount")}</Text>}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white, paddingTop: 8 },
  sectionLabel: { fontSize: 12, fontWeight: "700", color: colors.muted, textTransform: "uppercase", paddingHorizontal: 18, paddingTop: 16, paddingBottom: 8 },
  langRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, paddingHorizontal: 18, paddingBottom: 16 },
  langChip: { borderWidth: 1, borderColor: colors.border, borderRadius: 20, paddingVertical: 8, paddingHorizontal: 16 },
  langChipActive: { backgroundColor: colors.navy, borderColor: colors.navy },
  langChipText: { color: colors.ink, fontSize: 13 },
  langChipTextActive: { color: "#fff", fontSize: 13, fontWeight: "600" },
  row: { padding: 18, borderBottomWidth: 1, borderBottomColor: colors.border },
  switchRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 18,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  rowHint: { fontSize: 12, color: colors.muted, paddingHorizontal: 18, paddingTop: 8, paddingBottom: 14 },
  rowText: { fontSize: 16, color: colors.ink },
  dangerText: { fontSize: 16, color: colors.danger },
});
