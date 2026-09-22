// Thin re-export so CallContext.tsx never imports react-native-webrtc directly —
// same platform-split convention as services/ads.native.ts / rewardedAd.native.ts,
// needed because react-native-webrtc has no web implementation at all.
import { MediaStream, RTCIceCandidate, RTCPeerConnection, RTCSessionDescription, RTCView, mediaDevices } from "react-native-webrtc";

export const webrtcAvailable = true;
export { MediaStream, RTCIceCandidate, RTCPeerConnection, RTCSessionDescription, RTCView, mediaDevices };
