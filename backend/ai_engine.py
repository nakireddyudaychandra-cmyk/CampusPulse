def analyze_issue(title, description):

    # Combine title and description
    text = (title + " " + description).lower()

    # Default values
    category = "General"
    priority = "Medium"


    # =============================
    # CATEGORY DETECTION
    # =============================

    # AC / HVAC
    if (
        "ac" in text
        or "air conditioner" in text
        or "air conditioning" in text
        or "cooling" in text
    ):
        category = "AC/HVAC"


    # Network
    elif (
        "wifi" in text
        or "wi-fi" in text
        or "internet" in text
        or "network" in text
    ):
        category = "Network"


    # Equipment
    elif (
        "projector" in text
        or "computer" in text
        or "printer" in text
    ):
        category = "Equipment"


    # Plumbing
    elif (
        "water" in text
        or "leak" in text
        or "leakage" in text
        or "pipe" in text
    ):
        category = "Plumbing"


    # Electrical
    elif (
        "electric" in text
        or "electrical" in text
        or "power" in text
        or "switch" in text
        or "socket" in text
    ):
        category = "Electrical"


    # =============================
    # PRIORITY DETECTION
    # =============================

    # Critical
    if (
        "fire" in text
        or "spark" in text
        or "electric shock" in text
        or "danger" in text
    ):
        priority = "Critical"


    # High
    elif (
        "not working" in text
        or "broken" in text
        or "very hot" in text
        or "water leakage" in text
        or "no internet" in text
    ):
        priority = "High"


    # Low
    elif (
        "slow" in text
        or "minor" in text
        or "small" in text
    ):
        priority = "Low"


    return category, priority