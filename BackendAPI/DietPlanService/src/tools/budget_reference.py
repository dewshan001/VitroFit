# DietPlanService/budget_reference.py
"""Static reference table of approximate Sri Lankan grocery costs (LKR), so the
LLM is grounded in real local prices for a budget tier instead of guessing.
Small enough (a few dozen items) to embed directly in a prompt - no RAG/vector
DB needed at this scale. Revisit with pgvector only if this grows into a much
larger dataset (full recipe library, live scraped daily prices, hundreds of
items) that no longer fits comfortably in a prompt.

Prices are rough per-typical-portion estimates for prompt grounding, not meant
to be shown to end users as exact figures.
"""

BUDGET_TIERS = {
    "low": {
        "label": "Low (under Rs.2000/day)",
        "guidance": "Favor affordable staples - rice, dhal/lentils, eggs, chicken leg quarters, "
                     "seasonal local vegetables, bananas. Avoid imported or premium items.",
        "reference_items": [
            {"name": "Rice", "portion": "1 cup cooked", "lkr": 40},
            {"name": "Red lentils (parippu)", "portion": "150g cooked", "lkr": 60},
            {"name": "Eggs", "portion": "2 eggs", "lkr": 90},
            {"name": "Chicken leg quarter", "portion": "150g", "lkr": 180},
            {"name": "Local seasonal vegetables", "portion": "200g", "lkr": 80},
            {"name": "Banana", "portion": "1 medium", "lkr": 20},
            {"name": "Coconut", "portion": "1/4 grated", "lkr": 40},
            {"name": "Bread (loaf)", "portion": "2 slices", "lkr": 30},
        ],
    },
    "medium": {
        "label": "Medium (Rs.2000-4000/day)",
        "guidance": "Mix of staples with regular chicken breast/fish, dairy, and some fruit variety.",
        "reference_items": [
            {"name": "Chicken breast", "portion": "150g", "lkr": 280},
            {"name": "Fish (local, e.g. thora/salaya)", "portion": "150g", "lkr": 250},
            {"name": "Greek-style yoghurt / curd", "portion": "150g", "lkr": 150},
            {"name": "Brown rice", "portion": "1 cup cooked", "lkr": 70},
            {"name": "Mixed fruit (apple/orange)", "portion": "1 medium", "lkr": 80},
            {"name": "Oats", "portion": "60g dry", "lkr": 100},
            {"name": "Milk", "portion": "250ml", "lkr": 90},
            {"name": "Chickpeas", "portion": "180g cooked", "lkr": 120},
        ],
    },
    "high": {
        "label": "High (over Rs.4000/day)",
        "guidance": "Can include imported/premium proteins and supplements - salmon, beef, "
                     "protein powder, nuts, avocado - alongside everyday staples.",
        "reference_items": [
            {"name": "Salmon fillet", "portion": "140g", "lkr": 1200},
            {"name": "Beef sirloin", "portion": "150g", "lkr": 900},
            {"name": "Whey protein shake", "portion": "1 scoop", "lkr": 250},
            {"name": "Almonds", "portion": "28g", "lkr": 200},
            {"name": "Avocado", "portion": "1 whole", "lkr": 350},
            {"name": "Quinoa", "portion": "140g cooked", "lkr": 300},
            {"name": "Imported cheese", "portion": "50g", "lkr": 400},
            {"name": "Berries (imported)", "portion": "100g", "lkr": 500},
        ],
    },
}


def resolve_tier(budget_tier: str, budget_custom_amount: float | None) -> dict:
    """Maps a form's budget_tier ("low"/"medium"/"high"/"custom") plus an optional
    custom LKR/day amount to the closest reference tier's guidance + items, so
    a custom amount still gets grounded pricing context instead of none at all.
    """
    if budget_tier == "custom" and budget_custom_amount is not None:
        if budget_custom_amount < 2000:
            key = "low"
        elif budget_custom_amount <= 4000:
            key = "medium"
        else:
            key = "high"
        tier = BUDGET_TIERS[key]
        return {
            "label": f"Custom (Rs.{budget_custom_amount:.0f}/day)",
            "guidance": tier["guidance"],
            "reference_items": tier["reference_items"],
        }
    return BUDGET_TIERS.get(budget_tier, BUDGET_TIERS["medium"])
