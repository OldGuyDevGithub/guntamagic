"""
Tests für die Guntamagic Integration.
Prüft dass alle name_keys in den Mapping-Dateien in allen Sprachdateien übersetzt sind.
"""
import json
import os
import pytest

# Pfade relativ zur Testdatei
INTEGRATION_DIR = os.path.join(os.path.dirname(__file__), "..", "custom_components", "guntamagic")
TRANSLATIONS_DIR = os.path.join(INTEGRATION_DIR, "translations")

MAPPING_FILES = [
    "modbus_mapping_biostar.json",
    "modbus_mapping_bmk.json",
    "modbus_mapping_bmk_hybrid.json",
    "modbus_mapping_bmk_vario.json",
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