from datasette import hookimpl
import json


def pfp(letter, fg="white", bg="black"):
    return f"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32'%3E%3Ccircle cx='16' cy='16' r='16' fill='{bg}'%3E%3C/circle%3E%3Ctext fill='{fg}' x='16' y='16' text-anchor='middle' dominant-baseline='middle'%3E{letter}%3C/text%3E%3C/svg%3E"


ACTORS = {
    ###### DAILY PLANET ######
    "clark": {
        "id": "clark",
        "name": "Clark Kent",
        "newsroom": "daily-planet",
        "gender": "male",
        "profile_picture_url": pfp("C", bg="blue"),
    },
    "lois": {
        "id": "lois",
        "name": "Lois Lane",
        "newsroom": "daily-planet",
        "gender": "female",
        "profile_picture_url": pfp("L", bg="red"),
    },
    "jimmy": {
        "id": "jimmy",
        "name": "Jimmy Olsen",
        "newsroom": "daily-planet",
        "gender": "male",
        "profile_picture_url": pfp("J", bg="orange"),
    },
    ###### GOTHAM GAZETTE ######
    "bruce": {
        "id": "bruce",
        "name": "Bruce Wayne",
        "newsroom": "gotham-gazette",
        "gender": "male",
        "profile_picture_url": pfp("B", bg="black"),
    },
    "alfred": {
        "id": "alfred",
        "name": "Alfred Pennyworth",
        "newsroom": "gotham-gazette",
        "gender": "male",
        "profile_picture_url": pfp("A", bg="gray"),
    },
    "selina": {
        "id": "selina",
        "name": "Selina Kyle",
        "newsroom": "gotham-gazette",
        "gender": "female",
        "profile_picture_url": pfp("S", bg="purple"),
    },
}

# Build a JS-friendly list of users for the entrypoint
_USERS_JS = json.dumps(
    [{"name": k, "newsroom": v["newsroom"]} for k, v in ACTORS.items()]
)


def _user_profiles_installed():
    """True if datasette-user-profiles is importable in this environment."""
    try:
        import datasette_user_profiles  # noqa: F401
    except ImportError:
        return False
    return True


@hookimpl
def actor_from_request(datasette, request):
    actor_id = request.cookies.get("actor")
    for key in ACTORS:
        if key == actor_id:
            return ACTORS[key]


if _user_profiles_installed():

    @hookimpl
    def datasette_resolve_actors(datasette, actor_ids):
        """Resolve gotham's demo actors via the user-profiles sub-hook.

        user-profiles is the single owner of the core ``actors_from_ids`` hook
        (it is ``firstresult=True``). When it is installed we contribute our
        actors through its ``datasette_resolve_actors`` sub-hook instead of
        competing for the core hook, so seeded profiles and gotham resolution
        agree on names/avatars.
        """
        return {
            actor_id: ACTORS[actor_id]
            for actor_id in actor_ids
            if actor_id in ACTORS
        }

else:

    @hookimpl
    def actors_from_ids(datasette, actor_ids):
        # No user-profiles: own the core hook directly (standalone demo).
        return {
            actor_id: ACTORS[actor_id]
            for actor_id in actor_ids
            if actor_id in ACTORS
        }


