from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

class ServiceCategory(Enum):
    WELLNESS = "wellness"     # Цілителі, енергопрактики
    COACHING = "coaching"     # Коучі, вчителі
    CREATIVE = "creative"     # 3D Дизайн, візуалізація
    HOME = "home_services"    # Ремонт квартир

@dataclass
class ServiceDefinition:
    id: str
    name: str
    category: ServiceCategory
    ai_enabled: bool = False
    icon: str = "✨"

# Твій повний перелік послуг згідно README
SERVICES = [
    ServiceDefinition("healer", "Цілительство", ServiceCategory.WELLNESS, icon="🧘"),
    ServiceDefinition("energy_work", "Енергопрактики", ServiceCategory.WELLNESS, icon="⚡"),
    ServiceDefinition("coach", "Коучинг", ServiceCategory.COACHING, icon="🧠"),
    ServiceDefinition("visual3d", "3D Дизайн", ServiceCategory.CREATIVE, ai_enabled=True, icon="🎨"),
    ServiceDefinition("renovation", "Ремонт квартир", ServiceCategory.HOME, ai_enabled=False, icon="🏠")
]

class ServiceRegistry:
    def get_all(self) -> List[ServiceDefinition]:
        return SERVICES

    def get_by_id(self, service_id: str) -> Optional[ServiceDefinition]:
        return next((s for s in SERVICES if s.id == service_id), None)

service_registry = ServiceRegistry()
