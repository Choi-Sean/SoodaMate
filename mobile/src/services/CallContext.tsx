import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { Platform, Vibration } from "react-native";
import { useQueryClient } from "@tanstack/react-query";

import { getIceServers } from "../api/calls";
import { useSocket } from "./SocketProvider";
import {
  MediaStream,
  RTCIceCandidate,
  RTCPeerConnection,
  RTCSessionDescription,
  mediaDevices,
  webrtcAvailable,
} from "./webrtc";
import type { Gender, Match } from "../types";

export type CallPhase = "idle" | "outgoing" | "incoming" | "active";

// Matches CALL_END_REASONS in backend/app/routers/ws_chat.py.
export type CallEndReason = "hangup" | "declined" | "busy" | "missed" | "timeout" | "peer_offline" | "error";

interface CallPeer {
  matchId: string;
  otherUserId: string;
  otherDisplayName: string;
  otherGender: Gender | null;
}

interface CallState {
  phase: CallPhase;
  peer: CallPeer | null;
  localStreamURL: string | null;
  remoteStreamURL: string | null;
  isMuted: boolean;
  /** Set right before returning to "idle" so the UI can show why the call ended
   * (declined / no answer / offline / error) for a moment before dismissing. */
  lastEndReason: CallEndReason | null;
  /** A request the server rejected before any ringing started (e.g.
   * "call_restricted" — see routers/ws_chat.py's Bumble-style call-first rule). */
  startError: string | null;
}

interface CallContextValue extends CallState {
  startCall: (peer: CallPeer) => Promise<void>;
  acceptCall: () => Promise<void>;
  declineCall: () => void;
  hangUp: () => void;
  toggleMute: () => void;
  dismissEndReason: () => void;
}

const initialState: CallState = {
  phase: "idle",
  peer: null,
  localStreamURL: null,
  remoteStreamURL: null,
  isMuted: false,
  lastEndReason: null,
  startError: null,
};

const CallContext = createContext<CallContextValue | null>(null);

// Vibrates continuously while ringing — this is the "phone is ringing" signal
// while the app is open. Deliberately NOT a real ringtone sound: that needs a
// bundled audio asset (expo-audio) which doesn't exist yet, and a truly
// continuous ring/wake-on-closed-app experience needs iOS PushKit+CallKit /
// an Android foreground service (separately scoped native work — see the
// incoming/missed-call push notifications for what reaches a closed app).
const RING_VIBRATION_PATTERN = [0, 700, 400]; // wait, buzz, pause — repeats

