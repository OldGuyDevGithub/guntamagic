import os
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectOptionDict

from .const import DOMAIN, CONF_NAME, CONF_IP_ADDRESS, CONF_KEY, CONF_MAPPING, CONF_MAPPING_OPTIONS

_LOGGER = logging.getLogger(__name__)


def _build_mapping_options() -> list[SelectOptionDict]:
    """Scannt das Integrationsverzeichnis nach Mapping-Dateien.
    
    Wird einmalig beim Modul-Import aufgerufen (außerhalb des Event Loops),
    damit kein blocking I/O im async-Kontext stattfindet.
    """
    try:
        integration_dir = os.path.dirname(__file__)
        mapping_files = [
            f for f in os.listdir(integration_dir)
            if f.startswith("modbus_mapping_") and f.endswith(".json")
        ]

        options = []
        for f in mapping_files:
            label = CONF_MAPPING_OPTIONS.get(
                f,
                f.replace("modbus_mapping_", "").replace(".json", "").replace("_", " ").title()
            )
            options.append(SelectOptionDict(value=f, label=label))

        return options

    except Exception as e:  # noqa: BLE001
        _LOGGER.error("Fehler beim Laden der Mapping-Dateien: %s", e)
        return []


# Einmalig beim Import laden – Modul-Import läuft außerhalb des Event Loops,
# daher ist os.listdir() hier problemlos.
_MAPPING_OPTIONS: list[SelectOptionDict] = _build_mapping_options()


class GuntamagicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Guntamagic."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if not _MAPPING_OPTIONS:
            return self.async_abort(reason="no_mapping_files_found")

        if user_input is not None:
            if not user_input.get(CONF_MAPPING):
                errors[CONF_MAPPING] = "no_mapping_selected"
            else:
                mapping_file = user_input[CONF_MAPPING]
                mapping_path = os.path.join(os.path.dirname(__file__), mapping_file)

                if not os.path.exists(mapping_path):
                    errors[CONF_MAPPING] = "invalid_mapping"
                    _LOGGER.error("Mapping-Datei nicht gefunden: %s", mapping_path)
                else:
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data={
                            CONF_NAME: user_input[CONF_NAME],
                            CONF_IP_ADDRESS: user_input[CONF_IP_ADDRESS],
                            CONF_KEY: user_input[CONF_KEY],
                            CONF_MAPPING: user_input[CONF_MAPPING],
                        },
                    )

        schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_IP_ADDRESS): str,
            vol.Required(CONF_KEY): str,
            vol.Required(CONF_MAPPING): SelectSelector(
                SelectSelectorConfig(
                    options=_MAPPING_OPTIONS,
                    mode="dropdown",
                )
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GuntamagicOptionsFlowHandler(config_entry)


class GuntamagicOptionsFlowHandler(config_entries.OptionsFlow):
    """Optionen nachträglich ändern."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        errors = {}

        if user_input is not None:
            mapping_file = user_input[CONF_MAPPING]
            mapping_path = os.path.join(os.path.dirname(__file__), mapping_file)

            if not os.path.exists(mapping_path):
                errors[CONF_MAPPING] = "invalid_mapping"
                _LOGGER.error("Mapping-Datei nicht gefunden: %s", mapping_path)
            else:
                return self.async_create_entry(
                    title="",
                    data={CONF_MAPPING: user_input[CONF_MAPPING]},
                )

        current_mapping = self.config_entry.data.get(CONF_MAPPING)

        schema = vol.Schema({
            vol.Required(CONF_MAPPING, default=current_mapping): SelectSelector(
                SelectSelectorConfig(
                    options=_MAPPING_OPTIONS,
                    mode="dropdown",
                )
            ),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )