from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from .api import BptAuxFeature, BptDeviceMetadata, BptDoorConfig, CameConnectClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _build_bpt_device_info(device_id: str, metadata: BptDeviceMetadata | None) -> DeviceInfo:
    bpt_device_id = f"{device_id}_bpt"
    return DeviceInfo(
        identifiers={(DOMAIN, bpt_device_id)},
        via_device=(DOMAIN, device_id),
        name=metadata.device_name if metadata else "BPT/X1 Intercom",
        manufacturer=metadata.manufacturer if metadata else "CAME",
        model=metadata.model if metadata else "CAME BPT/X1",
        configuration_url="https://app.cameconnect.net/",
    )


class _CameBptButtonBase(ButtonEntity):
    def __init__(
        self,
        client: CameConnectClient,
        device_id: str,
        options: dict,
        metadata: BptDeviceMetadata | None = None,
    ) -> None:
        self._client = client
        self._device_id = str(device_id)
        self._bpt_device_id = f"{self._device_id}_bpt"
        self._options = options
        self._config: BptDoorConfig | None = None
        self._metadata = metadata
        self._attr_device_info = _build_bpt_device_info(self._device_id, metadata)
        self._last_run: str | None = None
        self._last_xipregister_status: str | None = None
        self._last_register_status: str | None = None
        self._last_message_status: str | None = None
        self._last_error: str | None = None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            "last_run": self._last_run,
            "last_xipregister_status": self._last_xipregister_status,
            "last_register_status": self._last_register_status,
            "last_message_status": self._last_message_status,
            "last_error": self._last_error,
            "sip_user": self._config.sip_user if self._config else None,
            "src_addr": self._config.src_addr if self._config else None,
            "target_user": self._config.target_user if self._config else None,
            "panel_addr": self._config.panel_addr if self._config else None,
            "subject_label": self._config.subject_label if self._config else None,
            "bpt_device_name": self._metadata.device_name if self._metadata else None,
            "bpt_unit_name": self._metadata.unit_name if self._metadata else None,
            "bpt_entry_panel_name": self._metadata.entry_panel_name if self._metadata else None,
            "bpt_open_door_label": self._metadata.open_door_label if self._metadata else None,
        }

    async def _resolve_config(self) -> BptDoorConfig:
        self._config = await self._client.async_resolve_bpt_door_config(self._device_id, self._options)
        return self._config

    def _record_success(self, result: dict[str, object]) -> None:
        self._last_register_status = str(result.get("register_status"))
        self._last_message_status = str(result.get("message_status"))
        self._last_xipregister_status = str(result.get("xipregister_status"))
        self._last_error = None
        self.async_write_ha_state()


class CameBptDoorButton(_CameBptButtonBase):
    def __init__(
        self,
        client: CameConnectClient,
        device_id: str,
        options: dict,
        metadata: BptDeviceMetadata | None = None,
    ) -> None:
        super().__init__(client, device_id, options, metadata)
        self._attr_name = metadata.open_door_label if metadata else "Open Door"
        self._attr_unique_id = f"came_bpt_open_door_{self._bpt_device_id}"
        self._attr_icon = "mdi:door-open"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        attrs = super().extra_state_attributes
        attrs["bpt_aux_count"] = len(self._metadata.aux_features) if self._metadata else 0
        attrs["bpt_aux_features"] = (
            [
                {
                    "aux_code": feature.aux_code,
                    "feature_id": feature.feature_id,
                    "name": feature.name,
                    "label": feature.label,
                    "icon": feature.icon,
                }
                for feature in self._metadata.aux_features
            ]
            if self._metadata
            else []
        )
        return attrs

    async def async_press(self) -> None:
        self._last_run = dt_util.utcnow().isoformat()
        try:
            config = await self._resolve_config()
            result = await self._client.async_open_bpt_door(config)
        except Exception as err:
            self._last_error = str(err)
            self.async_write_ha_state()
            raise HomeAssistantError(f"Open door failed: {err}") from err

        self._record_success(result)
        _LOGGER.debug(
            "BPT door-open succeeded for %s with register=%s message=%s",
            self._device_id,
            self._last_register_status,
            self._last_message_status,
        )


class CameBptAuxButton(_CameBptButtonBase):
    def __init__(
        self,
        client: CameConnectClient,
        device_id: str,
        options: dict,
        feature: BptAuxFeature,
        metadata: BptDeviceMetadata | None = None,
    ) -> None:
        super().__init__(client, device_id, options, metadata)
        self._feature = feature
        self._attr_name = feature.label
        self._attr_unique_id = f"came_bpt_aux_{feature.feature_id}_{self._bpt_device_id}"
        self._attr_icon = "mdi:toggle-switch-variant"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        attrs = super().extra_state_attributes
        attrs.update(
            {
                "bpt_aux_code": self._feature.aux_code,
                "bpt_aux_feature_id": self._feature.feature_id,
                "bpt_aux_name": self._feature.name,
                "bpt_aux_label": self._feature.label,
                "bpt_aux_icon": self._feature.icon,
            }
        )
        return attrs

    async def async_press(self) -> None:
        self._last_run = dt_util.utcnow().isoformat()
        try:
            config = await self._resolve_config()
            result = await self._client.async_open_bpt_aux(config, self._feature.aux_code)
        except Exception as err:
            self._last_error = str(err)
            self.async_write_ha_state()
            raise HomeAssistantError(f"{self._feature.label} failed: {err}") from err

        self._record_success(result)
        _LOGGER.debug(
            "BPT AUX %s succeeded for %s with register=%s message=%s",
            self._feature.aux_code,
            self._device_id,
            self._last_register_status,
            self._last_message_status,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    if not BptDoorConfig.has_credentials(entry.options):
        return

    data = hass.data[DOMAIN][entry.entry_id]
    client: CameConnectClient = data["client"]
    device_id = data["device_id"]
    metadata = None
    try:
        metadata = await client.async_get_bpt_device_metadata(device_id, dict(entry.options))
    except Exception:
        _LOGGER.debug("BPT metadata lookup failed during setup; using fallback device labels", exc_info=True)

    entities: list[ButtonEntity] = [CameBptDoorButton(client, device_id, dict(entry.options), metadata)]
    if metadata:
        entities.extend(
            CameBptAuxButton(client, device_id, dict(entry.options), feature, metadata)
            for feature in metadata.aux_features
        )

    async_add_entities(entities)
