"""Guntamagic select platform — Reglerprogramm & Heizkreisprogramme."""
from __future__ import annotations

import logging

import aiohttp

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_IP_ADDRESS, CONF_KEY, CONF_MAPPING, CONF_NAME
from .sensor import load_mapping

_LOGGER = logging.getLogger(__name__)

# Mapping-Dateien, die HANDBETRIEB unterstützen (lt. Dok.: PC/BC/BS/PRO)
MAPPINGS_WITH_HANDBETRIEB: set[str] = {
    "modbus_mapping_biostar.json",
    "modbus_mapping_powerchip.json",
}

# Reglerprogramm-Optionen: option_key → API-Wert
PROGRAM_OPTIONS: dict[str, int] = {
    "off":       0,
    "normal":    1,
    "hot_water": 2,
    "heating":   3,
    "setback":   4,
}
PROGRAM_OPTION_MANUAL: dict[str, int] = {"manual": 8}

# Heizkreisprogramm-Optionen
HC_PROGRAM_OPTIONS: dict[str, int] = {
    "off":     0,
    "normal":  1,
    "heating": 2,
    "setback": 3,
}

# Rückwärts-Mapping: API-String (lowercase) → option_key
# Die API gibt bei string-Typen Kurzformen zurück (max. 4 Zeichen via Modbus),
# über HTTP können auch Langformen kommen.
_API_STRING_MAP: dict[str, str] = {
    "aus":        "off",
    "normal":     "normal",
    "nrml":       "normal",
    "norm":       "normal",
    "warmwasser": "hot_water",
    "warm":       "hot_water",
    "ww":         "hot_water",
    "heizen":     "heating",
    "heiz":       "heating",
    "absenken":   "setback",
    "abse":       "setback",
    "abs":        "setback",
    "handbetrieb": "manual",
    "hand":        "manual",
}

# program_hc{n} → HTTP-Synonym HK{n}01
_HC_KEY_TO_SYN: dict[str, str] = {
    f"program_hc{i}": f"HK{i}01" for i in range(9)
}


def _api_value_to_option(api_value: object) -> str | None:
    """Konvertiert einen API-Rückgabewert (String) in einen option_key."""
    if api_value is None:
        return None
    lower = str(api_value).lower().strip()
    if lower in _API_STRING_MAP:
        return _API_STRING_MAP[lower]
    # Präfix-Matching als Fallback
    for prefix, key in _API_STRING_MAP.items():
        if lower.startswith(prefix):
            return key
    return None


def _find_register_id(mapping: dict, name_key: str) -> str | None:
    """Gibt die Register-ID (String) für einen name_key zurück."""
    for reg_id, details in mapping.items():
        if details.get("name_key") == name_key:
            return reg_id
    return None


