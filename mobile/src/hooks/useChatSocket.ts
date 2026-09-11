import { useCallback, useEffect, useRef, useState } from "react";

import { env } from "../config/env";
import { useAuthStore } from "../store/authStore";
import type { ChatMessage } from "../types";

function wsBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.replace(/^http/, "ws");
}

export interface ChatSocketError {
  code: string;
  match_id: string;
}

export function useChatSocket(
  matchId: string,
  onMessage: (msg: ChatMessage) => void,
  onError?: (err: ChatSocketError) => void,
  onBlindRevealUpdate?: () => void
) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);

  // Keep the latest callbacks in refs so the connect effect only depends on
  // (accessToken, matchId) — inline arrow functions passed by the caller
  // would otherwise reconnect the socket on every render.
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;
  const onBlindRevealUpdateRef = useRef(onBlindRevealUpdate);
  onBlindRevealUpdateRef.current = onBlindRevealUpdate;

  useEffect(() => {
    if (!accessToken) return;

    const url = `${wsBaseUrl(env.apiBaseUrl)}/ws/chat?token=${encodeURIComponent(accessToken)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string);
        if (data.type === "message" && data.match_id === matchId) {
          onMessageRef.current({
            id: data.message_id,
            match_id: data.match_id,
            sender_id: data.sender_id,
            content: data.content,
            message_type: data.message_type ?? "text",
            image_url: data.image_url ?? null,
            original_language: data.original_language ?? null,
            translated_content: data.translated_content ?? null,
            translated_language: data.translated_language ?? null,
            sent_at: data.sent_at,
            delivered_at: null,
            read_at: null,
          });
        } else if (data.type === "error" && data.match_id === matchId) {
          onErrorRef.current?.({ code: data.code, match_id: data.match_id });
        } else if (
          (data.type === "blind_reveal_requested" || data.type === "blind_reveal_accepted") &&
          data.match_id === matchId
        ) {
          onBlindRevealUpdateRef.current?.();
        }
      } catch {
        // ignore malformed frames
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [accessToken, matchId]);

  // Guards against "Still in CONNECTING state" — markRead in particular
  // tends to fire from a mount effect that runs before ws.onopen has, since
  // opening a WebSocket is always async.
  const sendMessage = useCallback(
    (content: string) => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) return;
      wsRef.current.send(JSON.stringify({ type: "message", match_id: matchId, message_type: "text", content }));
    },
    [matchId]
  );

  const sendImageMessage = useCallback(
    (imageObjectPath: string) => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) return;
      wsRef.current.send(
        JSON.stringify({ type: "message", match_id: matchId, message_type: "image", image_object_path: imageObjectPath })
      );
    },
    [matchId]
  );

  const markRead = useCallback(() => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: "read", match_id: matchId }));
  }, [matchId]);

  return { connected, sendMessage, sendImageMessage, markRead };
}
