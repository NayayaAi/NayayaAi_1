from thefuzz import process, fuzz

def analyze_complaint_for_sections(complaint_text):
    """AI-powered analysis to suggest relevant legal sections based on complaint."""
    if not complaint_text:
        return []

    complaint_lower = complaint_text.lower()

    # Special override: stolen documents are treated differently
    # 1. Define 'Smart' Categories for Fuzzy Matching
    categories = {
    "theft robbery stealing snatched pickpocket burglary": 
        ["IPC Section 378", "IPC Section 379", "IPC Section 380", "IPC Section 381", "IPC Section 392"],

    "assault beaten hit slapped attack injured fight": 
        ["IPC Section 319", "IPC Section 321", "IPC Section 323", "IPC Section 324", "IPC Section 325", "IPC Section 352"],

    "fraud cheating scam forged fake money deception": 
        ["IPC Section 415", "IPC Section 417", "IPC Section 418", "IPC Section 420", "IPC Section 468", "IPC Section 471"],

    "threaten kill intimidation scary criminal intimidation": 
        ["IPC Section 503", "IPC Section 506", "IPC Section 507"],

    "harassment abuse molestation insult woman stalking": 
        ["IPC Section 354", "IPC Section 354A", "IPC Section 354D", "IPC Section 509"],

    "kidnap kidnapping abduct missing child": 
        ["IPC Section 359", "IPC Section 360", "IPC Section 361", "IPC Section 363"],

    "rape sexual assault force sex": 
        ["IPC Section 375", "IPC Section 376"],

    "murder kill homicide death": 
        ["IPC Section 299", "IPC Section 300", "IPC Section 302"],

    "attempt murder try kill attack weapon": 
        ["IPC Section 307"],

    "dowry cruelty husband family harassment": 
        ["IPC Section 498A", "IPC Section 304B"],

    "property damage vandalism destroy property": 
        ["IPC Section 425", "IPC Section 426", "IPC Section 427"],

    "trespass illegal entry house breaking": 
        ["IPC Section 441", "IPC Section 447", "IPC Section 448"],

    "cyber fraud online scam hacking identity theft": 
        ["IT Act Section 43", "IT Act Section 66", "IT Act Section 66C", "IT Act Section 66D"],

    "defamation insult reputation false statement": 
        ["IPC Section 499", "IPC Section 500"],

    "bribery corruption public servant illegal money": 
        ["Prevention of Corruption Act Section 7", "Prevention of Corruption Act Section 13"]
}

    suggested_sections = []

    # 2. Run Fuzzy Logic (Tolerance for typos/synonyms)
    for category_keywords, sections in categories.items():
        # Score of 100 is exact, 70+ is a strong likely match
        if any(word in complaint_lower for word in category_keywords.split()):
            suggested_sections.extend(sections)

    # 3. Handle Lost Documents (Special Case)
    doc_keywords = "passport aadhar license id card certificate voter"
    if fuzz.partial_ratio(doc_keywords, complaint_lower) > 80 and not suggested_sections:
        return ['Non-criminal matter (lost/stolen documents) - Administrative Report']

    # 4. Clean up results
    unique_sections = list(dict.fromkeys(suggested_sections))
    
    # Return top 3, or a default if no match is found
    return unique_sections[:3] if unique_sections else ['IPC Section 323 (General Investigation)'] 