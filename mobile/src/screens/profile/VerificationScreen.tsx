import { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View, StyleSheet } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { getMyProfile } from "../../api/profiles";
import { startVerification, confirmVerification } from "../../api/verification";
import { colors } from "../../theme";

type Kind = "work" | "school";

export default function VerificationScreen() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: profile } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });

  const [kind, setKind] = useState<Kind>("work");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"email" | "code">("email");
  const [sending, setSending] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function handleSendCode() {
    setError(null);
    setSending(true);
    try {
      await startVerification(kind, email.trim());
      setInfo(t("verification.codeSent"));
      setStep("code");
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setSending(false);
    }
  }

  async function handleConfirm() {
    setError(null);
    setConfirming(true);
    try {
      await confirmVerification(kind, code.trim());
      await queryClient.invalidateQueries({ queryKey: ["myProfile"] });
      setInfo(t("verification.verifiedSuccess"));
      setStep("email");
      setEmail("");
      setCode("");
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setConfirming(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>{t("verification.title")}</Text>
      <Text style={styles.subtitle}>{t("verification.subtitle")}</Text>

      {profile?.verified_badge && (
        <View style={styles.badgeBanner}>
          <Text style={styles.badgeBannerText}>
            🏅{" "}
            {t("verification.alreadyVerified", {
              kind: t(`verification.kind${profile.verified_badge === "work" ? "Work" : "School"}`),
            })}
          </Text>
        </View>
      )}

      {error && <Text style={styles.error}>{error}</Text>}
      {info && !error && <Text style={styles.info}>{info}</Text>}

      <View style={styles.row}>
        <Pressable style={[styles.chip, kind === "work" && styles.chipSelected]} onPress={() => setKind("work")}>
          <Text style={kind === "work" ? styles.chipTextSelected : styles.chipText}>{t("verification.kindWork")}</Text>
        </Pressable>
        <Pressable style={[styles.chip, kind === "school" && styles.chipSelected]} onPress={() => setKind("school")}>
          <Text style={kind === "school" ? styles.chipTextSelected : styles.chipText}>{t("verification.kindSchool")}</Text>
        </Pressable>
      </View>

      {step === "email" ? (
        <>
          <TextInput
            style={styles.input}
            placeholder={t("verification.emailPlaceholder")}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
          />
          <Pressable style={styles.primaryButton} onPress={handleSendCode} disabled={sending || !email.trim()}>
            {sending ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>{t("verification.sendCode")}</Text>}
          </Pressable>
        </>
      ) : (
        <>
          <TextInput
            style={styles.input}
            placeholder={t("verification.codePlaceholder")}
            value={code}
            onChangeText={setCode}
            keyboardType="number-pad"
            maxLength={6}
          />
          <Pressable style={styles.primaryButton} onPress={handleConfirm} disabled={confirming || code.trim().length !== 6}>
            {confirming ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>{t("verification.confirm")}</Text>}
          </Pressable>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, flexGrow: 1, backgroundColor: colors.white },
  title: { fontSize: 24, fontWeight: "700", marginTop: 8, marginBottom: 4, color: colors.navy },
  subtitle: { color: colors.muted, marginBottom: 20 },
  badgeBanner: { backgroundColor: colors.creamDeep, borderRadius: 12, padding: 14, marginBottom: 16 },
  badgeBannerText: { color: colors.navy, fontWeight: "600" },
  error: { color: colors.danger, marginBottom: 12 },
  info: { color: colors.sage, marginBottom: 12 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 16 },
  chip: { borderWidth: 1, borderColor: colors.border, borderRadius: 20, paddingVertical: 8, paddingHorizontal: 16 },
  chipSelected: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipText: { color: colors.ink },
  chipTextSelected: { color: "#fff", fontWeight: "600" },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 14, marginBottom: 12, fontSize: 16 },
  primaryButton: { backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: "center", marginTop: 8 },
  primaryButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
});
