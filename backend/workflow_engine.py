# workflow_engine.py – Structured step-by-step guidance with official links

import json
import re
from typing import Tuple, List, Dict

from .llm_client import ask_llm

# ─── Language name map ───────────────────────────────────────
LANG_NAMES = {
    'en': 'English', 'hi': 'Hindi', 'ta': 'Tamil', 'te': 'Telugu',
    'bn': 'Bengali', 'mr': 'Marathi', 'gu': 'Gujarati', 'kn': 'Kannada',
    'ml': 'Malayalam', 'pa': 'Punjabi', 'ur': 'Urdu',
}

# ─── Official links per topic ────────────────────────────────
OFFICIAL_LINKS = {
    "passport": [
        ("Passport Seva Portal (Apply Online)", "https://www.passportindia.gov.in"),
        ("Book Appointment at PSK", "https://passportindia.gov.in/AppOnlineProject/online/redirectToPassportAppln"),
        ("Check Application Status", "https://www.passportindia.gov.in/AppOnlineProject/statusTracker/trackStatusInpNew"),
        ("Find Nearest Passport Seva Kendra", "https://www.passportindia.gov.in/AppOnlineProject/welcomeLink"),
        ("DigiLocker for Documents", "https://www.digilocker.gov.in"),
    ],
    "aadhaar": [
        ("UIDAI Self-Service Portal", "https://ssup.uidai.gov.in/ssup/"),
        ("Update Aadhaar Address Online", "https://uidai.gov.in/en/my-aadhaar/update-aadhaar.html"),
        ("Book Aadhaar Appointment", "https://appointments.uidai.gov.in/easappointment/openscheduling.html"),
        ("Download e-Aadhaar", "https://eaadhaar.uidai.gov.in/"),
        ("Lock/Unlock Biometrics", "https://resident.uidai.gov.in/bio-lock"),
    ],
    "birth_certificate": [
        ("Civil Registration System (CRS)", "https://crsorgi.gov.in/web/index.php/auth/login"),
        ("Delhi Birth Certificate", "https://edistrict.delhigovt.nic.in/"),
        ("Maharashtra Birth Certificate", "https://aaplesarkar.mahaonline.gov.in/"),
        ("Karnataka Nadakacheri Portal", "https://nadakacheri.karnataka.gov.in/"),
        ("DigiLocker for Certificates", "https://www.digilocker.gov.in"),
    ],
    "pan_card": [
        ("NSDL PAN Application", "https://tin.tin.nsdl.com/pan/index.html"),
        ("UTIITSL PAN Services", "https://www.pan.utiitsl.com/PAN/"),
        ("Instant e-PAN (Income Tax)", "https://www.incometax.gov.in/iec/foportal/help/individual/applying-for-epan"),
        ("Check PAN Status", "https://tin.tin.nsdl.com/pantan/StatusTrack.html"),
        ("Link PAN with Aadhaar", "https://eportal.incometax.gov.in/iec/foservices/#/pre-login/bl-link-aadhaar"),
    ],
    "driving_licence": [
        ("Sarathi Parivahan Portal", "https://sarathi.parivahan.gov.in/"),
        ("Apply for Learner's Licence", "https://sarathi.parivahan.gov.in/sarathiservice/stateSelection.do"),
        ("Book DL Appointment", "https://sarathi.parivahan.gov.in/sarathiservice/appointmentSearch.do"),
        ("Renew Driving Licence", "https://sarathi.parivahan.gov.in/sarathiservice/renewDL.do"),
        ("DigiLocker Driving Licence", "https://www.digilocker.gov.in"),
    ],
    "vehicle_rc": [
        ("Vahan Parivahan Portal", "https://vahan.parivahan.gov.in/"),
        ("Check Vehicle RC Details", "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/statevalidation/home.xhtml"),
        ("Transfer of Ownership", "https://vahan.parivahan.gov.in/nrservice/"),
        ("Pay Road Tax Online", "https://vahan.parivahan.gov.in/vahanservice/"),
        ("FASTag Registration", "https://www.netc.org.in/"),
    ],
    "voter_id": [
        ("Voter Service Portal (NVSP)", "https://voters.eci.gov.in/"),
        ("Apply / Correct Voter ID", "https://voters.eci.gov.in/signup/form6"),
        ("Check Voter Registration", "https://electoralsearch.eci.gov.in/"),
        ("Download e-EPIC Card", "https://voters.eci.gov.in/download-eEpic"),
        ("Locate Polling Booth", "https://electoralsearch.eci.gov.in/BLOSearch"),
    ],
    "ration_card": [
        ("National Food Security Portal", "https://nfsa.gov.in/portal/RationCard_Per_State_UTs"),
        ("Apply for Ration Card", "https://nfsa.gov.in/portal/ApplyNew"),
        ("Check Ration Card Status", "https://rcms.nfsa.gov.in/"),
        ("One Nation One Ration Card", "https://impds.nic.in/portal/"),
    ],
    "police_complaint": [
        ("CCTNS Citizen Portal", "https://cctnscitizenportal.gov.in/"),
        ("File Online FIR (Delhi)", "https://delhipolice.gov.in/onlinecomplaint.html"),
        ("National Cybercrime Portal", "https://cybercrime.gov.in/"),
        ("Women Helpline: 181", "https://wcd.nic.in/"), 
        ("Emergency: 100 (Police), 112 (All)", "https://www.112.gov.in/"),
    ],
    "general": [
        ("MyGov India", "https://www.mygov.in/"),
        ("DigiLocker", "https://www.digilocker.gov.in"),
        ("National Government Portal", "https://www.india.gov.in/"),
        ("Umang App Services", "https://web.umang.gov.in/"),
    ],
}


