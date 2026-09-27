from thefuzz import fuzz

MIN_COMPLAINT_WORDS = 6
MIN_COMPLAINT_CHARS = 20


def analyze_complaint_for_sections(complaint_text, top_n=3):
    if not complaint_text:
        return []

    complaint_text = complaint_text.strip()
    complaint_lower = complaint_text.lower()
    complaint_words = complaint_lower.translate(
        str.maketrans("", "", ".,!?;:\"'()")
    ).split()

    too_short = (
        len(complaint_text) < MIN_COMPLAINT_CHARS
        or len(complaint_words) < MIN_COMPLAINT_WORDS
    )

    complaint_word_set = set(complaint_words)
    STOPWORDS = {"to", "and", "or", "in", "on", "of", "the", "a", "at", "for", "with", "id"}

    # category keyword string -> list of applicable sections
    categories = {
        "theft robbery stealing steal stole stolen snatched snatching snatch pickpocket pickpocketing burglary burgled burglar robbed rob robbing dacoity dacoits looted loot looting shoplifting breakin housebreaking missing stolen items stolen goods stolen vehicle stolen bike stolen car stolen phone stolen mobile stolen wallet stolen purse stolen jewellery carried away taken away vanished belongings":
            ["IPC Section 378", "IPC Section 379", "IPC Section 380", "IPC Section 381", "IPC Section 390", "IPC Section 392", "IPC Section 395"],

        "assault beaten beat beating hit hitting slapped slap attack attacked attacking injured injury fight fighting fought hurt hurting punched punch thrashed thrashing grievous hurt wound wounded wounding bruises bruised bodily harm physical assault manhandled manhandling scuffle brawl blows kicked kicking pushed shoved struck violently":
            ["IPC Section 319", "IPC Section 321", "IPC Section 323", "IPC Section 324", "IPC Section 325", "IPC Section 326", "IPC Section 352"],

        "fraud cheating cheat cheated scam scammed forged forge forgery fake money deception deceive deceived duped dupe swindled swindle ponzi investment fraud online fraud loan fraud emi fraud chit fund fraud misrepresentation false promise fraudulent scheme fraudulent transaction siphoned diverted embezzled tricked into paying fake job offer fake investment":
            ["IPC Section 415", "IPC Section 417", "IPC Section 418", "IPC Section 420", "IPC Section 465", "IPC Section 468", "IPC Section 471"],

        "extortion forced money illegal demand coercion coerced ransom protection money forced to pay demanded money under threat blackmailed for money threatened for money hafta vasooli forced payment illegal collection":
            ["IPC Section 383", "IPC Section 384", "IPC Section 385", "IPC Section 386", "IPC Section 387"],

        "threaten threatened threatening kill intimidation intimidate intimidated scary criminal intimidation blackmail blackmailed threat to life life threat warned dire consequences threatening messages threatening calls threatened to harm threatened to kill sent threatening letter":
            ["IPC Section 503", "IPC Section 506", "IPC Section 507"],

        "harassment harass harassed abuse abused abusive molestation molested insult insulted insulting woman stalking stalked followed repeatedly eve teasing outraging modesty inappropriate comments lewd remarks catcalling obscene gestures unwanted attention passed lewd comments constantly bothering":
            ["IPC Section 354", "IPC Section 354A", "IPC Section 354C", "IPC Section 354D", "IPC Section 509"],

        "acid attack burnt face threw acid disfigured acid thrown corrosive substance chemical attack chemical burns":
            ["IPC Section 326A", "IPC Section 326B"],

        "kidnap kidnapping abduct abducted abduction missing child taken forcibly minor missing forcibly taken away carried off unlawfully detained held captive confined against will locked up against will taken without consent":
            ["IPC Section 359", "IPC Section 360", "IPC Section 361", "IPC Section 363", "IPC Section 364A"],

        "human trafficking trafficked sold bought forced labour bonded labour illegal trafficking sold into slavery forced prostitution recruited under false pretext trafficked for labour trafficked for marriage":
            ["IPC Section 370", "IPC Section 370A", "IPC Section 371"],

        "rape raped sexual assault force sex molested sexually assaulted outraged modesty non-consensual forced intercourse sexually violated":
            ["IPC Section 375", "IPC Section 376"],

        "child abuse pocso minor sexual abuse child molestation inappropriate touch child pornography touched inappropriately sexually exploited grooming online exploitation child sexual exploitation inappropriate contact with minor":
            ["POCSO Act Section 4", "POCSO Act Section 6", "POCSO Act Section 8", "POCSO Act Section 10"],

        "child cruelty harm harming mistreat mistreating illtreat ill-treat neglect neglecting neglected abandon abandoned abandonment battered beating child starved starving denied food locked child alone deprived of care forced child labour child labour scolded excessively physically punished child":
            ["Juvenile Justice Act Section 75", "IPC Section 317", "IPC Section 323"],

        "murder kill homicide death killed murdered dead body found dead deceased slain stabbed to death shot dead strangled to death fatal injuries beaten to death":
            ["IPC Section 299", "IPC Section 300", "IPC Section 302"],

        "attempt murder try kill attack weapon stabbed shot fired gun tried to kill life threatening injury attempted to kill attacked with knife attacked with weapon":
            ["IPC Section 307"],

        "culpable homicide accident death negligent death rash driving death caused death died due to negligence medical negligence death fatal accident death by negligence":
            ["IPC Section 304", "IPC Section 304A"],

        "abetment suicide forced suicide drove to suicide suicide note instigated suicide driven to suicide harassment leading to suicide pressured into suicide":
            ["IPC Section 306", "IPC Section 309"],

        "dowry cruelty husband family harassment in-laws domestic violence dowry demand dowry death burnt for dowry beaten for dowry mental harassment for dowry demanded dowry taunted for dowry":
            ["IPC Section 498A", "IPC Section 304B", "Dowry Prohibition Act Section 3", "Dowry Prohibition Act Section 4"],

        "property damage vandalism destroy property broke damaged destruction mischief smashed windows broken vehicle damaged crops damaged shop vandalized destroyed belongings damaged furniture":
            ["IPC Section 425", "IPC Section 426", "IPC Section 427", "IPC Section 435"],

        "arson fire set ablaze burnt house burnt shop deliberately set fire torched fire set deliberately set the house on fire":
            ["IPC Section 435", "IPC Section 436", "IPC Section 438"],

        "trespass illegal entry house breaking entered without permission house breaking forcibly entered unauthorized entry broke into premises entered the house forcibly climbed into house":
            ["IPC Section 441", "IPC Section 447", "IPC Section 448", "IPC Section 454", "IPC Section 457"],

        "cyber fraud online scam hacking identity theft phishing digital account otp fraud upi fraud fake website online banking fraud credit card fraud debit card fraud sim swap fraud fake loan app fraud investment app fraud account hacked money debited fraudulently unauthorized transaction":
            ["IT Act Section 43", "IT Act Section 66", "IT Act Section 66C", "IT Act Section 66D", "IPC Section 420"],

        "cyberstalking obscene online morphed photo revenge porn online harassment fake profile fake account impersonation online blackmail sextortion morphed images circulated private photos leaked":
            ["IT Act Section 66E", "IT Act Section 67", "IT Act Section 67A", "IPC Section 354D"],

        "defamation insult reputation false statement slander libel spread rumours character assassination false allegations online defamation damaged reputation spreading false rumours":
            ["IPC Section 499", "IPC Section 500"],

        "bribery corruption public servant illegal money bribe official demanded bribe asked for bribe corrupt practice took bribe official demanded money for work":
            ["Prevention of Corruption Act Section 7", "Prevention of Corruption Act Section 13"],

        "counterfeit fake currency fake notes fake product duplicate goods forged documents fake certificate fake degree fake stamp fake seal fake signature":
            ["IPC Section 489A", "IPC Section 489B", "IPC Section 465", "IPC Section 467"],

        "criminal breach of trust misappropriation embezzlement dishonest misuse of funds entrusted property misappropriated funds diverted funds entrusted money not returned":
            ["IPC Section 405", "IPC Section 406", "IPC Section 409"],

        "unlawful assembly rioting mob violence group attack communal riot stone pelting mob attacked group assaulted crowd attacked":
            ["IPC Section 141", "IPC Section 143", "IPC Section 146", "IPC Section 147", "IPC Section 148"],

        "drunk driving rash driving hit and run accident negligent driving road accident drove under influence intoxicated driving reckless driving speeding accident":
            ["IPC Section 279", "IPC Section 304A", "Motor Vehicles Act Section 184", "Motor Vehicles Act Section 185"],

        "drugs narcotics possession selling drugs peddling drug smuggling found with drugs drug dealer supplying drugs consuming drugs illegal substance":
            ["NDPS Act Section 8", "NDPS Act Section 20", "NDPS Act Section 21", "NDPS Act Section 22"],

        "gambling betting illegal gambling den cricket betting online betting satta matka running a gambling den":
            ["Public Gambling Act Section 3", "Public Gambling Act Section 4"],

        "bigamy second marriage married again without divorce remarried without divorcing":
            ["IPC Section 494", "IPC Section 495"],

        "public nuisance disturbance noise obstruction illegal encroachment public obstruction loud music disturbing peace blocking road":
            ["IPC Section 268", "IPC Section 290"],

        "missing person untraceable not found since not returned home disappeared went missing not seen since left home has not returned":
            ["IPC Section 365", "CrPC Section 155"],

        "altering destroying tampering tampered fabricated fabricating evidence disappearance concealing evidence hiding evidence false evidence forged record erased destroyed deleted evidence hid the weapon destroyed proof":
            ["IPC Section 201", "IPC Section 204", "IPC Section 192", "IPC Section 193", "IPC Section 477", "IPC Section 477A"],

        "illegal weapon unlicensed weapon country made pistol illegal firearm unlicensed firearm possession of arms without license found with knife found with gun illegal possession of weapon":
            ["Arms Act Section 25", "Arms Act Section 27"],

        "cheque bounced dishonoured cheque insufficient funds cheque returned cheque unpaid payment cheque dishonour cheque bounce":
            ["Negotiable Instruments Act Section 138"],

        "sexual harassment at workplace inappropriate behavior by colleague office harassment workplace misconduct boss harassed superior harassed inappropriate advances at work":
            ["POSH Act Section 4", "IPC Section 354A"],

        "elderly abuse senior citizen neglect abandoned elderly parents ill treatment of parents refused to maintain parents denied care to elderly parents":
            ["Maintenance and Welfare of Parents and Senior Citizens Act Section 24"],

        "animal cruelty beating animal poisoning animal killing stray dog cruelty to animal mistreating animal starving animal":
            ["Prevention of Cruelty to Animals Act Section 11"],

        "illegal possession of land land grabbing encroached land forcibly occupied land occupied property illegally captured land":
            ["IPC Section 447", "IPC Section 448"],
    }

    # strip stray punctuation so word-boundary matching is reliable
    def keyword_hits(keyword_list, fuzzy_threshold=92, min_fuzzy_len=5):
        hits = 0
        for kw in keyword_list:
            if kw in STOPWORDS or len(kw) < 4:
                continue
            if kw in complaint_word_set:
                hits += 1
                continue
            if len(kw) >= min_fuzzy_len:
                if any(fuzz.ratio(kw, w) >= fuzzy_threshold
                       for w in complaint_words if len(w) >= min_fuzzy_len):
                    hits += 1
        return hits

    doc_keywords = "passport aadhar aadhaar license pan certificate voter"
    doc_hits = keyword_hits(doc_keywords.split())

    scored = []
    for category_keywords, sections in categories.items():
        keyword_list = category_keywords.split()
        hits = keyword_hits(keyword_list)
        # require 2+ hits, OR a single confident EXACT (non-fuzzy) hit on a
        # long, specific keyword (e.g. "murdered", "kidnapped")
        confident_single = hits == 1 and any(
            kw in complaint_word_set and len(kw) >= 6 for kw in keyword_list
        )
        if hits >= 2 or confident_single:
            score = hits * 10 + (hits / len(keyword_list)) * 5
            scored.append((score, sections))

    # Guard: only bail out on "too short/vague" if we found no confident
    # category match. A short-but-specific narrative should never be
    # blocked from matching.
    if too_short and not scored:
        return ["Insufficient detail in narrative — manual review required"]

    if doc_hits > 0 and not scored:
        return ["Non-criminal matter (lost/stolen documents) - Administrative Report"]

    if not scored:
        return ["IPC Section 323 (General Investigation) — low-confidence, verify manually"]

    scored.sort(key=lambda x: x[0], reverse=True)
    suggested_sections = []
    for _, sections in scored:
        suggested_sections.extend(sections)

    unique_sections = list(dict.fromkeys(suggested_sections))
    return unique_sections[:top_n] if top_n else unique_sections