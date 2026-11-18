"""Every list_all/get_all pages through its listing the same way, on Exa and AsyncExa.

Each listing is driven through two stubbed pages. The test pins the items
returned and the arguments each page fetch got: the first cursor (agent
monitors resume from the caller's ``cursor``, every other listing starts at the
first page), the next cursor, and an extra ``cursor`` query that is sent with
the first page only.
"""

from types import SimpleNamespace

import pytest

from exa_py import AsyncExa, Exa

BETAS = {"betas": ["test-beta"]}

# (name, path to the client, list_all, get_all, path to the page fetch from the client,
#  leading arguments, extra keyword arguments, resumes from the caller's cursor)
LISTINGS = [
    ("agent.runs", "agent.runs", "list_all", "get_all", "list", (), {}, False),
    ("beta.agent.runs", "beta.agent.runs", "list_all", "get_all", "list", (), BETAS, False),
    ("beta.agent.monitors", "beta.agent.monitors", "list_all", "get_all", "list", (), BETAS, True),
    ("entities", "beta.agent.monitors.entities", "list_all", "get_all", "list", ("am_1",), BETAS, True),
    ("changes", "beta.agent.monitors.changes", "list_all", "get_all", "list", ("am_1",), BETAS, True),
    ("monitors", "monitors", "list_all", "get_all", "list", (), {}, False),
    ("monitors.runs", "monitors.runs", "list_all", "get_all", "list", ("sm_1",), {}, False),
    ("websets", "websets", "list_all", "get_all", "list", (), {}, False),
    ("websets.events", "websets.events", "list_all", "get_all", "list", (), {}, False),
    ("websets.imports", "websets.imports", "list_all", "get_all", "list", (), {}, False),
    ("websets.items", "websets.items", "list_all", "get_all", "list", ("ws_1",), {}, False),
    ("websets.monitors", "websets.monitors", "list_all", "get_all", "list", (), {}, False),
    ("websets.webhooks", "websets.webhooks", "list_all", "get_all", "list", (), {}, False),
    (
        "webhook attempts",
        "websets.webhooks",
        "list_all_attempts",
        "get_all_attempts",
        "attempts.list",
        ("wh_1",),
        {},
        False,
    ),
]

PAGES = [
    SimpleNamespace(data=["a", "b"], has_more=True, next_cursor="c1"),
    SimpleNamespace(data=["c"], has_more=False, next_cursor=None),
]


def _resolve(root, path):
    for part in path.split("."):
        root = getattr(root, part)
    return root


def _stub_pages(client, fetch_path, *, is_async):
    """Replace the page fetch with two pages; return the recorded calls."""
    owner_path, _, method = fetch_path.rpartition(".")
    owner = _resolve(client, owner_path) if owner_path else client
    calls = []

    def record(args, kwargs):
        calls.append((args, dict(kwargs)))
        return PAGES[len(calls) - 1]

    if is_async:

        async def fetch(*args, **kwargs):
            return record(args, kwargs)

    else:

        def fetch(*args, **kwargs):
            return record(args, kwargs)

    setattr(owner, method, fetch)
    return calls


def _assert_calls(calls, lead, resumes):
    assert [args for args, _ in calls] == [lead, lead]
    first, second = (kwargs for _, kwargs in calls)
    assert first["cursor"] == ("c0" if resumes else None)
    assert second["cursor"] == "c1"
    assert first["limit"] == second["limit"] == 2
    assert first["extra_query"] == {"cursor": "x0", "debug": "1"}
    assert second["extra_query"] == {"debug": "1"}


def _list_all_kwargs(extra_kwargs, resumes):
    kwargs = {**extra_kwargs, "limit": 2, "extra_query": {"cursor": "x0", "debug": "1"}}
    # Only agent monitors take a starting cursor.
    if resumes:
        kwargs["cursor"] = "c0"
    return kwargs


IDS = [listing[0] for listing in LISTINGS]


@pytest.mark.parametrize(
    ("name", "path", "list_all", "get_all", "fetch", "lead", "extra", "resumes"),
    LISTINGS,
    ids=IDS,
)
def test_sync_list_all_and_get_all(name, path, list_all, get_all, fetch, lead, extra, resumes):
    client = _resolve(Exa("test-key"), path)
    kwargs = _list_all_kwargs(extra, resumes)

    calls = _stub_pages(client, fetch, is_async=False)
    assert list(getattr(client, list_all)(*lead, **kwargs)) == ["a", "b", "c"]
    _assert_calls(calls, lead, resumes)

    calls = _stub_pages(client, fetch, is_async=False)
    assert getattr(client, get_all)(*lead, **kwargs) == ["a", "b", "c"]
    _assert_calls(calls, lead, resumes)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "path", "list_all", "get_all", "fetch", "lead", "extra", "resumes"),
    LISTINGS,
    ids=IDS,
)
async def test_async_list_all_and_get_all(
    name, path, list_all, get_all, fetch, lead, extra, resumes
):
    client = _resolve(AsyncExa("test-key"), path)
    kwargs = _list_all_kwargs(extra, resumes)

    calls = _stub_pages(client, fetch, is_async=True)
    assert [item async for item in getattr(client, list_all)(*lead, **kwargs)] == ["a", "b", "c"]
    _assert_calls(calls, lead, resumes)

    calls = _stub_pages(client, fetch, is_async=True)
    assert await getattr(client, get_all)(*lead, **kwargs) == ["a", "b", "c"]
    _assert_calls(calls, lead, resumes)


def test_list_all_ignores_values_sent_to_it():
    client = Exa("test-key").websets
    client.list = lambda **kwargs: PAGES[1]
    listing = client.list_all()

    assert next(listing) == "c"
    with pytest.raises(StopIteration):
        listing.send("ignored")


@pytest.mark.parametrize(
    ("page", "expected_calls"),
    [
        (SimpleNamespace(data=["a"], has_more=True, next_cursor=None), 1),
        (SimpleNamespace(data=[], has_more=False, next_cursor=None), 1),
    ],
    ids=["more without a cursor", "empty first page"],
)
def test_list_all_stops_after_the_last_page(page, expected_calls):
    client = Exa("test-key").websets
    calls = []

    def fetch(**kwargs):
        calls.append(kwargs)
        return page

    client.list = fetch
    assert client.get_all() == page.data
    assert len(calls) == expected_calls
