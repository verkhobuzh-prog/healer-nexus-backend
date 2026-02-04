from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class DemandSignal:
    """
    Сигнал попиту на послугу.
    
    Зберігає: service_type, user_id, timestamp
    """
    def __init__(self, service_type: str, user_id: int):
        self.service_type = service_type
        self.user_id = user_id
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_type": self.service_type,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat()
        }

class SimpleAnalytics:
    """
    Проста аналітика попиту на послуги.
    
    Зберігає дані в пам'яті (без БД).
    Використовується для:
    - Логування пошуків користувачів
    - Підрахунок попиту за періоди
    - Виявлення дисбалансу попит/пропозиція
    """
    
    def __init__(self):
        # Словник: service_type -> List[DemandSignal]
        self.demand_log: Dict[str, List[DemandSignal]] = defaultdict(list)
        logger.info("📊 Simple Analytics initialized")
    
    def log_search(self, service_type: str, user_id: int):
        """
        Логувати пошук послуги користувачем.
        
        Args:
            service_type: Тип послуги (healer, coach, etc)
            user_id: ID користувача
        """
        signal = DemandSignal(service_type, user_id)
        self.demand_log[service_type].append(signal)
        
        logger.info(f"📈 Demand signal: user {user_id} searched for {service_type}")
    
    def get_demand_last_n_days(self, service_type: str, days: int = 7) -> int:
        """
        Підрахунок попиту за останні N днів.
        
        Args:
            service_type: Тип послуги
            days: Кількість днів
        
        Returns:
            int: Кількість пошуків
        """
        cutoff = datetime.now() - timedelta(days=days)
        searches = self.demand_log.get(service_type, [])
        
        return len([s for s in searches if s.timestamp > cutoff])
    
    def get_imbalance(self, service_type: str, specialist_count: int) -> float:
        """
        Дисбаланс попит/пропозиція.
        
        Формула: demand_7d / specialist_count
        
        Args:
            service_type: Тип послуги
            specialist_count: Кількість спеціалістів
        
        Returns:
            float: Коефіцієнт дисбалансу
                   > 5.0 - високий попит, мало спеціалістів
                   1.0-5.0 - нормальний баланс
                   < 1.0 - низький попит
        """
        demand = self.get_demand_last_n_days(service_type, days=7)
        
        if specialist_count == 0:
            return float('inf') if demand > 0 else 0.0
        
        return demand / specialist_count
    
    def get_all_demand(self) -> Dict[str, int]:
        """
        Попит по всім сервісам за останні 7 днів.
        
        Returns:
            dict: {service_type: demand_count}
        """
        result = {}
        
        for service_type in self.demand_log.keys():
            result[service_type] = self.get_demand_last_n_days(service_type)
        
        return result
    
    def get_trending_services(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Топ N найпопулярніших послуг.
        
        Args:
            top_n: Кількість послуг у топі
        
        Returns:
            list: Відсортований список [{service, demand}, ...]
        """
        demand = self.get_all_demand()
        
        sorted_services = sorted(
            demand.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        return [
            {"service_type": service, "demand_7d": demand}
            for service, demand in sorted_services
        ]
    
    def clear_old_data(self, days: int = 30):
        """
        Очистити дані старші за N днів (для економії пам'яті).
        
        Args:
            days: Видалити дані старіші за цей період
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        for service_type in self.demand_log.keys():
            self.demand_log[service_type] = [
                s for s in self.demand_log[service_type]
                if s.timestamp > cutoff
            ]
        
        logger.info(f"🧹 Cleared analytics data older than {days} days")

# Глобальний інстанс
analytics = SimpleAnalytics()
