import { useEffect, useState } from "react";
import { Modal, Pressable, Text, View, StyleSheet } from "react-native";

import { subscribe, type AlertRequest } from "../services/alertStore";
import { colors } from "../theme";

/** Renders whatever utils/alert.ts's showAlert() publishes - only ever
 * receives anything on web (native just uses the real Alert.alert). Mount
 * once at the app root (App.tsx), not per-screen. */
export default function AlertHost() {
  const [request, setRequest] = useState<AlertRequest | null>(null);

  useEffect(() => subscribe(setRequest), []);

  if (!request) return null;

  function handlePress(onPress?: () => void) {
    setRequest(null);
    onPress?.();
  }

  return (
    <Modal transparent visible animationType="fade" onRequestClose={() => setRequest(null)}>
      <View style={styles.backdrop}>
        <View style={styles.card}>
          <Text style={styles.title}>{request.title}</Text>
          {request.message ? <Text style={styles.message}>{request.message}</Text> : null}
          <View style={styles.buttons}>
            {request.buttons.map((btn, i) => (
              <Pressable
                key={i}
                style={[styles.button, btn.style === "destructive" && styles.buttonDestructive]}
                onPress={() => handlePress(btn.onPress)}
              >
                <Text
                  style={[
                    styles.buttonText,
                    btn.style === "cancel" && styles.buttonTextCancel,
                    btn.style === "destructive" && styles.buttonTextDestructive,
                  ]}
                >
                  {btn.text}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: "rgba(11,41,68,0.45)", alignItems: "center", justifyContent: "center", padding: 24 },
  card: { width: "100%", maxWidth: 340, backgroundColor: colors.white, borderRadius: 20, padding: 22 },
  title: { fontSize: 17, fontWeight: "800", color: colors.navy, marginBottom: 6, textAlign: "center" },
  message: { fontSize: 14, color: colors.muted, textAlign: "center", lineHeight: 20, marginBottom: 4 },
  buttons: { marginTop: 18, gap: 8 },
  button: { backgroundColor: colors.creamDeep, borderRadius: 12, paddingVertical: 12, alignItems: "center" },
  buttonDestructive: { backgroundColor: "#FBEAE9" },
  buttonText: { fontSize: 15, fontWeight: "700", color: colors.navy },
  buttonTextCancel: { color: colors.muted, fontWeight: "600" },
  buttonTextDestructive: { color: "#B3261E" },
});
