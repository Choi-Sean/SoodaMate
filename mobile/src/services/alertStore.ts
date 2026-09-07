export interface AlertButtonSpec {
  text: string;
  onPress?: () => void;
  style?: "default" | "cancel" | "destructive";
}

export interface AlertRequest {
  title: string;
  message?: string;
  buttons: AlertButtonSpec[];
}

/** Minimal pub-sub so a plain function (showAlert, called from anywhere -
 * not just component bodies) can trigger the singleton <AlertHost/> mounted
 * once at the app root. Only used on web - see utils/alert.ts. */
let current: AlertRequest | null = null;
let listeners: Array<(req: AlertRequest | null) => void> = [];

export function subscribe(listener: (req: AlertRequest | null) => void): () => void {
  listeners.push(listener);
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}

export function publish(request: AlertRequest | null): void {
  current = request;
  listeners.forEach((l) => l(current));
}

export function getCurrent(): AlertRequest | null {
  return current;
}
