from src.gui.artcraft_catalog import artcraft_catalog
from src.gui.migration import build_migration_plan, normalize_saved_plan


def test_catalog_has_official_sources_and_no_unverified_snap_install():
    items = artcraft_catalog()
    assert len(items) == 17
    assert len({item['id'] for item in items}) == 17
    for item in items:
        assert item['website'].startswith('https://getartcraft.com/apps/')
        assert item['icon'].startswith('https://getartcraft.com/images/apps/')
        assert item['maturity'] in {'Alpha temprana', 'En desarrollo'}
        snap = next(method for method in item['methods'] if method['id'] == 'snap')
        assert snap['available'] is False
        assert 'command' not in snap
        assert {m['id'] for m in item['methods'] if m['available']} == {'flatpak','deb','rpm','appimage'}


def test_plan_recognizes_both_names_without_replacing_existing_alternatives():
    entries = build_migration_plan('PhotoCraft\nPhotoshop\nAutoCAD\nWordCraft')['entries']
    assert [entry['match']['id'] for entry in entries] == ['artcraft-photocraft','photoshop','artcraft-cadcraft','artcraft-wordcraft']


def test_saved_artcraft_plan_replaces_untrusted_urls_and_commands():
    saved = normalize_saved_plan({'entries': [{
        'input': 'PhotoCraft', 'match': {'id':'artcraft-photocraft', 'website':'https://evil.example',
                                       'methods':[{'command':'evil'}]}, 'tested':True
    }]})
    item = saved['entries'][0]['match']
    assert item['website'] == 'https://getartcraft.com/apps/photocraft'
    assert item['methods'][0]['command'].startswith('flatpak install --user')
    assert saved['entries'][0]['tested'] is True
