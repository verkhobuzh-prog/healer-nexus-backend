from app.core.base_module import BaseModule

class EcoPulseModule(BaseModule):
    def __init__(self):
        # Назва має збігатися з PROJECT_ID для фільтрації в майбутньому
        super().__init__("eco_pulse")

    async def health_check(self) -> dict:
        """Статус здоров'я модуля Eco-Pulse."""
        return {
            "module": self.name,
            "status": "healthy",
            "details": {
                "mode": "monitoring",
                "target": "environmental_data"
            }
        }