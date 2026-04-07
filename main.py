#!/usr/bin/env python3
"""
Sjekk ledige vielsestider hos Oslo kommune.
Kjør daglig for å finne ledige tider frem til 27. juni 2026.
"""

import os
import smtplib
import subprocess
import sys
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from dotenv import load_dotenv

load_dotenv()  # Les .env-fil i samme mappe


API_URL = "https://api.booking.oslo.kommune.no/api/schedule"
ASSET_ID = "c641abdd-6352-477b-8d34-d5b299922330"
START_DATE = date(2026, 4, 7)  # Kun tider etter 17. mai
END_DATE = date(2026, 6, 20)

# ── Email config ─────────────────────────────────────────
# Set these as environment variables, or edit directly here.
# To create a Gmail App Password: https://myaccount.google.com/apppasswords
EMAIL_TO = "eskild.mageli@gmail.com"
EMAIL_FROM = os.environ.get("VIELSE_EMAIL_FROM", "")
EMAIL_PASSWORD = os.environ.get("VIELSE_EMAIL_PASSWORD", "")
SMTP_SERVER = os.environ.get("VIELSE_SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("VIELSE_SMTP_PORT", "465"))

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-GB,en;q=0.7",
    "origin": "https://booking.oslo.kommune.no",
    "referer": "https://booking.oslo.kommune.no/",
    "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Brave";v="146"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "sec-gpc": "1",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
}

WEEKDAY_NAMES = {
    0: "mandag",
    1: "tirsdag",
    2: "onsdag",
    3: "torsdag",
    4: "fredag",
    5: "lørdag",
    6: "søndag",
}


def get_week_start(d: date) -> date:
    """Return Monday of the week containing date d."""
    return d - timedelta(days=d.weekday())


def fetch_week(from_date: date, to_date: date) -> dict:
    """Fetch schedule for one week window."""
    params = {
        "bookableAssetIds": ASSET_ID,
        "fromInclusive": from_date.isoformat(),
        "toInclusive": to_date.isoformat(),
    }
    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def check_availability():
    """Check all weeks from today until END_DATE and report available slots."""
    today = date.today()
    available_slots: list[tuple[str, str, str]] = []  # (date, time, weekday)

    search_from = max(today, START_DATE)
    current_monday = get_week_start(search_from)

    print(f"🔍 Sjekker ledige vielsestider fra {search_from} til {END_DATE} ...\n")

    while current_monday <= END_DATE:
        week_sunday = current_monday + timedelta(days=6)
        # Clamp to END_DATE so we don't fetch beyond what we care about
        fetch_end = min(week_sunday, END_DATE)

        print(f"  Henter uke {current_monday} → {fetch_end} ... ", end="", flush=True)

        try:
            data = fetch_week(current_monday, fetch_end)
        except requests.RequestException as e:
            print(f"❌ Feil: {e}")
            current_monday += timedelta(days=7)
            continue

        timeslots_by_date = data.get("timeslotsByDate", {})
        week_available = 0

        for date_str, slots in sorted(timeslots_by_date.items()):
            slot_date = date.fromisoformat(date_str)
            if slot_date < search_from or slot_date > END_DATE:
                continue
            weekday = WEEKDAY_NAMES[slot_date.weekday()]
            for slot in slots:
                if slot.get("bookingAllowed") and not slot.get("booked"):
                    time_str = slot["startTime"][:5]  # "08:00"
                    available_slots.append((date_str, time_str, weekday))
                    week_available += 1

        if week_available:
            print(f"✅ {week_available} ledig(e) tid(er)!")
        else:
            print("ingen ledige tider")

        current_monday += timedelta(days=7)

    # ── Summary ──────────────────────────────────────────────
    print("\n" + "=" * 55)
    if available_slots:
        print(f"🎉 Fant {len(available_slots)} ledig(e) tid(er)!\n")
        print(f"  {'Dato':<14} {'Dag':<10} {'Klokkeslett'}")
        print(f"  {'-'*14} {'-'*10} {'-'*11}")
        for date_str, time_str, weekday in available_slots:
            print(f"  {date_str:<14} {weekday:<10} {time_str}")
        print(
            f"\n👉 Gå til https://booking.oslo.kommune.no for å booke!"
        )
    else:
        print("😔 Ingen ledige tider funnet frem til", END_DATE)
        print("   Prøv igjen i morgen – tider kan bli frigjort!")
    print("=" * 55)

    return available_slots


