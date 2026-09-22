import { useState } from "react";
import { ActivityIndicator, Image, Modal, Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import { translateMessage } from "../api/messages";
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from "../i18n";
import type { AlertButtonSpec } from "../services/alertStore";
import { showAlert } from "../utils/alert";
import type { ChatMessage } from "../types";
import { colors } from "../theme";

interface Props {
  message: ChatMessage;
  isMine: boolean;
  /** Only ever called for the sender's own, not-yet-deleted messages — see the
   * long-press handler below. Omitted (or the message type is already
   * "deleted") means no delete affordance is offered at all. */
  onDelete?: (messageId: string) => void;
}

const LANGUAGE_LABELS: Record<SupportedLanguage, string> = {
  ko: "한국어",
  en: "English",
  es: "Español",
  zh: "中文",
  ja: "日本語",
};

/** Text bubbles from the other person show a small translate button. Tapping it
 * offers a pick of the app's 5 languages (not just the viewer's own preferred
 * language) and fetches that translation on demand (services/api/messages.ts),
 * replacing the earlier always-on auto-translated-into-my-language display —
 * the server still computes that one too (routers/ws_chat.py), but this button
 * is the only thing shown for it now: picking the viewer's own preferred
 * language here shows the exact same text instantly with no extra request.
 * A sender always sees their own original text; there's nothing to translate
 * on their own bubble. Image bubbles render the photo inline and open a simple
 * fullscreen viewer on tap. */
export default function ChatBubble({ message, isMine, onDelete }: Props) {
  const { t } = useTranslation();
  const [viewerOpen, setViewerOpen] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [shown, setShown] = useState<{ lang: SupportedLanguage; text: string } | null>(null);

  function confirmDelete() {
    if (!onDelete) return;
    showAlert(t("chat.deleteMessageTitle"), t("chat.deleteMessageBody"), [
      { text: t("common.cancel"), style: "cancel" },
      { text: t("common.delete"), style: "destructive", onPress: () => onDelete(message.id) },
    ]);
  }

  async function translateTo(lang: SupportedLanguage) {
    // The auto-translation ws_chat.py already attached at send time covers
    // exactly one language (the recipient's own preferred_language) — reuse
    // it instead of a redundant network call when it happens to match.
    if (message.translated_language === lang && message.translated_content) {
      setShown({ lang, text: message.translated_content });
      return;
    }
    setTranslating(true);
    try {
      const result = await translateMessage(message.match_id, message.id, lang);
      setShown({ lang, text: result.translated_content });
    } catch (e: any) {
      showAlert(t("common.somethingWentWrong"), e?.response?.data?.detail ?? e?.message ?? undefined);
    } finally {
      setTranslating(false);
    }
  }

  function openLanguagePicker() {
    const buttons: AlertButtonSpec[] = SUPPORTED_LANGUAGES.map((lang) => ({
      text: LANGUAGE_LABELS[lang],
      onPress: () => translateTo(lang),
    }));
    buttons.push({ text: t("common.cancel"), style: "cancel" });
    showAlert(t("chat.translateTo"), undefined, buttons);
  }

  if (message.message_type === "deleted") {
    return (
      <View style={[styles.row, isMine ? styles.rowMine : styles.rowTheirs]}>
        <View style={[styles.bubble, styles.bubbleDeleted]}>
          <Ionicons name="ban-outline" size={13} color={colors.muted} />
          <Text style={styles.deletedText}>{t("chat.messageDeleted")}</Text>
        </View>
      </View>
    );
  }

  if (message.message_type === "image" && message.image_url) {
    return (
      <View style={[styles.row, isMine ? styles.rowMine : styles.rowTheirs]}>
        <Pressable
          onPress={() => setViewerOpen(true)}
          onLongPress={isMine ? confirmDelete : undefined}
          delayLongPress={350}
        >
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
      <Pressable
        style={[styles.bubble, isMine ? styles.bubbleMine : styles.bubbleTheirs]}
        onLongPress={isMine ? confirmDelete : undefined}
        delayLongPress={350}
      >
        <Text style={isMine ? styles.textMine : styles.textTheirs}>{message.content}</Text>
        {shown && (
          <View style={styles.translatedBlock}>
            <Text style={isMine ? styles.textMine : styles.textTheirs}>{shown.text}</Text>
            <Text style={[styles.translatedTag, isMine ? styles.translatedLabelMine : styles.translatedLabelTheirs]}>
              {t("chat.translatedInto", { language: LANGUAGE_LABELS[shown.lang] })}
            </Text>
          </View>
        )}
        {!isMine && (
          <Pressable onPress={openLanguagePicker} disabled={translating} style={styles.translateButton} hitSlop={6}>
            {translating ? (
              <ActivityIndicator size="small" color={colors.muted} />
            ) : (
              <>
                <Ionicons name="language-outline" size={13} color={colors.muted} />
                <Text style={styles.translateButtonText}>{shown ? t("chat.translateAgain") : t("chat.translate")}</Text>
              </>
            )}
          </Pressable>
        )}
      </Pressable>
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
  bubbleDeleted: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: colors.border,
  },
  deletedText: { color: colors.muted, fontSize: 13, fontStyle: "italic" },
  textMine: { color: "#fff", fontSize: 15 },
  textTheirs: { color: colors.ink, fontSize: 15 },
  translatedBlock: { marginTop: 6, paddingTop: 6, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: "rgba(11,41,68,0.15)" },
  translatedTag: { fontSize: 11, marginTop: 2 },
  translatedLabelMine: { color: "rgba(255,255,255,0.75)" },
  translatedLabelTheirs: { color: colors.muted },
  translateButton: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 6 },
  translateButtonText: { fontSize: 11, color: colors.muted, fontWeight: "600" },
  image: { width: 200, height: 200, borderRadius: 16, backgroundColor: colors.creamDeep },
  viewerBackdrop: { flex: 1, backgroundColor: "rgba(11,41,68,0.95)", alignItems: "center", justifyContent: "center" },
  viewerClose: { position: "absolute", top: 50, right: 20, zIndex: 1, padding: 8 },
  viewerImage: { width: "100%", height: "80%" },
});
