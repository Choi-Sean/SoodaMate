import { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View, StyleSheet } from "react-native";
import { useTranslation } from "react-i18next";

import { startPhoneVerification, confirmPhoneVerification } from "../../api/verification";
import { colors } from "../../theme";

interface Props {
  onVerified: () => void;
}

type Country = "KR" | "US";

// Scoped to the app's two launch markets (see LocationPicker's own KR/US
// scoping) — not a general international picker.
const DIAL_CODE: Record<Country, string> = { KR: "+82", US: "+1" };

/** Local-format input -> E.164. KR mobile numbers are written locally with a
 * leading 0 (010-1234-5678) that E.164 drops; US just strips formatting. */
function toE164(country: Country, local: string): string {
  const digits = local.replace(/\D/g, "");
  if (country === "KR") {
    return `+82${digits.replace(/^0/, "")}`;
  }
  return `+1${digits}`;
}

export default function PhoneVerificationScreen({ onVerified }: Props) {
  const { t } = useTranslation();
  const [country, setCountry] = useState<Country>("KR");
  const [localNumber, setLocalNumber] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [sending, setSending] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const e164 = toE164(country, localNumber);

  async function handleSendCode() {
    setError(null);
    setSending(true);
    try {
      await startPhoneVerification(e164);
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
      await confirmPhoneVerification(e164, code.trim());
      onVerified();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setConfirming(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.badge}>🔒</Text>
      <Text style={styles.title}>{t("phoneVerification.title")}</Text>
      <Text style={styles.subtitle}>{t("phoneVerification.subtitle")}</Text>

      {error && <Text style={styles.error}>{error}</Text>}

      {step === "phone" ? (
        <>
          <View style={styles.row}>
            {(["KR", "US"] as Country[]).map((c) => (
              <Pressable
                key={c}
                style={[styles.chip, country === c && styles.chipSelected]}
                onPress={() => setCountry(c)}
              >
                <Text style={country === c ? styles.chipTextSelected : styles.chipText}>
                  {c === "KR" ? t("phoneVerification.countryKorea") : t("phoneVerification.countryUs")} ({DIAL_CODE[c]})
                </Text>
              </Pressable>
            ))}
          </View>
          <View style={styles.phoneInputRow}>
            <View style={styles.dialCodeBox}>
              <Text style={styles.dialCodeText}>{DIAL_CODE[country]}</Text>
            </View>
            <TextInput
              style={styles.phoneInput}
              placeholder={country === "KR" ? "010-1234-5678" : "(213) 456-1343"}
              placeholderTextColor={colors.muted}
              value={localNumber}
              onChangeText={setLocalNumber}
              keyboardType="phone-pad"
            />
          </View>
          <Pressable
            style={styles.primaryButton}
            onPress={handleSendCode}
            disabled={sending || localNumber.replace(/\D/g, "").length < 8}
          >
            {sending ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>{t("phoneVerification.sendCode")}</Text>}
          </Pressable>
        </>
      ) : (
        <>
          <Text style={styles.codeSentTo}>{t("phoneVerification.codeSentTo", { phone: e164 })}</Text>
          <TextInput
            style={styles.input}
            placeholder={t("phoneVerification.codePlaceholder")}
            placeholderTextColor={colors.muted}
            value={code}
            onChangeText={setCode}
            keyboardType="number-pad"
            maxLength={6}
          />
          <Pressable style={styles.primaryButton} onPress={handleConfirm} disabled={confirming || code.trim().length < 4}>
            {confirming ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>{t("phoneVerification.confirm")}</Text>}
          </Pressable>
          <Pressable style={styles.linkButton} onPress={() => setStep("phone")}>
            <Text style={styles.linkButtonText}>{t("phoneVerification.changeNumber")}</Text>
          </Pressable>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, paddingTop: 72, flexGrow: 1, backgroundColor: colors.white, alignItems: "stretch" },
  badge: { fontSize: 40, textAlign: "center", marginBottom: 12 },
  title: { fontSize: 24, fontWeight: "700", textAlign: "center", marginBottom: 8, color: colors.navy },
  subtitle: { color: colors.muted, textAlign: "center", marginBottom: 28, lineHeight: 20 },
  error: { color: colors.danger, marginBottom: 12, textAlign: "center" },
  row: { flexDirection: "row", gap: 8, marginBottom: 16, justifyContent: "center" },
  chip: { borderWidth: 1, borderColor: colors.border, borderRadius: 20, paddingVertical: 8, paddingHorizontal: 16 },
  chipSelected: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipText: { color: colors.ink },
  chipTextSelected: { color: "#fff", fontWeight: "600" },
  phoneInputRow: { flexDirection: "row", gap: 8, marginBottom: 16 },
  dialCodeBox: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 14,
    justifyContent: "center",
  },
  dialCodeText: { fontSize: 16, color: colors.ink, fontWeight: "600" },
  phoneInput: { flex: 1, borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 14, fontSize: 16 },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 14, marginBottom: 12, fontSize: 16 },
  codeSentTo: { color: colors.muted, textAlign: "center", marginBottom: 16 },
  primaryButton: { backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: "center", marginTop: 8 },
  primaryButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  linkButton: { alignItems: "center", marginTop: 16, padding: 8 },
  linkButtonText: { color: colors.accentDark, fontWeight: "600" },
});
