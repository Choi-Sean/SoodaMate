import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioPlayer,
  useAudioPlayerStatus,
  useAudioRecorder,
  useAudioRecorderState,
} from "expo-audio";
import { useTranslation } from "react-i18next";

import { showAlert } from "../utils/alert";
import { colors } from "../theme";

// Auto-stops (and drops straight into the send/discard preview) at this
// length rather than letting someone record indefinitely — matches the
// server's sanity ceiling being far above this (routers/ws_chat.py's
// MAX_VOICE_SECONDS), so a real recording from this UI never gets rejected.
const MAX_RECORD_SECONDS = 120;

function formatDuration(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = Math.floor(totalSeconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface Props {
  disabled?: boolean;
  sending?: boolean;
  onSend: (fileUri: string, durationSeconds: number) => void;
  /** Fires whenever recording or previewing starts/stops, so the parent can
   * hide the text input and image button and let this bar take the full
   * composer row while active (see ChatRoomScreen's inputBar). */
  onActiveChange?: (active: boolean) => void;
}

/** Mic button in the chat composer: tap to record, tap again to stop and
 * preview (play back what was just recorded), then send or discard. All
 * recording/playback state lives here; the parent (ChatRoomScreen) only
 * gets involved once "send" is tapped — mirrors how handleSendImage owns
 * the upload for the image-send button, just with a record step first. */
export default function VoiceRecorderBar({ disabled, sending, onSend, onActiveChange }: Props) {
  const { t } = useTranslation();
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const recorderState = useAudioRecorderState(recorder, 200);
  const [recordedUri, setRecordedUri] = useState<string | null>(null);
  const [recordedDuration, setRecordedDuration] = useState(0);
  const player = useAudioPlayer(null);
  const playerStatus = useAudioPlayerStatus(player);

  useEffect(() => {
    if (recordedUri) player.replace({ uri: recordedUri });
  }, [recordedUri, player]);

  const active = recorderState.isRecording || !!recordedUri;
  useEffect(() => {
    onActiveChange?.(active);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  async function stopRecording() {
    if (!recorderState.isRecording) return;
    const duration = Math.max(1, Math.round(recorderState.durationMillis / 1000));
    await recorder.stop();
    setRecordedDuration(duration);
    setRecordedUri(recorder.uri);
  }

  // Auto-stop once the cap is hit — same escape hatch a real phone call
  // dialer/voice-memo app gives you instead of silently truncating later.
  useEffect(() => {
    if (recorderState.isRecording && recorderState.durationMillis / 1000 >= MAX_RECORD_SECONDS) {
      stopRecording();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recorderState.durationMillis, recorderState.isRecording]);

  async function startRecording() {
    if (disabled) return;
    const permission = await requestRecordingPermissionsAsync();
    if (!permission.granted) {
      showAlert(t("common.somethingWentWrong"), t("chat.voicePermission"));
      return;
    }
    await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true });
    setRecordedUri(null);
    await recorder.prepareToRecordAsync();
    recorder.record();
  }

  async function cancelRecording() {
    if (recorderState.isRecording) await recorder.stop();
    setRecordedUri(null);
  }

  function discardPreview() {
    if (playerStatus.playing) player.pause();
    setRecordedUri(null);
  }

  function togglePlayback() {
    if (playerStatus.playing) {
      player.pause();
    } else {
      player.seekTo(0);
      player.play();
    }
  }

  function handleSend() {
    if (!recordedUri) return;
    onSend(recordedUri, recordedDuration);
    setRecordedUri(null);
  }

  if (recordedUri) {
    return (
      <View style={styles.previewBar}>
        <Pressable onPress={discardPreview} hitSlop={10} style={styles.iconButton}>
          <Ionicons name="trash-outline" size={20} color={colors.muted} />
        </Pressable>
        <Pressable onPress={togglePlayback} hitSlop={10} style={styles.playButton}>
          <Ionicons name={playerStatus.playing ? "pause" : "play"} size={16} color="#fff" />
        </Pressable>
        <Text style={styles.durationText}>{formatDuration(recordedDuration)}</Text>
        <Pressable
          onPress={handleSend}
          disabled={sending}
          style={[styles.sendVoiceButton, sending && styles.sendButtonDisabled]}
        >
          {sending ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.sendVoiceButtonText}>{t("chat.send")}</Text>
          )}
        </Pressable>
      </View>
    );
  }

  if (recorderState.isRecording) {
    return (
      <View style={styles.recordingBar}>
        <Pressable onPress={cancelRecording} hitSlop={10} style={styles.iconButton}>
          <Ionicons name="close" size={20} color={colors.muted} />
        </Pressable>
        <View style={styles.recordingDot} />
        <Text style={styles.recordingText}>
          {t("chat.recording")} {formatDuration(recorderState.durationMillis / 1000)}
        </Text>
        <Pressable onPress={stopRecording} hitSlop={10} style={styles.stopButton}>
          <Ionicons name="stop" size={14} color="#fff" />
        </Pressable>
      </View>
    );
  }

  return (
    <Pressable style={[styles.micButton, disabled && styles.micButtonDisabled]} onPress={startRecording} disabled={disabled}>
      <Ionicons name="mic-outline" size={22} color={colors.accentDark} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  micButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.creamDeep,
  },
  micButtonDisabled: { opacity: 0.5 },
  recordingBar: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.creamDeep,
    borderRadius: 21,
    paddingHorizontal: 12,
    height: 42,
  },
  recordingDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.danger },
  recordingText: { flex: 1, fontSize: 13, color: colors.ink, fontWeight: "600" },
  stopButton: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: colors.danger,
    alignItems: "center",
    justifyContent: "center",
  },
  iconButton: { padding: 4 },
  previewBar: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.creamDeep,
    borderRadius: 21,
    paddingHorizontal: 10,
    height: 42,
  },
  playButton: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  durationText: { flex: 1, fontSize: 13, color: colors.ink, fontWeight: "600" },
  sendVoiceButton: { backgroundColor: colors.accent, borderRadius: 16, paddingHorizontal: 14, paddingVertical: 7 },
  sendButtonDisabled: { backgroundColor: colors.border },
  sendVoiceButtonText: { color: "#fff", fontWeight: "700", fontSize: 13 },
});
