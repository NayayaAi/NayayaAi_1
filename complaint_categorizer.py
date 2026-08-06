"""
Categorizes citizen complaints into crime-severity buckets using
offline keyword matching — same approach as your IPC section mapper.
The citizen never selects this; it's derived automatically from
their incident description text.
"""

CATEGORY_RULES = [
    {
        "category": "Murder / Homicide",
        "is_cognizable": True,
        "keywords": [
            "murder", "killed", "kill him", "kill her", "homicide",
            "stabbed to death", "shot dead", "beaten to death",
            "attempt to murder", "tried to kill"
        ]
    },
    {
        "category": "Sexual Offence",
        "is_cognizable": True,
        "keywords": [
            "rape", "raped", "sexual assault", "molest", "molested",
            "outraging modesty", "sexually abused", "gang rape",
            "inappropriately touched", "forced sexual"
        ]
    },
    {
        "category": "Kidnapping / Missing Person",
        "is_cognizable": True,
        "keywords": [
            "kidnap", "abduct", "missing person", "not come back home",
            "taken away forcibly", "trafficking"
        ]
    },
    {
        "category": "Assault / Violence",
        "is_cognizable": True,
        "keywords": [
            "assault", "beaten", "attacked", "stabbed", "hit with",
            "grievous hurt", "acid attack", "domestic violence",
            "hit me", "physically abused"
        ]
    },
    {
        "category": "Theft / Robbery",
        "is_cognizable": True,
        "keywords": [
            "theft", "stolen", "robbed", "robbery", "burglary",
            "broke into my house", "snatched", "pickpocket", "chain snatching"
        ]
    },
    {
        "category": "Cybercrime / Fraud",
        "is_cognizable": True,
        "keywords": [
            "online fraud", "otp", "upi fraud", "hacked", "phishing",
            "cyberbullying", "fake account", "blackmail online",
            "cheated online", "digital arrest"
        ]
    },
    {
        "category": "Financial Fraud / Cheating",
        "is_cognizable": True,
        "keywords": [
            "cheated", "fraud", "duped", "fake investment", "ponzi",
            "did not return money", "forged", "counterfeit"
        ]
    },
]

NON_COGNIZABLE_KEYWORDS = [
    "neighbor dispute", "neighbour dispute", "property dispute",
    "civil matter", "loan not repaid", "landlord", "tenant dispute",
    "noise complaint", "parking dispute", "verbal abuse only",
    "defamation", "breach of contract", "family property division",
    "divorce", "marriage dispute", "workplace dispute"
]


def categorize_complaint(text: str) -> dict:
    """
    Takes the incident description text and automatically returns:
    {
        "category": str,
        "is_cognizable": bool,
        "can_file_fir": bool
    }
    The citizen never provides this — it's derived purely from
    the narrative they typed.
    """
    if not text:
        return {"category": "Other / Unclassified", "is_cognizable": False, "can_file_fir": False}

    text_lower = text.lower()

    for rule in CATEGORY_RULES:
        for kw in rule["keywords"]:
            if kw in text_lower:
                return {
                    "category": rule["category"],
                    "is_cognizable": rule["is_cognizable"],
                    "can_file_fir": rule["is_cognizable"]
                }

    for kw in NON_COGNIZABLE_KEYWORDS:
        if kw in text_lower:
            return {
                "category": "Other (Non-Cognizable)",
                "is_cognizable": False,
                "can_file_fir": False
            }

    return {
        "category": "Other / Needs Review",
        "is_cognizable": False,
        "can_file_fir": False
    }