import { useState } from "react";
import { Image, Modal, Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import type { ChatMessage } from "../types";
import { colors } from "../theme";

interface Props {
  message: ChatMessage;
  isMine: boolean;
}

/** Text bubbles show the translated_content (already computed server-side
 * for the recipient — see routers/ws_chat.py) as the primary line when
 * present, with a small "translated" label and a tap-to-toggle back to the
 * original — same idea as WhatsApp/Messenger's translation UI. A sender
 * always sees their own original text (translated_content is only ever
 * populated for the recipient's language). Image bubbles render the photo
 * inline and open a simple fullscreen viewer on tap. */
export default function ChatBubble({ message, isMine }: Props) {
  const { t } = useTranslation();
  const [showOriginal, setShowOriginal] = useState(false);
  const [viewerOpen, setViewerOpen] = useState(false);

  const hasTranslation = !isMine && !!message.translated_content;
  const primaryText = hasTranslation && !showOriginal ? message.translated_content! : message.content;

  if (message.message_type === "image" && message.image_url) {
    return (
      <View style={[styles.row, isMine ? styles.rowMine : styles.rowTheirs]}>
        <Pressable onPress={() => setViewerOpen(true)}>
          <Image source={{ uri: message.image_url }} style={styles.image} resizeMode="cover" />
        </Pressable>
        <Modal visible={viewerOpen} transparent animationType="fade" onRequestClose={() => setViewerOpen(false)}>
          <View style={styles.viewerBackdrop}>
            <Pressable style={styles.viewerClose} onPress={() => setViewerOpen(false)} hitSlop={12}>
              <Ionicons name="close" size={28} color="#fff" />
            </Pressable>
            <Image source={{ uri: message.image_url }} style={styles.viewerImage} resizeMode="contain" />
          </View>
        </Modal>
      </View>
    );
  }

  return (
    <View style={[styles.row, isMine ? styles.rowMine : styles.rowTheirs]}>
      <View style={[styles.bubble, isMine ? styles.bubbleMine : styles.bubbleTheirs]}>
        <Text style={isMine ? styles.textMine : styles.textTheirs}>{primaryText}</Text>
        {hasTranslation && (
          <Pressable onPress={() => setShowOriginal((v) => !v)} hitSlop={6}>
            <Text style={[styles.translatedLabel, isMine ? styles.translatedLabelMine : styles.translatedLabelTheirs]}>
              {showOriginal ? t("chat.viewTranslated") : `${t("chat.translatedLabel")} · ${t("chat.viewOriginal")}`}
            </Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", marginVertical: 4, paddingHorizontal: 12 },
  rowMine: { justifyContent: "flex-end" },
  rowTheirs: { justifyContent: "flex-start" },
  bubble: { maxWidth: "78%", borderRadius: 16, paddingVertical: 10, paddingHorizontal: 14 },
  bubbleMine: { backgroundColor: colors.accent, borderBottomRightRadius: 4 },
  bubbleTheirs: { backgroundColor: colors.creamDeep, borderBottomLeftRadius: 4 },
  textMine: { color: "#fff", fontSize: 15 },
  textTheirs: { color: colors.ink, fontSize: 15 },
  translatedLabel: { fontSize: 11, marginTop: 4 },
  translatedLabelMine: { color: "rgba(255,255,255,0.75)" },
  translatedLabelTheirs: { color: colors.muted },
  image: { width: 200, height: 200, borderRadius: 16, backgroundColor: colors.creamDeep },
  viewerBackdrop: { flex: 1, backgroundColor: "rgba(11,41,68,0.95)", alignItems: "center", justifyContent: "center" },
  viewerClose: { position: "absolute", top: 50, right: 20, zIndex: 1, padding: 8 },
  viewerImage: { width: "100%", height: "80%" },
});
