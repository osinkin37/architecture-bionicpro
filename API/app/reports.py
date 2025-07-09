from datetime import datetime
import random
from typing import List, Dict

def generate_report() -> List[Dict]:
    report_types = ["sales", "inventory", "user_activity"]
    dates = [datetime.now().strftime("%Y-%m-%d") for _ in range(5)]
    
    return [
        {
            "id": f"rep-{i:03d}",
            "type": random.choice(report_types),
            "date": random.choice(dates),
            "metrics": {
                "value": random.randint(100, 1000),
                "growth": round(random.uniform(-10.0, 25.0), 2),
                "target": random.randint(800, 1200)
            }
        }
        for i in range(1, 6)
    ]