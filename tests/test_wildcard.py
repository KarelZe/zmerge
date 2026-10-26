from collections.abc import Callable
from pathlib import Path

import pytest

from zmerge.config import Include, Section, load_site


def test_wildcard_include(make_project: Callable[..., Path]) -> None:
    make_project("apps/app1", {"nav": [{"Home": "index.md"}]})
    make_project("apps/app2", {"nav": [{"Home": "index.md"}]})

    umbrella = make_project("umbrella", {"nav": [{"Apps": "*include ../apps/*/zensical.toml"}]})

    site = load_site(umbrella)

    assert len(site.nav) == 1
    apps = site.nav[0]
    assert isinstance(apps, Section)
    assert isinstance(apps, Section)
    assert apps.title == "Apps"

    assert len(apps.items) == 2
    app1, app2 = apps.items

    assert isinstance(app1, Include)
    assert app1.title == "apps/app1"
    assert app1.project.id == "apps-app1"

    assert isinstance(app2, Include)
    assert app2.title == "apps/app2"
    assert app2.project.id == "apps-app2"


def test_wildcard_include_numeric(make_project: Callable[..., Path]) -> None:
    make_project("apps/app10", {"nav": [{"Home": "index.md"}]})
    make_project("apps/app2", {"nav": [{"Home": "index.md"}]})

    umbrella = make_project("umbrella", {"nav": [{"Apps": "*include -n ../apps/*/zensical.toml"}]})

    site = load_site(umbrella)
    apps = site.nav[0]
    assert isinstance(apps, Section)

    assert apps.items[0].title == "apps/app2"
    assert apps.items[1].title == "apps/app10"


def test_wildcard_include_reverse(make_project: Callable[..., Path]) -> None:
    make_project("apps/a", {"nav": [{"Home": "index.md"}]})
    make_project("apps/b", {"nav": [{"Home": "index.md"}]})

    umbrella = make_project("umbrella", {"nav": [{"Apps": "*include -r ../apps/*/zensical.toml"}]})

    site = load_site(umbrella)
    apps = site.nav[0]
    assert isinstance(apps, Section)

    assert apps.items[0].title == "apps/b"
    assert apps.items[1].title == "apps/a"


def test_wildcard_include_numeric_reverse(make_project: Callable[..., Path]) -> None:
    make_project("apps/app10", {"nav": [{"Home": "index.md"}]})
    make_project("apps/app2", {"nav": [{"Home": "index.md"}]})

    umbrella = make_project("umbrella", {"nav": [{"Apps": "*include -r -n ../apps/*/zensical.toml"}]})

    site = load_site(umbrella)
    apps = site.nav[0]
    assert isinstance(apps, Section)

    assert apps.items[0].title == "apps/app10"
    assert apps.items[1].title == "apps/app2"


def test_wildcard_include_flat(make_project: Callable[..., Path]) -> None:
    make_project("apps/a", {"nav": [{"Home": "index.md"}]})

    umbrella = make_project("umbrella", {"nav": ["*include ../apps/*/zensical.toml"]})

    site = load_site(umbrella)

    assert len(site.nav) == 1
    assert isinstance(site.nav[0], Include)
    assert site.nav[0].title == "apps/a"


def test_wildcard_include_no_matches(make_project: Callable[..., Path]) -> None:
    umbrella = make_project("umbrella", {"nav": [{"Apps": "*include ../apps/*/zensical.toml"}]})

    with pytest.raises(Exception, match="contains no"):
        load_site(umbrella)

    # assert len(site.nav) == 0
