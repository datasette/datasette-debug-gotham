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
    def datasette_user_profile_seeds(datasette):
        """Seed gotham's demo actors into the profiles directory.

        user-profiles never auto-populates its tables, so without this the
        people-search in the share dialog returns nothing for gotham's actors.
        We hand each actor's name and its ``data:`` SVG profile picture to the
        seed hook; user-profiles owns the tables, decodes the picture and writes
        it with fill-missing semantics (so a demo user's own edits survive).
        """
        from datasette_user_profiles.hookspecs import ProfileSeed

        return [
            ProfileSeed(
                actor_id=actor_id,
                display_name=info["name"],
                photo_url=info.get("profile_picture_url"),
            )
            for actor_id, info in ACTORS.items()
        ]

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
