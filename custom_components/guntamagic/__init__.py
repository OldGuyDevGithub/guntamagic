"""Guntamagic Integration."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Guntamagic from a config entry."""
    _LOGGER.debug("Guntamagic async_setup_entry aufgerufen.")
    hass.data.setdefault("guntamagic", {})
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove a config entry."""
    _LOGGER.debug("Guntamagic async_unload_entry aufgerufen.")
    return True

