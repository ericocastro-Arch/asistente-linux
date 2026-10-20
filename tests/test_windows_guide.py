"""Pruebas de la guía de migración sin cambios en el sistema."""

from src.gui.windows_guide import WINDOWS_ITEMS, search_windows_guide


def test_guide_has_unique_items_and_expected_kinds():
    results = search_windows_guide()

    assert len(results) == len(WINDOWS_ITEMS)
    assert len({item["id"] for item in results}) == len(results)
    assert {item["kind"] for item in results} == {"feature", "app"}
    assert all("keywords" not in item for item in results)


def test_natural_language_query_finds_task_manager():
    results = search_windows_guide("¿Dónde está el Administrador de tareas?")

    assert [item["id"] for item in results] == ["task-manager"]
    assert "Monitor del sistema" in results[0]["linux"]


def test_accent_insensitive_search_and_kind_filter():
    assert [item["id"] for item in search_windows_guide("calculo", "app")] == ["excel"]
    assert not search_windows_guide("calculo", "feature")
    assert [item["id"] for item in search_windows_guide("PowerShell", "feature")] == ["powershell"]


def test_alternatives_are_searches_not_install_commands():
    photoshop = search_windows_guide("Photoshop", "app")[0]

    assert photoshop["id"] == "photoshop"
    assert photoshop["searches"] == [
        {"name": "GIMP", "query": "gimp"},
        {"name": "Krita", "query": "krita"},
    ]
    assert "No son reemplazos idénticos" in photoshop["note"]


def test_unknown_query_returns_empty_list():
    assert search_windows_guide("programa imposible xyz") == []


def test_invalid_kind_uses_all_results():
    assert search_windows_guide(kind="unexpected") == search_windows_guide()