async def async_setup_entry(hass, entry, async_add_entities):
    """Richtet Guntamagic Select-Entitäten ein."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entity_name = entry.data.get(CONF_NAME, "Guntamagic")
    mapping_file_name = entry.data.get(CONF_MAPPING, "")

    mapping = await load_mapping(mapping_file_name)
    if not mapping:
        _LOGGER.error("Mapping konnte nicht geladen werden: %s", mapping_file_name)
        return

    has_handbetrieb = mapping_file_name in MAPPINGS_WITH_HANDBETRIEB
    mapping_name_keys = {details.get("name_key") for details in mapping.values()}
    entities: list[GuntamagicProgramSelect] = []

    # Reglerprogramm – vorhanden, wenn "program" im Mapping ist
    if "program" in mapping_name_keys:
        options = dict(PROGRAM_OPTIONS)
        if has_handbetrieb:
            options.update(PROGRAM_OPTION_MANUAL)
        register_id = _find_register_id(mapping, "program")
        entities.append(
            GuntamagicProgramSelect(
                coordinator=coordinator,
                entry=entry,
                entity_name=entity_name,
                translation_key="program_select",
                display_name=None,          # Name kommt aus Translation
                options=options,
                syn="PR001",
                register_id=register_id,
            )
        )

    # Heizkreisprogramme – eines pro vorhandenem program_hc{n}
    for hc_key, syn in _HC_KEY_TO_SYN.items():
        if hc_key in mapping_name_keys:
            hc_index = int(hc_key.replace("program_hc", ""))
            register_id = _find_register_id(mapping, hc_key)
            entities.append(
                GuntamagicProgramSelect(
                    coordinator=coordinator,
                    entry=entry,
                    entity_name=entity_name,
                    translation_key="program_hc_select",
                    display_name=f"Programm HK {hc_index}",
                    options=dict(HC_PROGRAM_OPTIONS),
                    syn=syn,
                    register_id=register_id,
                )
            )

    async_add_entities(entities)


class GuntamagicProgramSelect(SelectEntity):
    """Select-Entität für Reglerprogramm oder Heizkreisprogramm."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        entry,
        entity_name: str,
        translation_key: str,
        display_name: str | None,
        options: dict[str, int],
        syn: str,
        register_id: str | None,
    ) -> None:
        self.coordinator = coordinator
        self._entry = entry
        self._entity_name = entity_name
        self._options = options          # {option_key: api_value}
        self._syn = syn
        self._register_id = register_id

        self._attr_translation_key = translation_key
        # Expliziter Name für nummerierte Entitäten (HK 0..8)
        if display_name is not None:
            self._attr_name = display_name

        self._attr_unique_id = (
            f"{DOMAIN}_{entity_name}_{syn}_select"
        )
        self._attr_options = list(options.keys())

    # ------------------------------------------------------------------
    # HA lifecycle
    # ------------------------------------------------------------------

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def should_poll(self) -> bool:
        return False

    # ------------------------------------------------------------------
    # Aktuellen Wert aus Koordinator lesen
    # ------------------------------------------------------------------

    @property
    def current_option(self) -> str | None:
        if not self.coordinator.data or self._register_id is None:
            return None
        raw = self.coordinator.data.get(self._register_id)
        option = _api_value_to_option(raw)
        if option is not None and option in self._options:
            return option
        return None

    # ------------------------------------------------------------------
    # Wert setzen
    # ------------------------------------------------------------------

    async def async_select_option(self, option: str) -> None:
        """Sendet das gewählte Programm an den Kessel."""
        if option not in self._options:
            _LOGGER.error(
                "Ungültige Option '%s' für %s – erlaubt: %s",
                option, self._syn, list(self._options.keys()),
            )
            return

        api_value = self._options[option]
        ip = self._entry.data[CONF_IP_ADDRESS]
        key = self._entry.data[CONF_KEY]
        url = (
            f"http://{ip}/ext/parset.cgi"
            f"?syn={self._syn}&value={api_value}&key={key}"
        )

        session = async_get_clientsession(self.coordinator.hass)
        timeout = aiohttp.ClientTimeout(total=10)
        try:
            async with session.get(url, timeout=timeout) as resp:
                if resp.status != 200:
                    _LOGGER.error(
                        "Fehler beim Setzen von %s=%s: HTTP %d",
                        self._syn, option, resp.status,
                    )
                    return
                result = await resp.json(content_type=None)
        except Exception as exc:
            _LOGGER.error(
                "Verbindungsfehler beim Setzen von %s=%s: %s",
                self._syn, option, exc,
            )
            return

        if "ack" in result:
            _LOGGER.debug(
                "%s=%s gesetzt: %s", self._syn, option, result["ack"]
            )
        elif "err" in result:
            _LOGGER.error(
                "Gerät meldete Fehler beim Setzen von %s=%s: %s",
                self._syn, option, result["err"],
            )
            return

        # Coordinator aktualisieren, damit current_option sofort stimmt
        await self.coordinator.async_request_refresh()

    # ------------------------------------------------------------------
    # Geräteinformation
    # ------------------------------------------------------------------

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entity_name,
            manufacturer="Guntamatic",
            model=self._entry.data.get(CONF_MAPPING, "Unbekannt"),
            sw_version="1.0",
        )
