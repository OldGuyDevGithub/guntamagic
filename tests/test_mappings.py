"""
Tests für die Guntamagic Integration.
Prüft dass alle name_keys in den Mapping-Dateien in allen Sprachdateien übersetzt sind.
Prüft außerdem die Select-Logik (Programm-Auswahl).
"""
import json
import os
import sys
import pytest

# Pfade relativ zur Testdatei
INTEGRATION_DIR = os.path.join(os.path.dirname(__file__), "..", "custom_components", "guntamagic")
TRANSLATIONS_DIR = os.path.join(INTEGRATION_DIR, "translations")

MAPPING_FILES = [
    "modbus_mapping_biostar.json",
    "modbus_mapping_bmk.json",
    "modbus_mapping_bmk_hybrid.json",
    "modbus_mapping_bmk_vario.json",
    "modbus_mapping_powerchip.json",
]

LANGUAGE_FILES = ["de.json", "en.json", "it.json", "fr.json"]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_all_name_keys():
    """Sammelt alle name_keys aus allen Mapping-Dateien."""
    keys = {}
    for mapping_file in MAPPING_FILES:
        path = os.path.join(INTEGRATION_DIR, mapping_file)
        mapping = load_json(path)
        for reg, details in mapping.items():
            key = details.get("name_key")
            if key:
                if key not in keys:
                    keys[key] = []
                keys[key].append(mapping_file)
    return keys


def get_translated_keys(lang_file):
    """Liest alle übersetzten Keys aus einer Sprachdatei."""
    path = os.path.join(TRANSLATIONS_DIR, lang_file)
    data = load_json(path)
    return set(data.get("entity", {}).get("sensor", {}).keys())


class TestMappingFiles:

    def test_all_mapping_files_exist(self):
        """Alle Mapping-Dateien müssen vorhanden sein."""
        for mapping_file in MAPPING_FILES:
            path = os.path.join(INTEGRATION_DIR, mapping_file)
            assert os.path.exists(path), f"Mapping-Datei fehlt: {mapping_file}"

    def test_all_language_files_exist(self):
        """Alle Sprachdateien müssen vorhanden sein."""
        for lang_file in LANGUAGE_FILES:
            path = os.path.join(TRANSLATIONS_DIR, lang_file)
            assert os.path.exists(path), f"Sprachdatei fehlt: {lang_file}"

    def test_mapping_files_valid_json(self):
        """Alle Mapping-Dateien müssen valides JSON sein."""
        for mapping_file in MAPPING_FILES:
            path = os.path.join(INTEGRATION_DIR, mapping_file)
            try:
                load_json(path)
            except json.JSONDecodeError as e:
                pytest.fail(f"Ungültiges JSON in {mapping_file}: {e}")

    def test_language_files_valid_json(self):
        """Alle Sprachdateien müssen valides JSON sein."""
        for lang_file in LANGUAGE_FILES:
            path = os.path.join(TRANSLATIONS_DIR, lang_file)
            try:
                load_json(path)
            except json.JSONDecodeError as e:
                pytest.fail(f"Ungültiges JSON in {lang_file}: {e}")

    def test_all_mappings_have_index(self):
        """Jeder Mapping-Eintrag muss ein 'index'-Feld haben."""
        for mapping_file in MAPPING_FILES:
            path = os.path.join(INTEGRATION_DIR, mapping_file)
            mapping = load_json(path)
            for reg, details in mapping.items():
                assert "index" in details, (
                    f"Fehlendes 'index'-Feld in {mapping_file}, Register {reg}"
                )

    def test_all_mappings_have_name_key(self):
        """Jeder Mapping-Eintrag muss ein 'name_key'-Feld haben."""
        for mapping_file in MAPPING_FILES:
            path = os.path.join(INTEGRATION_DIR, mapping_file)
            mapping = load_json(path)
            for reg, details in mapping.items():
                assert "name_key" in details, (
                    f"Fehlendes 'name_key'-Feld in {mapping_file}, Register {reg}"
                )

    def test_no_duplicate_indices_per_mapping(self):
        """Innerhalb einer Mapping-Datei darf kein Index doppelt vorkommen."""
        for mapping_file in MAPPING_FILES:
            path = os.path.join(INTEGRATION_DIR, mapping_file)
            mapping = load_json(path)
            indices = [details["index"] for details in mapping.values() if "index" in details]
            duplicates = [i for i in set(indices) if indices.count(i) > 1]
            assert not duplicates, (
                f"Doppelte Indices in {mapping_file}: {duplicates}"
            )

    @pytest.mark.parametrize("lang_file", LANGUAGE_FILES)
    def test_all_name_keys_translated(self, lang_file):
        """Alle name_keys müssen in jeder Sprachdatei übersetzt sein."""
        all_keys = get_all_name_keys()
        translated = get_translated_keys(lang_file)

        missing = {
            key: mappings
            for key, mappings in all_keys.items()
            if key not in translated
        }

        assert not missing, (
            f"Fehlende Übersetzungen in {lang_file}:\n" +
            "\n".join(f"  '{k}' (verwendet in: {', '.join(v)})" for k, v in sorted(missing.items()))
        )

    @pytest.mark.parametrize("lang_file", LANGUAGE_FILES)
    def test_no_empty_translations(self, lang_file):
        """Kein übersetzter Name darf leer sein."""
        path = os.path.join(TRANSLATIONS_DIR, lang_file)
        data = load_json(path)
        sensors = data.get("entity", {}).get("sensor", {})

        empty = [key for key, val in sensors.items() if not val.get("name", "").strip()]
        assert not empty, (
            f"Leere Übersetzungen in {lang_file}: {empty}"
        )


