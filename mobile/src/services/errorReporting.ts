import * as Sentry from "@sentry/react-native";

import { env } from "../config/env";

// No Sentry project exists yet (env.sentryDsn is blank until one does) — every
// export here is a safe no-op in that case, so the app behaves exactly as it
// did before this file existed for anyone who hasn't set EXPO_PUBLIC_SENTRY_DSN.
let initialized = false;

export function initErrorReporting(): void {
  if (initialized || !env.sentryDsn) return;
  Sentry.init({
    dsn: env.sentryDsn,
    // Native (iOS/Android) crash capture is on by default the moment this
    // runs — no config-plugin/build-step needed for that part. The plugin
    // (not wired up yet, see app.config.js) only improves *symbolication*
    // (readable file/line instead of a minified frame) by uploading source
    // maps at build time.
    tracesSampleRate: 0.2,
  });
  initialized = true;
}

export function reportError(error: unknown, context?: Record<string, unknown>): void {
  if (!env.sentryDsn) {
    if (__DEV__) console.error("[errorReporting]", error, context);
    return;
  }
  Sentry.captureException(error, context ? { extra: context } : undefined);
}
