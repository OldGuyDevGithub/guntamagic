"""Guntamagic Integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Guntamagic from a config entry."""
    _LOGGER.debug("async_setup_entry in __init__.py aufgerufen.")
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    try:
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    except Exception as e:
        _LOGGER.error(f"Fehler beim Weiterleiten der Einrichtung für Sensoren: {e}")
        return False  # Falls ein Fehler auftritt, wird die Einrichtung abgebrochen

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove a config entry."""
    _LOGGER.debug("async_unload_entry in __init__.py aufgerufen")

    try:
        unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
        if unload_ok:
            hass.data[DOMAIN].pop(entry.entry_id)
            return True
        else:
            _LOGGER.warning("Entladen der Guntamagic-Sensoren fehlgeschlagen.")
            return False
    except Exception as e:
        _LOGGER.error(f"Fehler beim Entladen der Integration: {e}")
        return False
