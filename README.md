# 💍 Vielse-sjekk

Automatisk sjekk av ledige vielsestider hos Oslo kommune. Scriptet spør booking-API-et og sender e-post når det finnes ledige tider du kan booke.

## Oppsett

### 1. Klon og installer

```bash
git clone https://github.com/emedd33/vielse-script.git
cd vielse-script
python -m venv .venv
source .venv/bin/activate
pip install requests python-dotenv
```

### 2. Opprett `.env`

```
VIELSE_EMAIL_FROM=din-epost@gmail.com
VIELSE_EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
VIELSE_SMTP_SERVER=smtp.gmail.com
VIELSE_SMTP_PORT=465
```

> **NB:** Passordet må være en [Gmail App Password](https://myaccount.google.com/apppasswords), ikke ditt vanlige passord. Krever at 2-trinnsbekreftelse er aktivert.

### 3. Kjør lokalt

```bash
python main.py
```

## Konfigurasjon

Rediger øverst i `main.py`:

| Variabel     | Beskrivelse                                            |
| ------------ | ------------------------------------------------------ |
| `START_DATE` | Første dato å lete etter tider (default: 18. mai 2026) |
| `END_DATE`   | Siste dato å lete etter tider (default: 20. juni 2026) |
| `EMAIL_TO`   | E-postadressen som mottar varsler                      |

## GitHub Actions

Scriptet kjøres automatisk via GitHub Actions:

- **Kl. 07:00** og **21:00** norsk tid, hver dag
- Kan også kjøres manuelt fra [Actions-fanen](https://github.com/emedd33/vielse-script/actions)

### Secrets

Legg til i **Settings → Secrets and variables → Actions**:

- `VIELSE_EMAIL_FROM` — Gmail-adressen som sender
- `VIELSE_EMAIL_PASSWORD` — Gmail App Password
