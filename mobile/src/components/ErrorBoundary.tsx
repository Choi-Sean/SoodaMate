import { Component, type ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useTranslation } from "react-i18next";

import { reportError } from "../services/errorReporting";
import { colors } from "../theme";

interface Props {
  children: ReactNode;
  t: ReturnType<typeof useTranslation>["t"];
}

interface State {
  hasError: boolean;
}

// A render-time throw anywhere below this point used to take the whole app
// down with it (no boundary existed at all) — RN shows no dialog for this in
// a release build, it just silently exits, which is indistinguishable from a
// native crash/OOM kill from the user's side. This at least keeps the app
// alive and visible for the (likely more common) case of a JS-level bug, and
// reports it to Sentry when configured. A true native crash (OOM, a native
// module fault) still bypasses this entirely — only Sentry's native layer
// can see those.
class ErrorBoundaryInner extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: { componentStack?: string | null }) {
    reportError(error, { componentStack: info.componentStack ?? undefined });
  }

  handleRetry = () => this.setState({ hasError: false });

  render() {
    if (this.state.hasError) {
      const { t } = this.props;
      return (
        <View style={styles.container}>
          <Text style={styles.title}>{t("errorBoundary.title")}</Text>
          <Text style={styles.message}>{t("common.somethingWentWrong")}</Text>
          <Pressable style={styles.button} onPress={this.handleRetry}>
            <Text style={styles.buttonText}>{t("common.tryAgain")}</Text>
          </Pressable>
        </View>
      );
    }
    return this.props.children;
  }
}

export default function ErrorBoundary({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  return <ErrorBoundaryInner t={t}>{children}</ErrorBoundaryInner>;
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32, backgroundColor: colors.cream, gap: 12 },
  title: { fontSize: 20, fontWeight: "700", color: colors.navy, textAlign: "center" },
  message: { fontSize: 14, color: colors.muted, textAlign: "center", lineHeight: 20 },
  button: { backgroundColor: colors.accent, borderRadius: 10, paddingVertical: 12, paddingHorizontal: 28, marginTop: 8 },
  buttonText: { color: "#fff", fontSize: 15, fontWeight: "600" },
});
