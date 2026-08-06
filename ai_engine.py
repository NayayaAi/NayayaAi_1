from thefuzz import fuzz


def analyze_complaint_for_sections(complaint_text, top_n=3):
    """AI-powered analysis to suggest relevant legal sections based on complaint.

    Returns up to `top_n` section lists, ranked by how strongly the complaint
    matches each category (keyword hits + fuzzy score), not just dict order.
    """
    if not complaint_text:
        return []

    complaint_lower = complaint_text.lower()

    # category keyword string -> list of applicable sections
    categories = {
        "theft robbery stealing snatched pickpocket burglary robbed stole stolen chain snatching dacoity looted":
            ["IPC Section 378", "IPC Section 379", "IPC Section 380", "IPC Section 381", "IPC Section 390", "IPC Section 392", "IPC Section 395"],

        "assault beaten hit slapped attack injured fight attacked hurt punched thrashed grievous hurt":
            ["IPC Section 319", "IPC Section 321", "IPC Section 323", "IPC Section 324", "IPC Section 325", "IPC Section 326", "IPC Section 352"],

        "fraud cheating scam forged fake money deception cheated deceived duped swindled ponzi investment fraud":
            ["IPC Section 415", "IPC Section 417", "IPC Section 418", "IPC Section 420", "IPC Section 465", "IPC Section 468", "IPC Section 471"],

        "extortion forced money illegal demand coercion ransom protection money forced to pay":
            ["IPC Section 383", "IPC Section 384", "IPC Section 385", "IPC Section 386", "IPC Section 387"],

        "threaten kill intimidation scary criminal intimidation threatened blackmail threat to life":
            ["IPC Section 503", "IPC Section 506", "IPC Section 507"],

        "harassment abuse molestation insult woman stalking harassed molested eve teasing outraging modesty":
            ["IPC Section 354", "IPC Section 354A", "IPC Section 354C", "IPC Section 354D", "IPC Section 509"],

        "acid attack burnt face threw acid disfigured":
            ["IPC Section 326A", "IPC Section 326B"],

        "kidnap kidnapping abduct missing child abducted taken forcibly minor missing":
            ["IPC Section 359", "IPC Section 360", "IPC Section 361", "IPC Section 363", "IPC Section 364A"],

        "human trafficking trafficked sold bought forced labour bonded labour illegal trafficking":
            ["IPC Section 370", "IPC Section 370A", "IPC Section 371"],

        "rape sexual assault force sex molested sexually raped":
            ["IPC Section 375", "IPC Section 376"],

        "child abuse pocso minor sexual abuse child molestation inappropriate touch child pornography":
            ["POCSO Act Section 4", "POCSO Act Section 6", "POCSO Act Section 8", "POCSO Act Section 10"],

        "murder kill homicide death killed murdered dead body found dead":
            ["IPC Section 299", "IPC Section 300", "IPC Section 302"],

        "attempt murder try kill attack weapon stabbed shot fired gun tried to kill":
            ["IPC Section 307"],

        "culpable homicide accident death negligent death rash driving death caused death":
            ["IPC Section 304", "IPC Section 304A"],

        "abetment suicide forced suicide drove to suicide suicide note instigated suicide":
            ["IPC Section 306", "IPC Section 309"],

        "dowry cruelty husband family harassment in-laws domestic violence dowry demand dowry death":
            ["IPC Section 498A", "IPC Section 304B", "Dowry Prohibition Act Section 3", "Dowry Prohibition Act Section 4"],

        "property damage vandalism destroy property broke damaged destruction mischief":
            ["IPC Section 425", "IPC Section 426", "IPC Section 427", "IPC Section 435"],

        "arson fire set ablaze burnt house burnt shop deliberately set fire":
            ["IPC Section 435", "IPC Section 436", "IPC Section 438"],

        "trespass illegal entry house breaking entered without permission house breaking":
            ["IPC Section 441", "IPC Section 447", "IPC Section 448", "IPC Section 454", "IPC Section 457"],

        "cyber fraud online scam hacking identity theft phishing digital account otp fraud upi fraud fake website":
            ["IT Act Section 43", "IT Act Section 66", "IT Act Section 66C", "IT Act Section 66D", "IPC Section 420"],

        "cyberstalking obscene online morphed photo revenge porn online harassment fake profile":
            ["IT Act Section 66E", "IT Act Section 67", "IT Act Section 67A", "IPC Section 354D"],

        "defamation insult reputation false statement slander libel spread rumours":
            ["IPC Section 499", "IPC Section 500"],

        "bribery corruption public servant illegal money bribe official demanded bribe":
            ["Prevention of Corruption Act Section 7", "Prevention of Corruption Act Section 13"],

        "counterfeit fake currency fake notes fake product duplicate goods forged documents":
            ["IPC Section 489A", "IPC Section 489B", "IPC Section 465", "IPC Section 467"],

        "criminal breach of trust misappropriation embezzlement dishonest misuse of funds entrusted property":
            ["IPC Section 405", "IPC Section 406", "IPC Section 409"],

        "unlawful assembly rioting mob violence group attack communal riot stone pelting":
            ["IPC Section 141", "IPC Section 143", "IPC Section 146", "IPC Section 147", "IPC Section 148"],

        "drunk driving rash driving hit and run accident negligent driving road accident":
            ["IPC Section 279", "IPC Section 304A", "Motor Vehicles Act Section 184", "Motor Vehicles Act Section 185"],

        "drugs narcotics possession selling drugs peddling drug smuggling":
            ["NDPS Act Section 8", "NDPS Act Section 20", "NDPS Act Section 21", "NDPS Act Section 22"],

        "gambling betting illegal gambling den cricket betting online betting":
            ["Public Gambling Act Section 3", "Public Gambling Act Section 4"],

        "bigamy second marriage married again without divorce":
            ["IPC Section 494", "IPC Section 495"],

        "public nuisance disturbance noise obstruction illegal encroachment public obstruction":
            ["IPC Section 268", "IPC Section 290"],

        "missing person untraceable not found since not returned home disappeared":
            ["IPC Section 365", "CrPC Section 155"],
    }

    # strip stray punctuation so word-boundary matching is reliable
    complaint_words = complaint_lower.translate(
        str.maketrans("", "", ".,!?;:\"'()")
    ).split()
    complaint_word_set = set(complaint_words)

    STOPWORDS = {"to", "and", "or", "in", "on", "of", "the", "a", "at", "for", "with", "id"}

    def keyword_hits(keyword_list, fuzzy_threshold=88):
        """Count how many category keywords appear in the complaint, matched
        as a whole word (exact or close fuzzy match) so short keywords like
        'to' can't false-match inside unrelated words like 'today', and
        'car' can't false-match 'card'."""
        hits = 0
        for kw in keyword_list:
            if kw in STOPWORDS or len(kw) < 3:
                continue
            if kw in complaint_word_set:
                hits += 1
                continue
            if any(fuzz.ratio(kw, w) >= fuzzy_threshold for w in complaint_words):
                hits += 1
        return hits

    # Special case: lost/stolen documents with no other match
    doc_keywords = "passport aadhar aadhaar license pan certificate voter"
    doc_hits = keyword_hits(doc_keywords.split())

    scored = []  # (score, sections)
    for category_keywords, sections in categories.items():
        keyword_list = category_keywords.split()
        hits = keyword_hits(keyword_list)
        if hits > 0:
            # score = matched keywords as a fraction of category size, plus
            # raw hit count so longer, more specific matches rank higher
            score = hits * 10 + (hits / len(keyword_list)) * 5
            scored.append((score, sections))

    if doc_hits > 0 and not scored:
        return ["Non-criminal matter (lost/stolen documents) - Administrative Report"]

    if not scored:
        return ["IPC Section 323 (General Investigation)"]

    # sort by relevance, highest first
    scored.sort(key=lambda x: x[0], reverse=True)

    suggested_sections = []
    for _, sections in scored:
        suggested_sections.extend(sections)

    # Deduplicate while preserving relevance order
    unique_sections = list(dict.fromkeys(suggested_sections))

    return unique_sections[:top_n] if top_n else unique_sections