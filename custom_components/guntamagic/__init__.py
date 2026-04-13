"""The Guntamagic integration."""
from __future__ import annotations

import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_IP_ADDRESS, CONF_KEY
from .sensor import GuntamagicDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Guntamagic from a config entry."""

    # Verbindung testen BEVOR Plattformen geladen werden
    ip_address = entry.data[CONF_IP_ADDRESS]
    key = entry.data[CONF_KEY]
    session = async_get_clientsession(hass)
    timeout = aiohttp.ClientTimeout(total=10)

    try:
        async with session.get(
            f"http://{ip_address}/ext/daqdata.cgi?key={key}",
            timeout=timeout,
        ) as response:
            if response.status != 200:
                raise ConfigEntryNotReady(
                    f"Device at {ip_address} returned HTTP {response.status}"
                )
            data = await response.json()
            if not data:
                raise ConfigEntryNotReady(f"Device at {ip_address} returned no data")
    except ConfigEntryNotReady:
        raise
    except Exception as err:
        raise ConfigEntryNotReady(
            f"Could not connect to Guntamatic device at {ip_address}: {err}"
        ) from err

    hass.data.setdefault(DOMAIN, {})

    # Coordinator erstellen und für alle Plattformen bereitstellen
    coordinator = GuntamagicDataUpdateCoordinator(hass, entry)
    await coordinator.async_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded