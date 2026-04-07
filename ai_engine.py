from thefuzz import process, fuzz

def analyze_complaint_for_sections(complaint_text):
    """AI-powered analysis to suggest relevant legal sections based on complaint."""
    if not complaint_text:
        return []

    complaint_lower = complaint_text.lower()

    categories = {
        "theft robbery stealing snatched pickpocket burglary robbed stole": 
            ["IPC Section 378", "IPC Section 379", "IPC Section 380", "IPC Section 381", "IPC Section 392"],

        "assault beaten hit slapped attack injured fight attacked hurt punched": 
            ["IPC Section 319", "IPC Section 321", "IPC Section 323", "IPC Section 324", "IPC Section 325", "IPC Section 352"],

        "fraud cheating scam forged fake money deception cheated deceived": 
            ["IPC Section 415", "IPC Section 417", "IPC Section 418", "IPC Section 420", "IPC Section 468", "IPC Section 471"],

        "threaten kill intimidation scary criminal intimidation threatened blackmail": 
            ["IPC Section 503", "IPC Section 506", "IPC Section 507"],

        "harassment abuse molestation insult woman stalking harassed molested": 
            ["IPC Section 354", "IPC Section 354A", "IPC Section 354D", "IPC Section 509"],

        "kidnap kidnapping abduct missing child abducted taken forcibly": 
            ["IPC Section 359", "IPC Section 360", "IPC Section 361", "IPC Section 363"],

        "rape sexual assault force sex molested sexually": 
            ["IPC Section 375", "IPC Section 376"],

        "murder kill homicide death killed murdered dead body": 
            ["IPC Section 299", "IPC Section 300", "IPC Section 302"],

        "attempt murder try kill attack weapon stabbed shot fired gun": 
            ["IPC Section 307"],

        "dowry cruelty husband family harassment in-laws domestic violence": 
            ["IPC Section 498A", "IPC Section 304B"],

        "property damage vandalism destroy property broke damaged destruction": 
            ["IPC Section 425", "IPC Section 426", "IPC Section 427"],

        "trespass illegal entry house breaking entered without permission": 
            ["IPC Section 441", "IPC Section 447", "IPC Section 448"],

        "cyber fraud online scam hacking identity theft phishing digital account": 
            ["IT Act Section 43", "IT Act Section 66", "IT Act Section 66C", "IT Act Section 66D"],

        "defamation insult reputation false statement slander libel": 
            ["IPC Section 499", "IPC Section 500"],

        "bribery corruption public servant illegal money bribe official": 
            ["Prevention of Corruption Act Section 7", "Prevention of Corruption Act Section 13"]
    }

    suggested_sections = []

    for category_keywords, sections in categories.items():
        keyword_list = category_keywords.split()

        # Fast path: direct word match
        direct_match = any(word in complaint_lower for word in keyword_list)

        # Fuzzy path: catches typos, variants, partial phrases
        fuzzy_match = fuzz.partial_ratio(category_keywords, complaint_lower) > 65

        if direct_match or fuzzy_match:
            suggested_sections.extend(sections)

    # Special case: lost/stolen documents with no other match
    doc_keywords = "passport aadhar license id card certificate voter"
    if fuzz.partial_ratio(doc_keywords, complaint_lower) > 80 and not suggested_sections:
        return ["Non-criminal matter (lost/stolen documents) - Administrative Report"]

    # Deduplicate while preserving order
    unique_sections = list(dict.fromkeys(suggested_sections))

    # Return top 3, or a safe default
    return unique_sections[:3] if unique_sections else ["IPC Section 323 (General Investigation)"]