def build_email_body(slots: list[tuple[str, str, str]]) -> tuple[str, str]:
    """Build plain-text and HTML email bodies from available slots."""
    booking_url = "https://booking.oslo.kommune.no"

    # ── Plain text ───────────────────────────────────────
    lines = [f"Hei!\n\nDet er {len(slots)} ledig(e) vielsestid(er):\n"]
    lines.append(f"  {'Dato':<14} {'Dag':<10} {'Klokkeslett'}")
    lines.append(f"  {'-'*14} {'-'*10} {'-'*11}")
    for d, t, w in slots:
        lines.append(f"  {d:<14} {w:<10} {t}")
    lines.append(f"\nBook her: {booking_url}")
    text_body = "\n".join(lines)

    # ── HTML ─────────────────────────────────────────────
    rows = "".join(
        f"<tr><td>{d}</td><td>{w}</td><td>{t}</td></tr>" for d, t, w in slots
    )
    html_body = f"""\
<html><body>
<h2>🎉 {len(slots)} ledig(e) vielsestid(er) funnet!</h2>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
  <tr style="background:#f0f0f0;">
    <th>Dato</th><th>Dag</th><th>Klokkeslett</th>
  </tr>
  {rows}
</table>
<p>👉 <a href="{booking_url}">Book her!</a></p>
</body></html>"""

    return text_body, html_body


def send_email(slots: list[tuple[str, str, str]]) -> None:
    """Send an email notification with the available slots."""
    if not EMAIL_FROM or not EMAIL_PASSWORD:
        print(
            "\n⚠️  E-post ikke sendt – mangler VIELSE_EMAIL_FROM / "
            "VIELSE_EMAIL_PASSWORD miljøvariabler."
        )
        print("   Sett dem slik:")
        print('     export VIELSE_EMAIL_FROM="din-epost@gmail.com"')
        print('     export VIELSE_EMAIL_PASSWORD="xxxx xxxx xxxx xxxx"')
        print("   (Bruk en Gmail App Password, ikke vanlig passord.)")
        return

    text_body, html_body = build_email_body(slots)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"💍 {len(slots)} ledig(e) vielsestid(er) hos Oslo kommune!"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Try with spaces first, then without (Gmail accepts both)
    passwords_to_try = [EMAIL_PASSWORD.strip(), EMAIL_PASSWORD.replace(" ", "")]

    for pw in passwords_to_try:
        try:
            if SMTP_PORT == 465:
                with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                    server.login(EMAIL_FROM, pw)
                    server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
            else:
                with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                    server.starttls()
                    server.login(EMAIL_FROM, pw)
                    server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
            print(f"\n📧 E-post sendt til {EMAIL_TO}!")
            return
        except smtplib.SMTPAuthenticationError:
            continue  # try next password variant
        except Exception as e:
            print(f"\n❌ Kunne ikke sende e-post: {e}")
            return

    print(f"\n❌ Kunne ikke logge inn – sjekk at App Password er riktig.")
    print(f"   E-post: {EMAIL_FROM}")
    print(f"   Passord (lengde): {len(EMAIL_PASSWORD)} tegn")


def send_macos_notification(slots: list[tuple[str, str, str]]) -> None:
    """Show a macOS notification as a fallback."""
    n = len(slots)
    title = f"💍 {n} ledig(e) vielsestid(er)!"
    first_date, first_time, first_day = slots[0]
    if n == 1:
        body = f"{first_day} {first_date} kl. {first_time}"
    else:
        body = f"Første: {first_day} {first_date} kl. {first_time} (+{n-1} til)"
    body += "\nÅpne booking.oslo.kommune.no for å booke!"
    script = (
        f'display notification "{body}" with title "{title}" '
        f'sound name "Glass"'
    )
    try:
        subprocess.run(["osascript", "-e", script], check=True)
        print("🔔 macOS-varsel vist!")
    except Exception:
        pass


if __name__ == "__main__":
    slots = check_availability()
    if slots:
        send_macos_notification(slots)
        send_email(slots)
    sys.exit(0 if slots else 1)
