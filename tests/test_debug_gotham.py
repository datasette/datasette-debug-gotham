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
