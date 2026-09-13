import { useState } from "react";
import { ActivityIndicator, Image, Pressable, ScrollView, Text, TextInput, View, StyleSheet } from "react-native";
import { useTranslation } from "react-i18next";

import * as authApi from "../../api/auth";
import { useAuthStore } from "../../store/authStore";
import { colors } from "../../theme";

type Country = "KR" | "US";

// Scoped to the app's two launch markets (see LocationPicker's own KR/US
// scoping) — not a general international picker.
const DIAL_CODE: Record<Country, string> = { KR: "+82", US: "+1" };
const MAX_DIGITS: Record<Country, number> = { KR: 11, US: 10 };

/** Local-format input -> E.164. KR mobile numbers are written locally with a
 * leading 0 (010-1234-5678) that E.164 drops; US just strips formatting. */
function toE164(country: Country, local: string): string {
  const digits = local.replace(/\D/g, "");
  if (country === "KR") {
    return `+82${digits.replace(/^0/, "")}`;
  }
  return `+1${digits}`;
}

/** Digits-only -> auto-hyphenated display string, formatted as the user
 * types (010-1234-5678 for KR, (213) 456-1343 for US). */
function formatLocalNumber(country: Country, digits: string): string {
  const d = digits.slice(0, MAX_DIGITS[country]);
  if (country === "KR") {
    if (d.length <= 3) return d;
    if (d.length <= 7) return `${d.slice(0, 3)}-${d.slice(3)}`;
    return `${d.slice(0, 3)}-${d.slice(3, 7)}-${d.slice(7)}`;
  }
  if (d.length <= 3) return d;
  if (d.length <= 6) return `(${d.slice(0, 3)}) ${d.slice(3)}`;
  return `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`;
}

/** KR mobile numbers are 10-11 digits starting with 01 (010 is standard,
 * 011/016-019 are old grandfathered carriers); US local numbers are a flat
 * 10 digits. Just a shape check — Twilio Verify is the real validator. */
function isValidLocalNumber(country: Country, digits: string): boolean {
  if (country === "KR") return digits.startsWith("01") && digits.length >= 10 && digits.length <= 11;
  return digits.length === 10;
}

// The app's one sign-in/sign-up entry point — no email or password, and no
// separate signup screen. Confirming the code is enough for the backend to
// find-or-create the account (see /auth/phone/confirm), so RootNavigator's
// existing profile-completeness check is what actually decides whether this
// person lands on ProfileSetupScreen (new) or straight into MainTabs
// (returning) — nothing here needs to know which case it is.
export default function PhoneAuthScreen() {
  const { t } = useTranslation();
  const [country, setCountry] = useState<Country>("KR");
  const [localNumber, setLocalNumber] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [sending, setSending] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const login = useAuthStore((s) => s.login);

  const digits = localNumber.replace(/\D/g, "");
  const e164 = toE164(country, localNumber);
  const numberValid = isValidLocalNumber(country, digits);

  function handleChangeCountry(next: Country) {
    setCountry(next);
    setLocalNumber(formatLocalNumber(next, digits));
  }

  function handleChangeLocalNumber(text: string) {
    setLocalNumber(formatLocalNumber(country, text.replace(/\D/g, "")));
  }

  async function handleSendCode() {
    setError(null);
    if (!numberValid) {
      setError(t("phoneAuth.invalidNumber"));
      return;
    }
    setSending(true);
    try {
      await authApi.startPhoneAuth(e164);
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
      const result = await authApi.confirmPhoneAuth(e164, code.trim());
      await login(result);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setConfirming(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      <Image source={require("../../../assets/logo-mascot.png")} style={styles.logo} resizeMode="contain" />
      <Text style={styles.brand}>SooDaMate</Text>
      <Text style={styles.subtitle}>{step === "phone" ? t("phoneAuth.subtitle") : t("phoneAuth.codeSubtitle")}</Text>

      {error && <Text style={styles.error}>{error}</Text>}

      {step === "phone" ? (
        <>
          <View style={styles.row}>
            {(["KR", "US"] as Country[]).map((c) => (
              <Pressable
                key={c}
                style={[styles.chip, country === c && styles.chipSelected]}
                onPress={() => handleChangeCountry(c)}
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
              placeholder={country === "KR" ? "010-1234-5678" : "(213) 123-4567"}
              placeholderTextColor={colors.muted}
              value={localNumber}
              onChangeText={handleChangeLocalNumber}
              keyboardType="phone-pad"
              maxLength={country === "KR" ? 13 : 14}
              autoFocus
            />
          </View>
          <Pressable
            style={styles.primaryButton}
            onPress={handleSendCode}
            disabled={sending || !numberValid}
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
            autoFocus
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
  container: { padding: 24, paddingTop: 88, flexGrow: 1, backgroundColor: colors.white, alignItems: "stretch" },
  logo: { width: 96, height: 96, alignSelf: "center", marginBottom: 12 },
  brand: { fontSize: 30, fontWeight: "800", textAlign: "center", color: colors.accentDark, marginBottom: 8 },
  subtitle: { color: colors.muted, textAlign: "center", marginBottom: 28, lineHeight: 20, paddingHorizontal: 12 },
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
