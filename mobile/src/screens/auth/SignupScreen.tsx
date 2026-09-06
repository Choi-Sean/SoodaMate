import { useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View, StyleSheet } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import * as authApi from "../../api/auth";
import { useAuthStore } from "../../store/authStore";
import type { AuthStackParamList } from "../../navigation/AuthStack";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<AuthStackParamList, "Signup">;

const PROVIDER_DISPLAY_NAMES: Record<string, string> = { google: "Google", kakao: "Kakao", apple: "Apple" };

// signup_with_email (see backend/app/services/auth_service.py) returns a
// structured 409 detail — {message, providers} — when the email is already
// linked to an OAuth account, so this can point the user at the right login
// method instead of a dead-end "already registered" message.
function describeSignupError(e: any, t: (key: string, opts?: Record<string, unknown>) => string): string {
  const detail = e?.response?.data?.detail;
  if (detail && typeof detail === "object" && Array.isArray(detail.providers)) {
    const providers = detail.providers as string[];
    if (providers.length > 0 && providers[0] !== "email") {
      const providerLabel = providers.map((p) => PROVIDER_DISPLAY_NAMES[p] ?? p).join(", ");
      return t("auth.alreadyRegisteredWithProvider", { provider: providerLabel });
    }
    return t("auth.emailAlreadyRegistered");
  }
  return typeof detail === "string" ? detail : e?.message ?? t("common.somethingWentWrong");
}

export default function SignupScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const login = useAuthStore((s) => s.login);

  async function handleSignup() {
    if (password.length < 8) {
      setError(t("auth.passwordMinLength"));
      return;
    }
    if (password !== confirmPassword) {
      setError(t("auth.passwordMismatch"));
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const tokens = await authApi.signup(email, password);
      await login(tokens);
      // RootNavigator swaps to MainTabs once isAuthenticated flips true; the
      // profile-completion gate inside it routes to ProfileSetup first.
    } catch (e: any) {
      setError(describeSignupError(e, t));
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t("auth.createAccount")}</Text>

      {error && <Text style={styles.error}>{error}</Text>}

      <TextInput
        style={styles.input}
        placeholder={t("auth.email")}
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder={t("auth.password")}
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />
      <TextInput
        style={styles.input}
        placeholder={t("auth.confirmPassword")}
        secureTextEntry
        value={confirmPassword}
        onChangeText={setConfirmPassword}
      />

      <Pressable style={styles.primaryButton} onPress={handleSignup} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>{t("auth.signUp")}</Text>}
      </Pressable>

      <Pressable onPress={() => navigation.navigate("Login")}>
        <Text style={styles.link}>{t("auth.haveAccount")}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 24, backgroundColor: colors.white },
  title: { fontSize: 24, fontWeight: "700", textAlign: "center", marginBottom: 32, color: colors.navy },
  error: { color: colors.danger, textAlign: "center", marginBottom: 12 },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
    fontSize: 16,
  },
  primaryButton: { backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: "center", marginTop: 8 },
  primaryButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  link: { textAlign: "center", marginTop: 24, color: colors.accentDark },
});
