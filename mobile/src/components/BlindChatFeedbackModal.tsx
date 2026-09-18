import { useState } from "react";
import { ActivityIndicator, Modal, Pressable, Text, TextInput, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import MultiChipSelect from "./MultiChipSelect";
import { BLIND_CHAT_FEEDBACK_TAG_KEYS } from "../constants/blindChatFeedbackTags";
import type { BlindChatFeedbackInput } from "../types";
import { colors } from "../theme";

const STAR_COUNT = 5;
const COMMENT_MAX_LENGTH = 100;

interface Props {
  visible: boolean;
  otherDisplayName: string;
  onCancel: () => void;
  onSubmit: (input: BlindChatFeedbackInput) => Promise<void>;
}

/** Post-chat rating for a blind-chat partner — purely a signal that feeds
 * future AI Match ranking (see backend's llm_match_service.py), never shown
 * to the rated person. Self-contained {visible, onCancel, onSubmit} modal,
 * same convention as MbtiQuizModal/PhotoCropEditor, opened from
 * ChatRoomScreen's options menu for blind matches only. */
export default function BlindChatFeedbackModal({ visible, otherDisplayName, onCancel, onSubmit }: Props) {
  const { t } = useTranslation();
  const [rating, setRating] = useState(0);
  const [tags, setTags] = useState<string[]>([]);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const showComment = tags.includes("other");

  function reset() {
    setRating(0);
    setTags([]);
    setComment("");
  }

  function handleCancel() {
    reset();
    onCancel();
  }

  async function handleSubmit() {
    if (rating === 0) return;
    setSubmitting(true);
    try {
      await onSubmit({
        rating,
        tags,
        comment: showComment && comment.trim() ? comment.trim() : null,
      });
      reset();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal visible={visible} animationType="fade" transparent onRequestClose={handleCancel}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <Text style={styles.title}>{t("blindFeedback.title", { name: otherDisplayName })}</Text>
          <Text style={styles.subtitle}>{t("blindFeedback.subtitle")}</Text>

          <View style={styles.starRow}>
            {Array.from({ length: STAR_COUNT }, (_, i) => i + 1).map((n) => (
              <Pressable key={n} onPress={() => setRating(n)} hitSlop={8}>
                <Ionicons
                  name={n <= rating ? "star" : "star-outline"}
                  size={34}
                  color={n <= rating ? colors.accent : colors.border}
                />
              </Pressable>
            ))}
          </View>

          <MultiChipSelect
            label={t("blindFeedback.tagsLabel")}
            options={BLIND_CHAT_FEEDBACK_TAG_KEYS as unknown as readonly string[]}
            translatePrefix="blindFeedback.tag"
            values={tags}
            onChange={setTags}
          />

          {showComment && (
            <View style={styles.commentWrap}>
              <TextInput
                style={styles.commentInput}
                placeholder={t("blindFeedback.commentPlaceholder")}
                placeholderTextColor={colors.muted}
                value={comment}
                onChangeText={(v) => setComment(v.slice(0, COMMENT_MAX_LENGTH))}
                maxLength={COMMENT_MAX_LENGTH}
                multiline
              />
              <Text style={styles.commentCount}>
                {comment.length}/{COMMENT_MAX_LENGTH}
              </Text>
            </View>
          )}

          <Pressable
            style={[styles.submitButton, rating === 0 && styles.submitButtonDisabled]}
            onPress={handleSubmit}
            disabled={rating === 0 || submitting}
          >
            {submitting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.submitButtonText}>{t("blindFeedback.submit")}</Text>
            )}
          </Pressable>
          <Pressable style={styles.skipButton} onPress={handleCancel}>
            <Text style={styles.skipButtonText}>{t("blindFeedback.skip")}</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: "rgba(11,41,68,0.45)", justifyContent: "center", padding: 24 },
  sheet: { backgroundColor: colors.white, borderRadius: 20, padding: 20 },
  title: { fontSize: 17, fontWeight: "800", color: colors.navy, textAlign: "center" },
  subtitle: { fontSize: 13, color: colors.muted, textAlign: "center", marginTop: 4, marginBottom: 16 },
  starRow: { flexDirection: "row", justifyContent: "center", gap: 10, marginBottom: 8 },
  commentWrap: { marginTop: 8 },
  commentInput: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 12,
    minHeight: 60,
    textAlignVertical: "top",
    fontSize: 14,
    color: colors.ink,
  },
  commentCount: { fontSize: 11, color: colors.muted, textAlign: "right", marginTop: 4 },
  submitButton: { backgroundColor: colors.accent, borderRadius: 12, paddingVertical: 14, alignItems: "center", marginTop: 20 },
  submitButtonDisabled: { opacity: 0.5 },
  submitButtonText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  skipButton: { alignItems: "center", marginTop: 10, padding: 8 },
  skipButtonText: { color: colors.muted, fontWeight: "600" },
});
