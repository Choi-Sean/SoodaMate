import { useState } from "react";
import { ActivityIndicator, Image, Platform, Pressable, Text, TextInput, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import * as authApi from "../../api/auth";
import { useAuthStore } from "../../store/authStore";
import { signInWithGoogle } from "../../services/googleAuth";
import { signInWithKakao } from "../../services/kakaoAuth";
import { signInWithApple } from "../../services/appleAuth";
import type { AuthStackParamList } from "../../navigation/AuthStack";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<AuthStackParamList, "Login">;

export default function LoginScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const login = useAuthStore((s) => s.login);

  async function run(kind: string, fn: () => Promise<void>) {
    setError(null);
    setLoading(kind);
    try {
      await fn();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setLoading(null);
    }
  }

  const handleEmailLogin = () => run("email", async () => login(await authApi.login(email, password)));
  const handleGoogleLogin = () =>
    run("google", async () => {
      const idToken = await signInWithGoogle();
      if (idToken) login(await authApi.loginWithGoogle(idToken));
    });
  const handleKakaoLogin = () =>
    run("kakao", async () => login(await authApi.loginWithKakao(await signInWithKakao())));
  const handleAppleLogin = () =>
    run("apple", async () => {
      const identityToken = await signInWithApple();
      if (identityToken) login(await authApi.loginWithApple(identityToken));
    });

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t("auth.loginTitle")}</Text>

      {error && <Text style={styles.error}>{error}</Text>}

      <TextInput
        style={styles.input}
        placeholder={t("auth.email")}
        placeholderTextColor={colors.muted}
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <View style={styles.passwordRow}>
        <TextInput
          style={[styles.input, styles.passwordInput]}
          placeholder={t("auth.password")}
          placeholderTextColor={colors.muted}
          secureTextEntry={!passwordVisible}
          value={password}
          onChangeText={setPassword}
        />
        <Pressable style={styles.eyeButton} onPress={() => setPasswordVisible((v) => !v)} hitSlop={8}>
          <Ionicons name={passwordVisible ? "eye-off" : "eye"} size={22} color={colors.muted} />
        </Pressable>
      </View>

      <Pressable style={styles.primaryButton} onPress={handleEmailLogin} disabled={loading !== null}>
        {loading === "email" ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>{t("auth.logIn")}</Text>}
      </Pressable>

      <Pressable style={styles.googleButton} onPress={handleGoogleLogin} disabled={loading !== null}>
        {loading === "google" ? (
          <ActivityIndicator />
        ) : (
          <View style={styles.buttonContent}>
            <Image source={require("../../../assets/google-logo.png")} style={styles.providerLogo} />
            <Text style={styles.googleButtonText}>{t("auth.continueWithGoogle")}</Text>
          </View>
        )}
      </Pressable>

      <View style={styles.divider} />

      <Pressable style={styles.kakaoButton} onPress={handleKakaoLogin} disabled={loading !== null}>
        {loading === "kakao" ? (
          <ActivityIndicator />
        ) : (
          <View style={styles.buttonContent}>
            <Image source={require("../../../assets/kakao-logo.png")} style={styles.providerLogo} />
            <Text style={styles.kakaoButtonText}>{t("auth.continueWithKakao")}</Text>
          </View>
        )}
      </Pressable>

      {Platform.OS === "ios" && (
        <Pressable style={styles.appleButton} onPress={handleAppleLogin} disabled={loading !== null}>
          {loading === "apple" ? <ActivityIndicator color="#fff" /> : <Text style={styles.appleButtonText}>{t("auth.continueWithApple")}</Text>}
        </Pressable>
      )}

      <Pressable onPress={() => navigation.navigate("Signup")}>
        <Text style={styles.link}>{t("auth.noAccount")}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 24, backgroundColor: colors.white },
  title: { fontSize: 32, fontWeight: "700", textAlign: "center", marginBottom: 32, color: colors.accent },
  error: { color: colors.danger, textAlign: "center", marginBottom: 12 },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
    fontSize: 16,
    color: colors.ink,
  },
  passwordRow: { position: "relative", justifyContent: "center" },
  passwordInput: { paddingRight: 46 },
  eyeButton: { position: "absolute", right: 14, top: 0, bottom: 12, justifyContent: "center" },
  primaryButton: { backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: "center", marginTop: 8 },
  primaryButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  buttonContent: { flexDirection: "row", alignItems: "center", justifyContent: "center" },
  providerLogo: { width: 20, height: 20, marginRight: 10 },
  googleButton: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 14,
    alignItems: "center",
    marginTop: 12,
  },
  googleButtonText: { fontSize: 16, fontWeight: "500", color: colors.ink },
  divider: { height: 1, backgroundColor: colors.border, marginTop: 16, marginBottom: 4 },
  kakaoButton: { backgroundColor: colors.kakaoYellow, borderRadius: 10, padding: 14, alignItems: "center", marginTop: 12 },
  kakaoButtonText: { fontSize: 16, fontWeight: "500", color: "#000" },
  appleButton: { backgroundColor: "#000", borderRadius: 10, padding: 14, alignItems: "center", marginTop: 12 },
  appleButtonText: { fontSize: 16, fontWeight: "500", color: "#fff" },
  link: { textAlign: "center", marginTop: 24, color: colors.accentDark },
});
