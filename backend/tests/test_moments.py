import pytest

from tests.helpers import create_user_with_profile


def _path(uid, n):
    return f"users/{uid}/moments/img{n}.jpg"


@pytest.mark.asyncio
async def test_create_list_and_delete_moment(client):
    uid, headers = await create_user_with_profile(client, "moment1@example.com")

    r = await client.post("/moments", headers=headers, json={"image_object_path": _path(uid, 1), "caption": "hiked today"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["caption"] == "hiked today"
    assert body["image_url"].endswith(_path(uid, 1))
    moment_id = body["id"]

    listing = await client.get("/moments/me", headers=headers)
    assert [m["id"] for m in listing.json()] == [moment_id]

    other_uid, other_headers = await create_user_with_profile(client, "momentOther@example.com")
    wrong_delete = await client.delete(f"/moments/{moment_id}", headers=other_headers)
    assert wrong_delete.status_code == 404

    ok_delete = await client.delete(f"/moments/{moment_id}", headers=headers)
    assert ok_delete.status_code == 204
    assert (await client.get("/moments/me", headers=headers)).json() == []


@pytest.mark.asyncio
async def test_moments_are_a_rolling_window_of_six(client):
    uid, headers = await create_user_with_profile(client, "moment2@example.com")

    for i in range(8):
        r = await client.post("/moments", headers=headers, json={"image_object_path": _path(uid, i)})
        assert r.status_code == 201

    listing = await client.get("/moments/me", headers=headers)
    paths = [m["image_url"].split("/")[-1] for m in listing.json()]
    assert len(paths) == 6
    # Newest first, oldest two (img0, img1) pruned.
    assert paths == ["img7.jpg", "img6.jpg", "img5.jpg", "img4.jpg", "img3.jpg", "img2.jpg"]


@pytest.mark.asyncio
async def test_moments_appear_on_other_users_candidate_card(client):
    viewer_id, viewer_headers = await create_user_with_profile(
        client, "momentViewer@example.com", gender="male", interested_in="female"
    )
    cand_id, cand_headers = await create_user_with_profile(
        client, "momentCand@example.com", gender="female", interested_in="male"
    )
    await client.post("/moments", headers=cand_headers, json={"image_object_path": _path(cand_id, 1), "caption": "coffee ☕"})

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    assert resp.status_code == 200
    card = next((c for c in resp.json() if c["user_id"] == cand_id), None)
    assert card is not None
    assert len(card["moments"]) == 1
    assert card["moments"][0]["caption"] == "coffee ☕"
