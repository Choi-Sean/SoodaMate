"""One more pending face-verification user so the admin page's Reject dialog can be driven through the UI."""
from qa import harness as H
from qa.ui_seed import phone_user, portrait, tc


def main():
    H.start()
    u = phone_user("+12135550111", "QA거절UI", "male", "female", 30, "X", (200, 200, 255), lang="en")
    for kind, data in (("selfie", portrait("X", (200, 200, 255))), ("id_photo", H.make_jpeg("ID CARD REJECT", (900, 560), (255, 230, 200)))):
        pr = tc.post("/verification/face/presign", headers=u.h, json={"content_type": "image/jpeg", "kind": kind}).json()
        H.put_to_r2(pr["upload_url"], data, "image/jpeg")
        if kind == "selfie":
            sp = pr["gcs_object_path"]
        else:
            ip = pr["gcs_object_path"]
    r = tc.post("/verification/face/submit", headers=u.h, json={"selfie_object_path": sp, "id_photo_object_path": ip})
    print("submit", r.status_code, r.json())
    H.stop()


main()