@hookimpl
def startup(datasette):
    """Seed gotham's demo actors into datasette-user-profiles, if installed.

    user-profiles never auto-populates ``datasette_user_profiles``, so without
    this the people-search in the share dialog returns nothing for gotham's
    actors. We upsert each actor's display name (and its data-URL profile
    picture as a photo) so name-search surfaces them with friendly names and
    avatars. No-op when user-profiles is absent.
    """

    async def inner():
        if not _user_profiles_installed():
            return
        internal_db = datasette.get_internal_database()

        # Ensure the profiles tables exist before we seed: startup hook order
        # across plugins is not guaranteed, so apply user-profiles' internal
        # migrations (idempotent) ourselves rather than relying on its startup
        # having run first.
        try:
            from sqlite_utils import Database as SqliteUtilsDatabase
            from datasette_user_profiles.internal_migrations import (
                internal_migrations,
            )

            def migrate(conn):
                internal_migrations.apply(SqliteUtilsDatabase(conn))

            await internal_db.execute_write_fn(migrate)
        except Exception:
            # If migrations can't be applied here, fall back to assuming
            # user-profiles' own startup created the tables.
            pass

        # Decode each actor's data-URL profile picture into (bytes, content_type)
        # so we can seed datasette_user_profile_photos. The gotham pictures are
        # SVG data URLs (data:image/svg+xml,<percent-encoded svg>); fall back to
        # the initials chip when a picture can't be decoded.
        photos = {}
        for actor_id, info in ACTORS.items():
            decoded = _decode_data_url(info.get("profile_picture_url"))
            if decoded is not None:
                photos[actor_id] = decoded

        def write(conn):
            with conn:
                for actor_id, info in ACTORS.items():
                    conn.execute(
                        """
                        INSERT INTO datasette_user_profiles (actor_id, display_name)
                        VALUES (?, ?)
                        ON CONFLICT(actor_id) DO UPDATE SET
                            display_name = excluded.display_name,
                            updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now')
                        """,
                        [actor_id, info["name"]],
                    )
                    photo = photos.get(actor_id)
                    if photo is not None:
                        photo_bytes, content_type = photo
                        conn.execute(
                            """
                            INSERT INTO datasette_user_profile_photos
                                (actor_id, photo, content_type)
                            VALUES (?, ?, ?)
                            ON CONFLICT(actor_id) DO UPDATE SET
                                photo = excluded.photo,
                                content_type = excluded.content_type,
                                updated_at = strftime('%Y-%m-%dT%H:%M:%f', 'now')
                            """,
                            [actor_id, photo_bytes, content_type],
                        )

        await internal_db.execute_write_fn(write)

    return inner


def _decode_data_url(data_url):
    """Decode a ``data:`` URL into ``(bytes, content_type)`` or ``None``.

    Handles both percent-encoded (gotham's SVG pictures) and base64 data URLs.
    """
    if not data_url or not data_url.startswith("data:"):
        return None
    try:
        header, _, payload = data_url[len("data:"):].partition(",")
        if not _:
            return None
        is_base64 = header.endswith(";base64")
        content_type = header[: -len(";base64")] if is_base64 else header
        content_type = content_type or "application/octet-stream"
        if is_base64:
            import base64

            body = base64.b64decode(payload)
        else:
            from urllib.parse import unquote

            body = unquote(payload).encode("utf-8")
        if not body or len(body) > 1048576:
            return None
        return body, content_type
    except Exception:
        return None


@hookimpl
def datasette_comments_mentioned(datasette):
    return "Response from this plugin hook"


@hookimpl
def datasette_comments_users():
    async def inner():
        return list(ACTORS.values())

    return inner


def debug_bar_items(datasette):
    return {
        "label": "User Switch",
        "entrypoint": """function(el) {
            var users = """
        + _USERS_JS
        + """;
            var icons = {
                'daily-planet': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" fill="#0066cc" stroke="#004499" stroke-width="1.5"/><circle cx="8" cy="8" r="2" fill="white"/></svg>',
                'gotham-gazette': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" fill="#333" stroke="#000" stroke-width="1.5"/><path d="M5 5 L11 11 M11 5 L5 11" stroke="#fff" stroke-width="2"/></svg>'
            };
            function getCookie(name) {
                var nameEQ = name + "=";
                var ca = document.cookie.split(';');
                for (var i = 0; i < ca.length; i++) {
                    var c = ca[i].trim();
                    if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length);
                }
                return null;
            }
            function setCookie(name, value) {
                var date = new Date();
                date.setTime(date.getTime() + 365*24*60*60*1000);
                document.cookie = name + "=" + value + ";expires=" + date.toUTCString() + ";path=/";
            }
            var current = getCookie('actor') || 'clark';
            var currentUser = users.find(function(u) { return u.name === current; }) || users[0];

            var info = document.createElement('div');
            info.style.cssText = 'display:flex;align-items:center;gap:8px;margin-bottom:8px;';
            info.innerHTML = '<span>' + icons[currentUser.newsroom] + '</span>' +
                '<span style="font-weight:bold;color:#333;">' + currentUser.name + '</span>' +
                '<span style="color:#999;font-size:12px;">(' + currentUser.newsroom + ')</span>';
            el.appendChild(info);

            var select = document.createElement('select');
            select.style.cssText = 'width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:13px;cursor:pointer;background:white;';
            users.forEach(function(user) {
                var opt = document.createElement('option');
                opt.value = user.name;
                opt.textContent = user.name + ' (' + user.newsroom + ')';
                if (user.name === currentUser.name) opt.selected = true;
                select.appendChild(opt);
            });
            select.addEventListener('change', function(e) {
                setCookie('actor', e.target.value);
                location.reload();
            });
            el.appendChild(select);
        }""",
    }
