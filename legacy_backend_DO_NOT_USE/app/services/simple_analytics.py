from datetime import datetime
from collections import defaultdict

class SimpleAnalytics:
    def __init__(self):
        self.demand_log = defaultdict(list)
    
    def log_search(self, service_type, user_id):
        self.demand_log[service_type].append({"user": user_id, "time": datetime.now()})

    def get_all_demand(self):
        return {k: len(v) for k, v in self.demand_log.items()}

    def get_trending_services(self, top_n: int = 5) -> list[dict]:
        """Return top N service types by demand count (desc)."""
        demand = self.get_all_demand()
        sorted_items = sorted(
            demand.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [
            {"service_type": k, "count": v}
            for k, v in sorted_items[:top_n]
        ]

analytics = SimpleAnalytics()
