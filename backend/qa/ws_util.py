import threading


def ws_recv(ws, timeout=10):
    """receive_json() with a timeout so a missing frame fails a case instead of hanging the run."""
    box = []

    def go():
        try:
            box.append(ws.receive_json())
        except Exception as e:  # noqa: BLE001
            box.append(e)

    t = threading.Thread(target=go, daemon=True)
    t.start()
    t.join(timeout)
    if box and not isinstance(box[0], Exception):
        return box[0]
    return None
