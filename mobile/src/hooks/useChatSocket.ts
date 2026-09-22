import { useCallback, useEffect, useRef } from "react";

import { useSocket } from "../services/SocketProvider";
import type { ChatMessage } from "../types";

export interface ChatSocketError {
  code: string;
  match_id: string;
}

/** Thin wrapper over the single app-level socket (services/SocketProvider.tsx) —
 * public API and behavior are unchanged from when this hook owned its own
 * WebSocket per screen; only where the connection itself lives has moved. */
export function useChatSocket(
  matchId: string,
  onMessage: (msg: ChatMessage) => void,
  onError?: (err: ChatSocketError) => void,
  onBlindRevealUpdate?: () => void
) {
  const { connected, send, addListener } = useSocket();

  // Keep the latest callbacks in refs so the subscribe effect only depends on
  // (addListener, matchId) — inline arrow functions passed by the caller
  // would otherwise resubscribe on every render.
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;
  const onBlindRevealUpdateRef = useRef(onBlindRevealUpdate);
  onBlindRevealUpdateRef.current = onBlindRevealUpdate;

  useEffect(() => {
    return addListener((data) => {
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
    });
  }, [addListener, matchId]);

  const sendMessage = useCallback(
    (content: string) => send({ type: "message", match_id: matchId, message_type: "text", content }),
    [send, matchId]
  );

  const sendImageMessage = useCallback(
    (imageObjectPath: string) =>
      send({ type: "message", match_id: matchId, message_type: "image", image_object_path: imageObjectPath }),
    [send, matchId]
  );

  const markRead = useCallback(() => send({ type: "read", match_id: matchId }), [send, matchId]);

  return { connected, sendMessage, sendImageMessage, markRead };
}