def _clean_json(raw: str) -> str:
    """Strip Markdown fences from LLM output."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _get_links_for_topic(topic: str) -> List[Dict]:
    topic_key = topic.lower().replace(" ", "_")
    # Try exact match first, then partial match
    links = OFFICIAL_LINKS.get(topic_key)
    if not links:
        for key in OFFICIAL_LINKS:
            if key in topic_key or topic_key in key:
                links = OFFICIAL_LINKS[key]
                break
    if not links:
        links = OFFICIAL_LINKS["general"]
    return [{"title": t, "url": u} for t, u in links]


async def process_user_message(
    topic: str,
    message: str,
    current_data: Dict,
    language: str = "en",
    gemini_key: str = "",
    groq_key: str = "",
) -> Tuple[str, Dict, List[Dict]]:
    """Main conversation processor. Returns (reply, merged_data, steps_with_links)."""

    lang_name = LANG_NAMES.get(language, "English")
    links = _get_links_for_topic(topic)
    links_text = "\n".join([f"- {l['title']}: {l['url']}" for l in links])

    system_prompt = f"""You are Beuro AI — a friendly, expert Indian government service assistant.
The user wants help with: '{topic}'.
Always respond in {lang_name}.

OFFICIAL LINKS FOR THIS SERVICE (include the most relevant ones in your reply):
{links_text}

CURRENT USER DATA COLLECTED SO FAR:
{json.dumps(current_data, ensure_ascii=False) if current_data else "Nothing collected yet."}

INSTRUCTIONS:
1. Give a clear numbered step-by-step guide (minimum 3 steps, maximum 6 steps).
2. For each step, mention the website/portal to visit with the full URL.
3. List what documents/information the user will need.
4. At the end, ask for ONE specific missing piece of information to continue personalizing help.
5. Be warm, encouraging and specific — not vague.
6. Format steps clearly as: "Step 1: Title — description. Visit: URL"

Respond ONLY with a valid JSON object (no markdown, no backticks, no extra text):
{{
  "reply": "Your full response in {lang_name} with numbered steps and URLs.",
  "updated_data": {{
    "FieldName": "value extracted from user's message"
  }}
}}
Only add fields to updated_data that the user actually mentioned in their message.
"""

    raw = await ask_llm(f"User says: {message}", system=system_prompt, gemini_key=gemini_key, groq_key=groq_key)
    cleaned = _clean_json(raw)

    try:
        parsed = json.loads(cleaned)
        reply     = parsed.get("reply", "I need more information.")
        new_fields = parsed.get("updated_data", {})
        merged = {**current_data, **new_fields}
    except Exception as e:
        # If JSON parse fails, use the raw text as reply (still better than error message)
        if len(cleaned) > 50 and not cleaned.startswith("⚠️"):
            reply = cleaned  # Raw text is readable
        else:
            reply = f"Sorry, I had a processing error. Please try again. ({e})"
        merged = current_data

    # Always attach the official links as structured steps for the frontend
    steps = links

    return reply, merged, steps