# ---------------------------------------------------------------------------
# Hilfsfunktionen, die select.py-Logik ohne HA-Import prüfen
# ---------------------------------------------------------------------------

# Direkt die Konstanten aus select.py importieren ohne homeassistant-Abhängigkeit
def _load_select_module():
    """Lädt select.py direkt per Dateipfad, ohne guntamagic/__init__.py auszuführen."""
    import types
    import importlib.util

    # Minimale Mocks für homeassistant-Module, die select.py direkt importiert
    for mod_name in [
        "homeassistant",
        "homeassistant.components",
        "homeassistant.components.select",
        "homeassistant.helpers",
        "homeassistant.helpers.aiohttp_client",
        "homeassistant.helpers.entity",
        "homeassistant.helpers.update_coordinator",
    ]:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)

    sys.modules["homeassistant.components.select"].SelectEntity = object
    sys.modules["homeassistant.helpers.entity"].DeviceInfo = dict
    sys.modules["homeassistant.helpers.aiohttp_client"].async_get_clientsession = lambda hass: None
    sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = object
    sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = Exception

    # aiohttp mock
    if "aiohttp" not in sys.modules:
        sys.modules["aiohttp"] = types.ModuleType("aiohttp")
        sys.modules["aiohttp"].ClientTimeout = lambda **kw: None

    # const.py direkt laden und als guntamagic.const registrieren
    const_path = os.path.join(INTEGRATION_DIR, "const.py")
    const_spec = importlib.util.spec_from_file_location("guntamagic.const", const_path)
    const_mod = importlib.util.module_from_spec(const_spec)
    const_spec.loader.exec_module(const_mod)
    sys.modules["guntamagic.const"] = const_mod

    # guntamagic.sensor: nur load_mapping wird benötigt
    sensor_stub = types.ModuleType("guntamagic.sensor")
    def load_mapping(path):
        import json
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    sensor_stub.load_mapping = load_mapping
    sensor_stub.GuntamagicDataUpdateCoordinator = object
    sys.modules["guntamagic.sensor"] = sensor_stub

    # Leeres guntamagic-Package-Stub (verhindert __init__.py-Ausführung)
    if "guntamagic" not in sys.modules:
        sys.modules["guntamagic"] = types.ModuleType("guntamagic")

    # select.py direkt laden
    select_path = os.path.join(INTEGRATION_DIR, "select.py")
    spec = importlib.util.spec_from_file_location("guntamagic.select", select_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["guntamagic.select"] = mod
    spec.loader.exec_module(mod)
    return mod


_SELECT = None


def _get_select():
    global _SELECT
    if _SELECT is None:
        _SELECT = _load_select_module()
    return _SELECT


class TestSelectConstants:
    """Prüft die Konstanten und Hilfsfunktionen des Select-Moduls."""

    def test_program_options_values(self):
        """Reglerprogramm-Werte lt. Dokumentation."""
        sel = _get_select()
        assert sel.PROGRAM_OPTIONS["off"]       == 0
        assert sel.PROGRAM_OPTIONS["normal"]    == 1
        assert sel.PROGRAM_OPTIONS["hot_water"] == 2
        assert sel.PROGRAM_OPTIONS["heating"]   == 3
        assert sel.PROGRAM_OPTIONS["setback"]   == 4
        assert sel.PROGRAM_OPTION_MANUAL["manual"] == 8

    def test_hc_program_options_values(self):
        """Heizkreisprogramm-Werte lt. Dokumentation."""
        sel = _get_select()
        assert sel.HC_PROGRAM_OPTIONS["off"]     == 0
        assert sel.HC_PROGRAM_OPTIONS["normal"]  == 1
        assert sel.HC_PROGRAM_OPTIONS["heating"] == 2
        assert sel.HC_PROGRAM_OPTIONS["setback"] == 3

    def test_hc_syn_format(self):
        """Heizkreis-Synonyme müssen das Format HK{n}01 haben."""
        sel = _get_select()
        for i in range(9):
            assert sel._HC_KEY_TO_SYN[f"program_hc{i}"] == f"HK{i}01"

    @pytest.mark.parametrize("api_val,expected", [
        ("AUS",         "off"),
        ("aus",         "off"),
        ("NORMAL",      "normal"),
        ("NRML",        "normal"),
        ("NORM",        "normal"),
        ("WARMWASSER",  "hot_water"),
        ("WW",          "hot_water"),
        ("WARM",        "hot_water"),
        ("HEIZEN",      "heating"),
        ("HEIZ",        "heating"),
        ("ABSENKEN",    "setback"),
        ("ABSE",        "setback"),
        ("HANDBETRIEB", "manual"),
        ("HAND",        "manual"),
        (None,          None),
        ("",            None),
        ("UNBEKANNT",   None),
    ])
    def test_api_value_to_option(self, api_val, expected):
        """_api_value_to_option muss API-Strings korrekt mappen."""
        sel = _get_select()
        assert sel._api_value_to_option(api_val) == expected

    def test_find_register_id(self):
        """_find_register_id findet den Register-Schlüssel anhand des name_key."""
        sel = _get_select()
        mapping = {
            "69": {"name_key": "program"},
            "70": {"name_key": "program_hc0"},
        }
        assert sel._find_register_id(mapping, "program")     == "69"
        assert sel._find_register_id(mapping, "program_hc0") == "70"
        assert sel._find_register_id(mapping, "missing")     is None


class TestSelectMappingIntegration:
    """Prüft ob Select-Entitäten für die richtigen Kesseltypen erzeugt würden."""

    def _get_name_keys(self, mapping_file: str) -> set[str]:
        path = os.path.join(INTEGRATION_DIR, mapping_file)
        mapping = load_json(path)
        return {v.get("name_key") for v in mapping.values()}

    @pytest.mark.parametrize("mapping_file", [
        "modbus_mapping_biostar.json",
        "modbus_mapping_powerchip.json",
    ])
    def test_program_select_exists(self, mapping_file):
        """Biostar und Powerchip haben 'program' → Reglerprogramm-Select."""
        assert "program" in self._get_name_keys(mapping_file), (
            f"{mapping_file} sollte 'program' enthalten"
        )

    @pytest.mark.parametrize("mapping_file", [
        "modbus_mapping_biostar.json",
        "modbus_mapping_powerchip.json",
    ])
    def test_handbetrieb_allowed(self, mapping_file):
        """Biostar und Powerchip unterstützen HANDBETRIEB."""
        sel = _get_select()
        assert mapping_file in sel.MAPPINGS_WITH_HANDBETRIEB

    @pytest.mark.parametrize("mapping_file", [
        "modbus_mapping_bmk.json",
        "modbus_mapping_bmk_hybrid.json",
        "modbus_mapping_bmk_vario.json",
    ])
    def test_handbetrieb_not_allowed(self, mapping_file):
        """BMK-Varianten unterstützen KEIN HANDBETRIEB."""
        sel = _get_select()
        assert mapping_file not in sel.MAPPINGS_WITH_HANDBETRIEB

    @pytest.mark.parametrize("mapping_file,expected_hc_count", [
        ("modbus_mapping_biostar.json",   9),  # program_hc0..8
        ("modbus_mapping_powerchip.json", 9),  # program_hc0..8
    ])
    def test_hc_program_selects_count(self, mapping_file, expected_hc_count):
        """Anzahl der Heizkreis-Selects stimmt mit dem Mapping überein."""
        name_keys = self._get_name_keys(mapping_file)
        hc_keys = [k for k in name_keys if k and k.startswith("program_hc")]
        assert len(hc_keys) == expected_hc_count, (
            f"{mapping_file}: erwartet {expected_hc_count} HK-Selects, "
            f"gefunden {len(hc_keys)}: {hc_keys}"
        )


class TestSelectTranslations:
    """Prüft die Übersetzungen der Select-Entitäten."""

    REQUIRED_PROGRAM_STATES = {"off", "normal", "hot_water", "heating", "setback", "manual"}
    REQUIRED_HC_STATES = {"off", "normal", "heating", "setback"}

    @pytest.mark.parametrize("lang_file", LANGUAGE_FILES)
    def test_select_section_exists(self, lang_file):
        """Jede Sprachdatei muss einen entity.select-Abschnitt haben."""
        path = os.path.join(TRANSLATIONS_DIR, lang_file)
        data = load_json(path)
        assert "select" in data.get("entity", {}), (
            f"Fehlender 'entity.select'-Abschnitt in {lang_file}"
        )

    @pytest.mark.parametrize("lang_file", LANGUAGE_FILES)
    def test_program_select_translation(self, lang_file):
        """program_select muss Name und alle States übersetzen."""
        path = os.path.join(TRANSLATIONS_DIR, lang_file)
        data = load_json(path)
        select = data["entity"]["select"]
        assert "program_select" in select, (
            f"'program_select' fehlt in {lang_file}"
        )
        entry = select["program_select"]
        assert entry.get("name", "").strip(), f"Leerer Name in {lang_file} program_select"
        states = set(entry.get("state", {}).keys())
        assert self.REQUIRED_PROGRAM_STATES == states, (
            f"{lang_file} program_select: erwartet {self.REQUIRED_PROGRAM_STATES}, "
            f"gefunden {states}"
        )

    @pytest.mark.parametrize("lang_file", LANGUAGE_FILES)
    def test_program_hc_select_translation(self, lang_file):
        """program_hc_select muss Name und alle States übersetzen."""
        path = os.path.join(TRANSLATIONS_DIR, lang_file)
        data = load_json(path)
        select = data["entity"]["select"]
        assert "program_hc_select" in select, (
            f"'program_hc_select' fehlt in {lang_file}"
        )
        entry = select["program_hc_select"]
        assert entry.get("name", "").strip(), (
            f"Leerer Name in {lang_file} program_hc_select"
        )
        states = set(entry.get("state", {}).keys())
        assert self.REQUIRED_HC_STATES == states, (
            f"{lang_file} program_hc_select: erwartet {self.REQUIRED_HC_STATES}, "
            f"gefunden {states}"
        )

    @pytest.mark.parametrize("lang_file", LANGUAGE_FILES)
    def test_select_state_values_not_empty(self, lang_file):
        """Kein State-Label darf leer sein."""
        path = os.path.join(TRANSLATIONS_DIR, lang_file)
        data = load_json(path)
        selects = data.get("entity", {}).get("select", {})
        for sel_key, sel_val in selects.items():
            for state_key, label in sel_val.get("state", {}).items():
                assert label.strip(), (
                    f"{lang_file}: leeres Label für {sel_key}.state.{state_key}"
                )