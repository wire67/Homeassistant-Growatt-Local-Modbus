"""Sensor Entity Description for the Growatt integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntityDescription


@dataclass
class GrowattSwitchRequiredKeysMixin:
    """Mixin for required keys."""
    key: str


@dataclass
class GrowattSwitchEntityDescription(SwitchEntityDescription, GrowattSwitchRequiredKeysMixin):
    """Describes Growatt sensor entity."""
    key: str
    name: str

    def __hash__(self):
        return hash((self.key, self.name))  # Use key and name or any hashable attributes

    def __eq__(self, other):
        if isinstance(other, GrowattSwitchEntityDescription):
            return (self.key, self.name) == (other.key, other.name)
        return False