export function CallProvider({ children }: { children: ReactNode }) {
  const { send, addListener } = useSocket();
  const queryClient = useQueryClient();
  const [state, setState] = useState<CallState>(initialState);

  const pcRef = useRef<any>(null);
  const localStreamRef = useRef<any>(null);
  const callIdRef = useRef<string | null>(null);
  // Trickle ICE candidates the caller generates arrive before call_answer
  // gives us the server-assigned call_id (the caller's own call_offer frame
  // never gets one back — only the callee's copy of it does), so they're
  // queued here and flushed once callIdRef is set.
  const pendingLocalCandidatesRef = useRef<any[]>([]);
  const isCallerRef = useRef(false);

  const teardown = useCallback((reason: CallEndReason | null) => {
    Vibration.cancel();
    try {
      pcRef.current?.close();
    } catch {
      // already closed
    }
    pcRef.current = null;
    try {
      localStreamRef.current?.getTracks().forEach((t: any) => t.stop());
    } catch {
      // already stopped
    }
    localStreamRef.current = null;
    callIdRef.current = null;
    pendingLocalCandidatesRef.current = [];
    isCallerRef.current = false;
    setState({ ...initialState, lastEndReason: reason });
  }, []);

  const setupPeerConnection = useCallback(
    async (matchId: string) => {
      const iceServers = await getIceServers().catch(() => []);
      const pc = new RTCPeerConnection({ iceServers });
      pcRef.current = pc;

      pc.onicecandidate = (event: any) => {
        if (!event.candidate) return;
        const candidate = event.candidate.toJSON ? event.candidate.toJSON() : event.candidate;
        if (callIdRef.current) {
          send({ type: "call_ice_candidate", call_id: callIdRef.current, candidate });
        } else {
          pendingLocalCandidatesRef.current.push(candidate);
        }
      };

      pc.ontrack = (event: any) => {
        const stream = event.streams?.[0];
        if (stream) setState((prev) => ({ ...prev, remoteStreamURL: stream.toURL() }));
      };

      pc.onconnectionstatechange = () => {
        if (pc.connectionState === "failed") {
          send({ type: "call_end", call_id: callIdRef.current, reason: "error" });
          teardown("error");
        }
      };

      return pc;
    },
    [send, teardown]
  );

  const startCall = useCallback(
    async (peer: CallPeer) => {
      if (!webrtcAvailable) return;
      if (state.phase !== "idle") return;
      setState({ ...initialState, phase: "outgoing", peer });
      isCallerRef.current = true;
      try {
        const localStream = await mediaDevices.getUserMedia({ audio: true, video: true });
        localStreamRef.current = localStream;
        setState((prev) => ({ ...prev, localStreamURL: localStream.toURL() }));

        const pc = await setupPeerConnection(peer.matchId);
        localStream.getTracks().forEach((track: any) => pc.addTrack(track, localStream));

        const offer = await pc.createOffer({});
        await pc.setLocalDescription(offer);
        send({ type: "call_offer", match_id: peer.matchId, sdp: offer.sdp });
      } catch {
        teardown("error");
      }
    },
    [state.phase, setupPeerConnection, send, teardown]
  );

  const acceptCall = useCallback(async () => {
    if (state.phase !== "incoming" || !state.peer || !callIdRef.current) return;
    Vibration.cancel();
    try {
      const localStream = await mediaDevices.getUserMedia({ audio: true, video: true });
      localStreamRef.current = localStream;
      setState((prev) => ({ ...prev, phase: "active", localStreamURL: localStream.toURL() }));

      const pc = pcRef.current;
      localStream.getTracks().forEach((track: any) => pc.addTrack(track, localStream));

      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      send({ type: "call_answer", call_id: callIdRef.current, sdp: answer.sdp });
    } catch {
      send({ type: "call_end", call_id: callIdRef.current, reason: "error" });
      teardown("error");
    }
  }, [state.phase, state.peer, send, teardown]);

  const declineCall = useCallback(() => {
    if (callIdRef.current) send({ type: "call_end", call_id: callIdRef.current, reason: "declined" });
    teardown("declined");
  }, [send, teardown]);

  const hangUp = useCallback(() => {
    if (callIdRef.current) send({ type: "call_end", call_id: callIdRef.current, reason: "hangup" });
    teardown("hangup");
  }, [send, teardown]);

  const toggleMute = useCallback(() => {
    const stream = localStreamRef.current;
    if (!stream) return;
    const next = !state.isMuted;
    stream.getAudioTracks().forEach((track: any) => {
      track.enabled = !next;
    });
    setState((prev) => ({ ...prev, isMuted: next }));
  }, [state.isMuted]);

  const dismissEndReason = useCallback(() => {
    setState((prev) => ({ ...prev, lastEndReason: null, startError: null }));
  }, []);

  // The one shared socket's frames are broadcast to every listener (see
  // SocketProvider) — this filters for call_* and the call-specific error
  // codes, mirroring how useChatSocket filters for message/blind_reveal_*.
  useEffect(() => {
    return addListener(async (data) => {
      switch (data.type) {
        case "call_offer": {
          // Busy: already on a call — decline automatically rather than
          // silently dropping the offer, so the caller sees why.
          if (state.phase !== "idle") {
            send({ type: "call_end", call_id: data.call_id, reason: "busy" });
            return;
          }
          if (!webrtcAvailable) return;
          callIdRef.current = data.call_id;
          isCallerRef.current = false;
          const pc = await setupPeerConnection(data.match_id);
          try {
            await pc.setRemoteDescription(new RTCSessionDescription({ type: "offer", sdp: data.sdp }));
          } catch {
            teardown("error");
            return;
          }
          // The offer frame only carries caller_id — the display name/gender
          // come from the matches list react-query already keeps warm
          // (ChatListScreen/ChatRoomScreen both read the same ["matches"]
          // cache), same real name a call is always allowed to show (calls
          // are blocked entirely for a still-anonymous blind match).
          const cachedMatches = queryClient.getQueryData<Match[]>(["matches"]);
          const cachedMatch = cachedMatches?.find((m) => m.id === data.match_id);
          setState({
            ...initialState,
            phase: "incoming",
            peer: {
              matchId: data.match_id,
              otherUserId: data.caller_id,
              otherDisplayName: cachedMatch?.other_display_name ?? "",
              otherGender: cachedMatch?.other_gender ?? null,
            },
          });
          if (Platform.OS !== "web") Vibration.vibrate(RING_VIBRATION_PATTERN, true);
          break;
        }
        case "call_answer": {
          if (!isCallerRef.current || !pcRef.current) return;
          callIdRef.current = data.call_id;
          try {
            await pcRef.current.setRemoteDescription(new RTCSessionDescription({ type: "answer", sdp: data.sdp }));
          } catch {
            teardown("error");
            return;
          }
          for (const candidate of pendingLocalCandidatesRef.current.splice(0)) {
            send({ type: "call_ice_candidate", call_id: data.call_id, candidate });
          }
          setState((prev) => ({ ...prev, phase: "active" }));
          break;
        }
        case "call_ice_candidate": {
          if (!pcRef.current || data.call_id !== callIdRef.current) return;
          try {
            await pcRef.current.addIceCandidate(new RTCIceCandidate(data.candidate));
          } catch {
            // A candidate that fails to add (e.g. arrives after the connection
            // closed) is never fatal — WebRTC just tries the next one.
          }
          break;
        }
        case "call_end": {
          if (data.call_id !== callIdRef.current && state.phase !== "outgoing") return;
          teardown(data.reason ?? null);
          break;
        }
        case "error": {
          if (data.code === "call_restricted" || data.code === "call_not_allowed" || data.code === "rate_limited") {
            if (state.phase === "outgoing") {
              teardown(null);
              setState((prev) => ({ ...prev, startError: data.code }));
            }
          }
          break;
        }
        default:
          break;
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [addListener, state.phase, send, setupPeerConnection, teardown]);

  // Belt-and-suspenders cleanup if the provider itself ever unmounts mid-call
  // (e.g. logout) — MediaStream tracks must not keep the camera/mic held open.
  useEffect(() => {
    return () => {
      Vibration.cancel();
      try {
        pcRef.current?.close();
      } catch {
        // already closed
      }
      try {
        localStreamRef.current?.getTracks().forEach((t: any) => t.stop());
      } catch {
        // already stopped
      }
    };
  }, []);

  const value: CallContextValue = {
    ...state,
    startCall,
    acceptCall,
    declineCall,
    hangUp,
    toggleMute,
    dismissEndReason,
  };

  return <CallContext.Provider value={value}>{children}</CallContext.Provider>;
}

export function useCall(): CallContextValue {
  const ctx = useContext(CallContext);
  if (!ctx) {
    throw new Error("useCall must be used within a CallProvider (mounted once in RootNavigator's MainApp)");
  }
  return ctx;
}

// Re-exported so screens can render a video view without importing the
// native/web split module directly.
export { MediaStream };
