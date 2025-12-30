import re
from typing import Dict, Any


def normalize_user_input(raw: Dict[str, Any]) -> Dict[str, Any]:
    data = raw.copy()

    # -------- Budget ----------
    budget = str(data.get("budget", ""))
    nums = list(map(int, re.findall(r"\d+", budget.replace(",", ""))))
    if len(nums) >= 2:
        data["budget_numeric"] = (nums[0] + nums[1]) // 2
    elif len(nums) == 1:
        data["budget_numeric"] = nums[0]
    else:
        data["budget_numeric"] = 80000

    # -------- Priorities ----------
    usage = (data.get("usage") or "").lower()

    data["gpu_priority"] = "high" if "gaming" in usage else "medium"
    data["cpu_priority"] = "high" if "editing" in usage or "programming" in usage else "medium"
    data["storage_priority"] = data.get("storage_capacity", "medium")

    return data
