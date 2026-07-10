"""Config flow for the Akahu integration."""

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_APP_TOKEN, CONF_USER_TOKEN, DOMAIN, LOGGER
from .pyakahu import AkahuAuthError, AkahuClient, AkahuConnectionError

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_APP_TOKEN): str,
        vol.Required(CONF_USER_TOKEN): str,
    }
)


class AkahuConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Akahu config flow."""

    async def _async_validate(
        self, data: Mapping[str, Any]
    ) -> tuple[str | None, str | None, dict[str, str]]:
        """Validate the tokens by calling /me. Returns (user_id, name, errors)."""
        client = AkahuClient(
            session=async_get_clientsession(self.hass),
            app_token=data[CONF_APP_TOKEN],
            user_token=data[CONF_USER_TOKEN],
        )
        errors: dict[str, str] = {}
        try:
            user = await client.async_get_user()
        except AkahuAuthError:
            errors["base"] = "invalid_auth"
        except AkahuConnectionError:
            errors["base"] = "cannot_connect"
        except Exception:  # noqa: BLE001
            LOGGER.exception("Unexpected Akahu API error")
            errors["base"] = "unknown"
        else:
            return user.id, user.name, errors
        return None, None, errors

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_id, name, errors = await self._async_validate(user_input)
            if user_id is not None:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name or "Akahu",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauthentication."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            user_id, _, errors = await self._async_validate(user_input)
            if user_id is not None:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates=user_input,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()
        if user_input is not None:
            user_id, _, errors = await self._async_validate(user_input)
            if user_id is not None:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates=user_input,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
