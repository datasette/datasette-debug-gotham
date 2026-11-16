from datasette.app import Datasette
import pytest


@pytest.mark.asyncio
async def test_plugin_is_installed():
    datasette = Datasette(memory=True)
    response = await datasette.client.get("/-/plugins.json")
    assert response.status_code == 200
    installed_plugins = {p["name"] for p in response.json()}
    assert "datasette-debug-gotham" in installed_plugins


@pytest.mark.asyncio
async def test_seeds_actors_into_user_profiles():
    """When datasette-user-profiles is installed, gotham's actors are seeded
    into its directory via the datasette_user_profile_seeds hook.

    Skipped when user-profiles (with the seed hook) is not available.
    """
    pytest.importorskip("datasette_user_profiles.seed")

    ds = Datasette(memory=True)
    await ds.invoke_startup()
    internal = ds.get_internal_database()

    rows = (
        await internal.execute(
            "select actor_id, display_name from datasette_user_profiles"
        )
    ).rows
    names = {r["actor_id"]: r["display_name"] for r in rows}
    assert names["clark"] == "Clark Kent"
    assert names["bruce"] == "Bruce Wayne"

    # The data: SVG profile picture is decoded and seeded as a photo.
    photo = (
        await internal.execute(
            "select content_type from datasette_user_profile_photos"
            " where actor_id = 'clark'"
        )
    ).first()
    assert photo is not None
    assert photo["content_type"] == "image/svg+xml"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cookies,expected_id",
    [
        ({"actor": "clark"}, "clark"),
        ({"actor": "selina"}, "selina"),
        # No cookie, an empty one, or one naming nobody: signed out
        ({}, None),
        ({"actor": ""}, None),
        ({"actor": "joker"}, None),
    ],
)
async def test_actor_cookie(cookies, expected_id):
    datasette = Datasette(memory=True)
    response = await datasette.client.get("/-/actor.json", cookies=cookies)
    assert response.status_code == 200
    actor = response.json()["actor"]
    assert (actor or {}).get("id") == expected_id


def test_switcher_offers_signed_out():
    from datasette_debug_gotham import debug_bar_items

    entrypoint = debug_bar_items(datasette=None)["entrypoint"]
    assert "Signed out (no actor)" in entrypoint
    # Choosing it removes the cookie instead of setting one
    assert "clearCookie('actor')" in entrypoint
    # ... and a missing cookie is no longer shown as the first user
    assert "|| 'clark'" not in entrypoint
