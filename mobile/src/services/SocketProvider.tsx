import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { env } from "../config/env";
import { useAuthStore } from "../store/authStore";

type SocketListener = (data: any) => void;

interface SocketContextValue {
  connected: boolean;
  send: (payload: object) => void;
  /** Every parsed frame from the socket is broadcast to every listener — each
   * consumer (useChatSocket, the call manager) filters for the `type`/`match_id`
   * it cares about, same as the old per-screen socket's onmessage switch did
   * inline. Returns an unsubscribe function. */
  addListener: (listener: SocketListener) => () => void;
}

const SocketContext = createContext<SocketContextValue | null>(null);

function wsBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.replace(/^http/, "ws");
}

/** Owns the single app-level WebSocket connection to /ws/chat.
 *
 * The server allows exactly one connection per user (backend's
 * ConnectionManager — "v1: single device"): connecting a second one silently
 * closes the first. Every previous version of this app opened a fresh socket
 * per ChatRoomScreen mount, which worked for messaging (only one chat room is
 * ever open at a time) but meant an incoming call frame only ever reached
 * someone already sitting in that exact chat. Mounted once in RootNavigator's
 * MainApp, above both chat screens and the app-wide call listener, so they
 * share this one connection no matter which screen is on top.
 *
 * Behavior is otherwise unchanged from the old per-screen socket: connects
 * once per login session (effect depends only on accessToken), does not
 * auto-reconnect after a drop. */
export function SocketProvider({ children }: { children: ReactNode }) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const listenersRef = useRef<Set<SocketListener>>(new Set());

  useEffect(() => {
    if (!accessToken) {
      setConnected(false);
      return;
    }

    const url = `${wsBaseUrl(env.apiBaseUrl)}/ws/chat?token=${encodeURIComponent(accessToken)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (event) => {
      let data: any;
      try {
        data = JSON.parse(event.data as string);
      } catch {
        return; // ignore malformed frames
      }
      // Snapshot before iterating: a listener that unsubscribes itself (or
      // subscribes a new one) mid-dispatch must not mutate the set being iterated.
      for (const listener of Array.from(listenersRef.current)) {
        listener(data);
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [accessToken]);

  const send = useCallback((payload: object) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify(payload));
  }, []);

  const addListener = useCallback((listener: SocketListener) => {
    listenersRef.current.add(listener);
    return () => {
      listenersRef.current.delete(listener);
    };
  }, []);

  const value = useMemo(() => ({ connected, send, addListener }), [connected, send, addListener]);

  return <SocketContext.Provider value={value}>{children}</SocketContext.Provider>;
}

export function useSocket(): SocketContextValue {
  const ctx = useContext(SocketContext);
  if (!ctx) {
    throw new Error("useSocket must be used within a SocketProvider (mounted once in RootNavigator's MainApp)");
  }
  return ctx;
}
