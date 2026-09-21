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
    sendDefaultPii: false,
    // Last line of defence: whatever a caller attaches, never ship credentials.
    beforeSend(event) {
      if (event.request?.headers) {
        for (const key of Object.keys(event.request.headers)) {
          if (/authorization|cookie|token/i.test(key)) event.request.headers[key] = "[redacted]";
        }
      }
      if (event.request?.url) event.request.url = event.request.url.replace(/([?&#]token=)[^&#]*/gi, "$1[redacted]");
      return event;
    },
    beforeBreadcrumb(breadcrumb) {
      const url = (breadcrumb.data as { url?: unknown } | undefined)?.url;
      if (typeof url === "string" && /token=/i.test(url) && breadcrumb.data) {
        breadcrumb.data.url = url.replace(/([?&#]token=)[^&#]*/gi, "$1[redacted]");
      }
      return breadcrumb;
    },
  });
  initialized = true;
}

type ReportLevel = "fatal" | "error" | "warning";

export function reportError(error: unknown, context?: Record<string, unknown>, level: ReportLevel = "error"): void {
  if (!env.sentryDsn) {
    if (__DEV__) console.error("[errorReporting]", error, context);
    return;
  }
  Sentry.captureException(error, { extra: context, level });
}
