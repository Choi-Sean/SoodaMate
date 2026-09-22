import { useCallback, useState } from "react";
import { ActivityIndicator, Modal, Pressable, ScrollView, Text, TextInput, View, StyleSheet } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useFocusEffect } from "@react-navigation/native";
import { useTranslation } from "react-i18next";

import { deleteAccount } from "../../api/account";
import { createInquiry } from "../../api/inquiries";
import { useAuthStore } from "../../store/authStore";
import { env } from "../../config/env";
import { SUPPORTED_LANGUAGES, setLanguage, type SupportedLanguage } from "../../i18n";
import type { ProfileStackParamList } from "../../navigation/ProfileStack";
import {
  getPushPermissionStatus,
  openNotificationSettings,
  registerForPushNotifications,
  type PushPermissionStatus,
} from "../../services/pushNotifications";
import { colors } from "../../theme";
import { showAlert } from "../../utils/alert";
import { openExternalUrl } from "../../utils/openExternalUrl";

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
  const [deleting, setDeleting] = useState(false);
  const [inquiryVisible, setInquiryVisible] = useState(false);
  const [inquirySubject, setInquirySubject] = useState("");
  const [inquiryMessage, setInquiryMessage] = useState("");
  const [submittingInquiry, setSubmittingInquiry] = useState(false);
  const [pushStatus, setPushStatus] = useState<PushPermissionStatus>("not-determined");

  // Re-checked every time this screen gains focus (not just on mount) — the only
  // way permission actually changes is the OS Settings app, which the row below
  // sends the user to and then back here.
  useFocusEffect(
    useCallback(() => {
      getPushPermissionStatus().then(setPushStatus);
    }, [])
  );

  async function handlePushRowPress() {
    if (pushStatus === "not-determined") {
      const result = await registerForPushNotifications();
      setPushStatus(result);
      return;
    }
    // "granted": nothing to request — still useful as a shortcut to the OS toggle.
    // "denied": this is the only way left to turn it back on (iOS won't re-prompt).
    // "unavailable": web, or a build without push configured — no-op.
    if (pushStatus !== "unavailable") openNotificationSettings();
  }

  function openInquiry() {
    setInquirySubject("");
    setInquiryMessage("");
    setInquiryVisible(true);
  }

  async function submitInquiry() {
    if (!inquirySubject.trim() || !inquiryMessage.trim()) {
      showAlert(t("settings.inquiryMissingFields"));
      return;
    }
    setSubmittingInquiry(true);
    try {
      await createInquiry(inquirySubject.trim(), inquiryMessage.trim());
      setInquiryVisible(false);
      showAlert(t("settings.inquirySentTitle"), t("settings.inquirySentBody"));
    } catch (e: any) {
      showAlert(t("common.somethingWentWrong"), e?.response?.data?.detail ?? e?.message ?? t("settings.tryAgainLater"));
    } finally {
      setSubmittingInquiry(false);
    }
  }

  function confirmDeleteAccount() {
    showAlert(t("settings.deleteConfirmTitle"), t("settings.deleteConfirmBody"), [
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
      showAlert(t("settings.deleteFailed"), e?.response?.data?.detail ?? e?.message ?? t("settings.tryAgainLater"));
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

      {/* Incognito toggle and Travel Mode entry removed per product decision —
          neither fits the Blind Chat concept for now. The underlying
          is_incognito field/API and TravelModeScreen/route are left intact
          so this is a one-line revert if that changes. */}

      <Pressable style={styles.row} onPress={() => navigation.navigate("Verification")}>
        <Text style={styles.rowText}>{t("settings.verification")}</Text>
      </Pressable>

      {pushStatus !== "unavailable" && (
        <Pressable style={[styles.row, styles.rowSpaceBetween]} onPress={handlePushRowPress}>
          <Text style={styles.rowText}>{t("settings.pushNotifications")}</Text>
          <Text style={pushStatus === "granted" ? styles.rowValueOn : styles.rowValueOff}>
            {t(pushStatus === "granted" ? "settings.pushOn" : "settings.pushOff")}
          </Text>
        </Pressable>
      )}

      <Pressable style={styles.row} onPress={() => openExternalUrl(`${env.marketingSiteUrl}/privacy-policy.html`)}>
        <Text style={styles.rowText}>{t("settings.privacyPolicy")}</Text>
      </Pressable>
      <Pressable style={styles.row} onPress={() => openExternalUrl(`${env.marketingSiteUrl}/terms.html`)}>
        <Text style={styles.rowText}>{t("settings.termsOfService")}</Text>
      </Pressable>

      <Pressable style={styles.row} onPress={openInquiry}>
        <Text style={styles.rowText}>{t("settings.contactUs")}</Text>
      </Pressable>

      <Pressable style={styles.row} onPress={() => logout()}>
        <Text style={styles.rowText}>{t("settings.logOut")}</Text>
      </Pressable>

      <Pressable style={styles.row} onPress={confirmDeleteAccount} disabled={deleting}>
        {deleting ? <ActivityIndicator color={colors.danger} /> : <Text style={styles.dangerText}>{t("settings.deleteAccount")}</Text>}
      </Pressable>

      <Modal visible={inquiryVisible} transparent animationType="slide" onRequestClose={() => setInquiryVisible(false)}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <ScrollView keyboardShouldPersistTaps="handled">
              <Text style={styles.modalTitle}>{t("settings.contactUs")}</Text>
              <Text style={styles.modalHint}>{t("settings.inquiryHint")}</Text>

              <Text style={styles.fieldLabel}>{t("settings.inquirySubjectLabel")}</Text>
              <TextInput
                style={styles.input}
                placeholder={t("settings.inquirySubjectPlaceholder")}
                value={inquirySubject}
                onChangeText={setInquirySubject}
                maxLength={200}
              />

              <Text style={[styles.fieldLabel, styles.fieldLabelSpaced]}>{t("settings.inquiryMessageLabel")}</Text>
              <TextInput
                style={[styles.input, styles.multiline]}
                placeholder={t("settings.inquiryMessagePlaceholder")}
                value={inquiryMessage}
                onChangeText={setInquiryMessage}
                multiline
                maxLength={4000}
              />

              <View style={styles.modalButtonRow}>
                <Pressable style={styles.modalCancelButton} onPress={() => setInquiryVisible(false)}>
                  <Text style={styles.modalCancelButtonText}>{t("common.cancel")}</Text>
                </Pressable>
                <Pressable style={styles.modalSubmitButton} onPress={submitInquiry} disabled={submittingInquiry}>
                  {submittingInquiry ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={styles.modalSubmitButtonText}>{t("settings.inquirySubmit")}</Text>
                  )}
                </Pressable>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
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
  rowSpaceBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  rowText: { fontSize: 16, color: colors.ink },
  rowValueOn: { fontSize: 14, fontWeight: "700", color: colors.accent },
  rowValueOff: { fontSize: 14, fontWeight: "600", color: colors.muted },
  dangerText: { fontSize: 16, color: colors.danger },
  modalBackdrop: { flex: 1, backgroundColor: "rgba(11,41,68,0.55)", justifyContent: "flex-end" },
  modalCard: {
    backgroundColor: colors.white,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    maxHeight: "85%",
  },
  modalTitle: { fontSize: 18, fontWeight: "800", color: colors.navy, marginBottom: 4 },
  modalHint: { fontSize: 13, color: colors.muted, marginBottom: 16, lineHeight: 18 },
  fieldLabel: { fontSize: 14, fontWeight: "600", marginBottom: 8, color: colors.muted },
  fieldLabelSpaced: { marginTop: 14 },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 14, fontSize: 16 },
  multiline: { minHeight: 100, textAlignVertical: "top" },
  modalButtonRow: { flexDirection: "row", gap: 10, marginTop: 20, marginBottom: 8 },
  modalCancelButton: { flex: 1, borderRadius: 10, paddingVertical: 14, alignItems: "center", backgroundColor: colors.creamDeep },
  modalCancelButtonText: { color: colors.muted, fontWeight: "700" },
  modalSubmitButton: { flex: 1, borderRadius: 10, paddingVertical: 14, alignItems: "center", backgroundColor: colors.accent },
  modalSubmitButtonText: { color: "#fff", fontWeight: "700" },
});
