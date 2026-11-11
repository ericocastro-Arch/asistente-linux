"""Planificación local de migración. Nunca ejecuta el inventario recibido."""
import re
import json
import os
import tempfile
from pathlib import Path
from difflib import SequenceMatcher

from src.gui.windows_guide import search_windows_guide, _fold, _item
from src.gui.artcraft_catalog import artcraft_catalog

ALIASES = {
    'firefox': ['firefox', 'mozilla.firefox'], 'obs': ['obs', 'obs studio', 'obsproject.obsstudio'],
    'vlc': ['vlc', 'videolan.vlc'], 'putty': ['putty'], 'onenote': ['onenote'], 'sharex': ['sharex'],
    'office': ['office', 'microsoft 365'], 'word': ['word'], 'excel': ['excel'],
    'powerpoint': ['powerpoint'], 'photoshop': ['photoshop'], 'vscode': ['vscode', 'visual studio code', 'microsoft.visualstudiocode'],
    'chrome': ['chrome', 'google.chrome'], 'steam': ['steam', 'valve.steam'],
    'notepad-plus': ['notepad++', 'notepadplusplus.notepadplusplus'],
}


def migration_catalog():
    items = search_windows_guide(kind='app')
    items.extend([
        _item('vlc', 'app', 'VLC', 'VLC para Linux', 'Prueba los formatos de video y audio que utilizas.', (('VLC', 'vlc'),)),
        _item('firefox', 'app', 'Mozilla Firefox', 'Firefox para Linux', 'Importa marcadores desde el navegador o usa su sincronización.', (('Firefox', 'firefox'),)),
        _item('obs', 'app', 'OBS Studio', 'OBS Studio para Linux', 'Revisa fuentes de captura, dispositivos y complementos.', (('OBS Studio', 'obs-studio'),)),
        _item('putty', 'app', 'PuTTY', 'Cliente SSH de Linux', 'Puedes usar SSH desde la terminal; importa tus claves con cuidado y revisa sus permisos.', (('OpenSSH', 'openssh'),)),
        _item('onenote', 'app', 'Microsoft OneNote', 'Joplin o la versión web de OneNote', 'Comprueba cómo exportar tus notas y adjuntos antes de migrar.', (('Joplin', 'joplin'),)),
        _item('sharex', 'app', 'ShareX', 'Capturas del escritorio o Flameshot', 'Las funciones y permisos de captura dependen de tu escritorio.', (('Flameshot', 'flameshot'),)),
    ])
    for item in items:
        item['route'] = 'native' if item['id'] in {'chrome', 'vscode', 'vlc', 'firefox', 'obs'} else 'compatibility' if item['id'] == 'steam' else 'alternative'
        item['aliases'] = ALIASES.get(item['id'], [item['windows']])
    return items + artcraft_catalog()


def build_migration_plan(inventory):
    if not isinstance(inventory, str) or len(inventory) > 20000:
        raise ValueError('Introduce hasta 20 000 caracteres, con un programa por línea.')
    catalog = migration_catalog()
    entries, seen = [], set()
    for raw in re.split(r'[\n,;]+', inventory):
        name = raw.strip().lstrip('-• ').strip()
        if not name or re.fullmatch(r'[-\s]+', name):
            continue
        # winget list: columnas separadas por dos o más espacios.
        name = re.split(r'\s{2,}|\t', name)[0][:160]
        key = _fold(name)
        if key in seen or key in {'name', 'nombre'}:
            continue
        seen.add(key)
        if len(entries) >= 100:
            raise ValueError('El plan admite hasta 100 programas por vez.')
        matches = []
        for item in catalog:
            aliases = [_fold(x) for x in [item['windows'], *item['aliases']]]
            score = max(1.0 if key == alias else .96 if re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', key) else SequenceMatcher(None, key, alias).ratio() for alias in aliases)
            matches.append((score, item))
        matches.sort(key=lambda pair: pair[0], reverse=True)
        score, match = matches[0]
        exact = score >= .96
        entries.append({'input': name, 'match': match if exact else None,
                        'suggestion': match if .78 <= score < .96 else None,
                        'route': match['route'] if exact else 'review'})
    return {'entries': entries, 'total': len(entries)}


def normalize_saved_plan(payload):
    if not isinstance(payload, dict):
        raise ValueError('Plan inválido.')
    inventory = payload.get('inventory', '')
    rows = payload.get('entries', [])
    if not isinstance(inventory, str) or len(inventory) > 20000 or not isinstance(rows, list) or len(rows) > 100:
        raise ValueError('El plan admite 100 aplicaciones y 20 000 caracteres.')
    catalog = {item['id']: item for item in migration_catalog()}
    entries = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('input'), str):
            raise ValueError('Entrada de plan inválida.')
        match = row.get('match')
        match = catalog.get(match.get('id')) if isinstance(match, dict) else None
        entries.append({'input': row['input'][:160], 'match': match,
                        'route': match['route'] if match else 'review', 'tested': row.get('tested') is True})
    checks = payload.get('checks', {})
    if not isinstance(checks, dict):
        checks = {}
    return {'inventory': inventory, 'entries': entries,
            'checks': {key: checks.get(key) is True for key in ('backup', 'files', 'browser', 'desktop')}}


def plan_path():
    return Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'linuxmate' / 'migration-plan.json'


def load_plan():
    path = plan_path()
    if not path.exists():
        return normalize_saved_plan({})
    if path.stat().st_size > 500000:
        raise ValueError('El plan guardado supera el tamaño permitido.')
    return normalize_saved_plan(json.loads(path.read_text(encoding='utf-8')))


def save_plan(payload):
    plan = normalize_saved_plan(payload)
    path = plan_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(plan, handle, ensure_ascii=False)
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
