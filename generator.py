import os
import re
import random
import google.generativeai as genai
from typing import List

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

# Pattern: [Base][Separator][Suffix]
# Bases: 'adi' or 'aadi'
# Separators: '.' or '_'
# Suffixes: exactly 2 lowercase letters
PATTERN_REGEX = re.compile(r"^(adi|aadi)[._][a-z]{2}$")

SARCASTIC_POOL = [
    "maybeok", "notreally", "stillfine", "kindofokay", "almostsure", "seemsfine", "idkmaybe", "justsaying", "notthatdeep", "couldbe",
    "stillmaybe", "seemsright", "idoubtthat", "notexactly", "kindofmeh", "barelythere", "justfine", "notmuch", "stillidk", "almostthere",
    "sortofok", "notwrong", "couldwork", "justmaybe", "idktho", "seemsok", "notbadish", "almostok", "kindofright", "stillcool",
    "notreallytho", "justenough", "seemsalright", "notexactlytho", "barelyok", "idkanyway", "kindofcool", "stillthinking", "maybeidk", "justthere",
    "notquite", "almostfine", "seemslikely", "idkstill", "kindofthere", "nottoomuch", "justvibing", "stillok", "notreallyok", "maybeish",
    "justchill", "kindoflow", "stillalive", "notbigdeal", "justexisting", "kindofblank", "stillneutral", "maybequiet", "notalot", "justsimple",
    "stillsoft", "kindofslow", "maybeplain", "notloud", "justcalm", "stillsteady", "kindofcoolish", "nottrying", "justidle", "stillmeh",
    "maybeempty", "notpressed", "justlight", "stillmild", "kindofeasy", "notfast", "justbasic", "stillloose", "maybechill", "notserious",
    "justnormal", "stillflat", "kindofdry", "notmuchhere", "justlowkey", "stillsoftly", "maybequietly", "notforced", "justminimal", "stillplain",
    "kindofstill", "notsharp", "juststeady", "stillsoftish", "maybeidle", "notextra", "justenoughish", "stillclear", "kindofneutral", "notpushed",
    "maybeokish", "stillalright", "nottoobad", "kindofokayish", "stillworking", "notreallysure", "maybeagain", "justchecking", "stillpending", "notfinal",
    "kindofready", "stillguessing", "maybeclose", "notquiteyet", "justwaiting", "stillaround", "notcertain", "kindofthereish", "stillholding", "maybeenough",
    "notclear", "justlooking", "stillunclear", "maybeishok", "notperfect", "kindofdone", "stillopen", "maybeidleish", "notfixed", "justneutral",
    "stillgoing", "maybehandled", "notresolved", "kindofmanaged", "stillfineish", "noturgent", "juststeadyish", "stillokish", "maybeadjusted",
    "notfocused", "kindofsimple", "stilllevel", "maybeplainish", "notdeep", "justquiet", "stillstable", "maybecontained", "notpushedyet", "kindofaligned",
    "stillbasic", "maybeunder", "notcomplex", "justsoft", "stilllight", "maybehidden", "notvisible", "kindofsubtle", "stillcalmish", "maybecontainedish",
    "notexpanded", "justminimalist", "stillflatish", "maybealigned", "notoverdone", "kindofbalanced", "stillcentered", "maybeformed", "notextreme", "justeven",
    "stillsoftcore", "maybeheld", "notsharpish", "kindofmuted", "stilltoned", "maybeleveled", "notspiked", "justlow", "stillreduced", "maybeheldback",
    "notforcedyet", "kindofreserved", "stillcoolish", "maybeclosed", "notopenyet", "justcontained", "stilllimited", "maybequietish", "notloudyet", "kindofsilent",
    "stillsofttone", "maybeunderstated", "notvisibleyet", "justcalmish", "stillmellow", "maybehiddenish", "notactive", "kindofresting", "stillpassive", "maybeinactive",
    "notmoving", "justpaused", "stillwaitingish", "maybeidlemode", "notrunning", "kindofstopped", "stillresting", "maybehalted", "notstarted", "justpending",
    "stillqueued", "maybeonhold", "notreadyyet", "kindofdelayed", "stillpaused", "maybeprocessing", "notfinished", "justongoing", "stillworkingish"
]

used_sarcastic = set()

def get_local_fallback() -> List[str]:
    bases = ["adi", "aadi"]
    separators = [".", "_"]
    # Generating some random 2-letter suffixes
    letters = "abcdefghijklmnopqrstuvwxyz"
    fallback = []
    for _ in range(50):
        base = random.choice(bases)
        sep = random.choice(separators)
        suffix = random.choice(letters) + random.choice(letters)
        fallback.append(f"{base}{sep}{suffix}")
    return fallback

def generate_usernames(batch_size: int = 25, mode: str = "pattern") -> List[str]:
    if mode == "sarcastic":
        available = [n for n in SARCASTIC_POOL if n not in used_sarcastic]
        if len(available) < batch_size:
            used_sarcastic.clear()
            available = SARCASTIC_POOL.copy()
        random.shuffle(available)
        selected = available[:batch_size]
        used_sarcastic.update(selected)
        return selected

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "Generate a list of 50 Instagram usernames following this exact pattern: "
            "[Base][Separator][Suffix].\n"
            "Bases must be exactly 'adi' or 'aadi'.\n"
            "Separators must be exactly '.' or '_'.\n"
            "Suffixes must be exactly 2 lowercase English letters.\n"
            "Examples: adi.io, aadi_hq, adi.fx\n"
            "Provide only the usernames, one per line, with no extra text."
        )
        response = model.generate_content(prompt)
        ai_names = [line.strip() for line in response.text.split('\n') if line.strip()]
    except Exception as e:
        print(f"Gemini API error: {e}")
        ai_names = []

    fallback_names = get_local_fallback()
    
    # Merge, deduplicate, filter, and shuffle
    all_names = list(set(ai_names + fallback_names))
    valid_names = [name for name in all_names if PATTERN_REGEX.match(name)]
    
    # Fill up with more valid names if needed
    while len(valid_names) < batch_size:
        valid_names.extend([name for name in get_local_fallback() if name not in valid_names])
        valid_names = list(set(valid_names))
        
    random.shuffle(valid_names)
    return valid_names[:batch_size]
