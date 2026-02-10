from datetime import datetime
from collections import defaultdict

class SimpleAnalytics:
    def __init__(self):
        self.demand_log = defaultdict(list)
    
    def log_search(self, service_type, user_id):
        self.demand_log[service_type].append({"user": user_id, "time": datetime.now()})

    def get_all_demand(self):
        return {k: len(v) for k, v in self.demand_log.items()}

analytics = SimpleAnalytics()
