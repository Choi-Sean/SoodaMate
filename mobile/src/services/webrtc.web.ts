// react-native-webrtc has no web implementation at all (unlike AdMob, which at
// least has Google's web SDK) — video calling is simply unavailable on web.
// CallContext.tsx checks webrtcAvailable before doing anything else, so
// nothing here is ever actually called; these exist only so the bare
// `./webrtc` import resolves to *something* in a web Metro bundle.
export const webrtcAvailable = false;
export const MediaStream: any = null;
export const RTCIceCandidate: any = null;
export const RTCPeerConnection: any = null;
export const RTCSessionDescription: any = null;
export const RTCView: any = null;
export const mediaDevices: any = null;
