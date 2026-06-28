# backend/ai/categorizer.py
"""Auto-categorize transactions based on description and context."""

CATEGORY_KEYWORDS = {
    "sales_product": ["sold", "becha", "bikri", "sale", "bik gaya", "customer"],
    "sales_service": ["service", "repair", "seva", "kaam kiya", "labour charge"],
    "inventory": ["stock", "maal", "saman", "kharida", "purchase", "wholesale"],
    "labor_wages": ["wages", "mazdoori", "salary", "tankhah", "labour"],
    "transport_fuel": ["petrol", "diesel", "fuel", "transport", "delivery", "auto"],
    "rent_premises": ["rent", "kiraya", "dukaan", "shop"],
    "utilities": ["bijli", "electricity", "pani", "water", "gas"],
    "equipment": ["repair", "machine", "tool", "equipment"],
    "food_personal": ["khana", "food", "chai", "lunch", "dinner", "nashta"],
    "mobile_internet": ["recharge", "mobile", "internet", "data", "phone"],
}


def auto_categorize(description: str, tx_type: str = "expense") -> str:
    desc_lower = description.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return cat
    return "other_income" if tx_type == "income" else "other_expense"
