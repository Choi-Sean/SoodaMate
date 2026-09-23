import { useEffect } from "react";
import { Image, Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import { useCall, type CallEndReason } from "../services/CallContext";
import { RTCView, webrtcAvailable } from "../services/webrtc";
import { showAlert } from "../utils/alert";
import { colors } from "../theme";

const END_REASON_KEY: Partial<Record<CallEndReason, string>> = {
  declined: "call.endedDeclined",
  timeout: "call.endedNoAnswer",
  peer_offline: "call.endedOffline",
  error: "call.endedError",
  busy: "call.endedBusy",
};

const START_ERROR_KEY: Record<string, string> = {
  call_restricted: "call.startErrorRestricted",
  call_not_allowed: "call.startErrorNotAllowed",
  rate_limited: "call.startErrorRateLimited",
};

/** Mounted once in RootNavigator's MainApp, alongside CallProvider — renders
 * nothing while idle, and the ringing/active call screen as a full-screen
 * Modal over whatever else is on screen, from anywhere in the app. */
export default function CallOverlay() {
  const { t } = useTranslation();
  const call = useCall();

  useEffect(() => {
    if (call.lastEndReason && call.lastEndReason !== "hangup") {
      const key = END_REASON_KEY[call.lastEndReason];
      if (key) showAlert(t(key));
      call.dismissEndReason();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [call.lastEndReason]);

  useEffect(() => {
    if (call.startError) {
      showAlert(t(START_ERROR_KEY[call.startError] ?? "call.startErrorGeneric"));
      call.dismissEndReason();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [call.startError]);

  if (!webrtcAvailable || call.phase === "idle") return null;

  const name = call.peer?.otherDisplayName || t("call.someone");
  const genderIconName = call.peer?.otherGender === "male" ? "male" : call.peer?.otherGender === "female" ? "female" : null;

  const isAudioCall = call.callType === "audio";

  return (
    <Modal visible animationType="slide" onRequestClose={() => {}}>
      <View style={styles.container}>
        {!isAudioCall && call.phase === "active" && call.remoteStreamURL ? (
          <RTCView streamURL={call.remoteStreamURL} style={styles.remoteVideo} objectFit="cover" />
        ) : (
          <View style={[styles.remoteVideo, styles.remotePlaceholder]}>
            {isAudioCall && (
              <Image
                source={require("../../assets/logo-mascot.png")}
                style={styles.audioMascot}
                resizeMode="contain"
              />
            )}
          </View>
        )}

        {/* Name shown at the top of the call screen throughout — masked "S***"
            pre-reveal is never reachable here (calls are blocked until a blind
            match is revealed), so this is always the real name. */}
        <View style={styles.nameBar}>
          <Text style={styles.nameText} numberOfLines={1}>
            {name}
          </Text>
          {genderIconName && <Ionicons name={genderIconName} size={16} color="#fff" style={styles.nameGenderIcon} />}
        </View>
        <Text style={styles.statusText}>
          {call.phase === "outgoing"
            ? t("call.calling")
            : call.phase === "incoming"
              ? t(isAudioCall ? "call.incomingAudio" : "call.incoming")
              : ""}
        </Text>

        {!isAudioCall && call.phase === "active" && call.localStreamURL && (
          <RTCView streamURL={call.localStreamURL} style={styles.localVideo} objectFit="cover" mirror zOrder={1} />
        )}

        <View style={styles.controls}>
          {call.phase === "incoming" ? (
            <>
              <Pressable style={[styles.roundButton, styles.declineButton]} onPress={call.declineCall} hitSlop={10}>
                <Ionicons name="call" size={28} color="#fff" style={styles.declineIcon} />
              </Pressable>
              <Pressable style={[styles.roundButton, styles.acceptButton]} onPress={call.acceptCall} hitSlop={10}>
                <Ionicons name="call" size={28} color="#fff" />
              </Pressable>
            </>
          ) : (
            <>
              {call.phase === "active" && (
                <Pressable
                  style={[styles.roundButton, styles.muteButton, call.isMuted && styles.muteButtonActive]}
                  onPress={call.toggleMute}
                  hitSlop={10}
                >
                  <Ionicons name={call.isMuted ? "mic-off" : "mic"} size={24} color={call.isMuted ? colors.navy : "#fff"} />
                </Pressable>
              )}
              <Pressable style={[styles.roundButton, styles.declineButton]} onPress={call.hangUp} hitSlop={10}>
                <Ionicons name="call" size={28} color="#fff" style={styles.declineIcon} />
              </Pressable>
            </>
          )}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0B2944", alignItems: "center" },
  remoteVideo: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0 },
  remotePlaceholder: { backgroundColor: "#0B3B63", alignItems: "center", justifyContent: "center" },
  audioMascot: { width: 140, height: 140, opacity: 0.9 },
  nameBar: { flexDirection: "row", alignItems: "center", marginTop: 90, paddingHorizontal: 24 },
  nameText: { color: "#fff", fontSize: 26, fontWeight: "800" },
  nameGenderIcon: { marginLeft: 8 },
  statusText: { color: "rgba(255,255,255,0.8)", fontSize: 15, marginTop: 8 },
  localVideo: {
    position: "absolute",
    top: 50,
    right: 20,
    width: 110,
    height: 150,
    borderRadius: 14,
    backgroundColor: "#082944",
  },
  controls: { position: "absolute", bottom: 60, flexDirection: "row", gap: 28 },
  roundButton: { width: 64, height: 64, borderRadius: 32, alignItems: "center", justifyContent: "center" },
  acceptButton: { backgroundColor: colors.sage },
  declineButton: { backgroundColor: colors.danger },
  declineIcon: { transform: [{ rotate: "135deg" }] },
  muteButton: { backgroundColor: "rgba(255,255,255,0.2)" },
  muteButtonActive: { backgroundColor: "#fff" },
});
