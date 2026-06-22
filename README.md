# PRISM™ Protein Intelligence Suite

**Protein Rational Intelligence & Structural Modeling Suite** — a computational platform for biophysical characterisation of protein sequences. PRISM computes molecular weight, isoelectric point, grand average of hydropathicity (GRAVY), aromaticity, instability index, secondary structure fractions, and molar extinction coefficients from a user-provided amino acid sequence. Results are interpreted through a drug-target strategy lens, with electrostatic complementarity analysis and conformational stability assessment.

Built for medicinal chemists, structural biologists, and bioinformaticians in early-stage drug discovery workflows.

---

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Maintenance Guide — Adding New Descriptors](#maintenance-guide--adding-new-descriptors)
- [Database Backup](#database-backup)
- [License](#license)

---

## Installation

### Prerequisites

- Python 3.11 or later
- pip (Python package manager)

### Clone & Setup

```bash
git clone <repository-url>
cd PRISM_Protein_Intelligence_Suite
```

### Create a Virtual Environment (Recommended)

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment

```bash
cp .env.example .env
```

Edit `.env` to set a secure `SECRET_KEY` and optionally adjust `FLASK_PORT`, `FLASK_DEBUG`, or `DATABASE_URL`.

---

## Usage

Start the application:

```bash
python app.py
```

Navigate to [http://localhost:5000](http://localhost:5000) in your browser.

1. **Register** an account or log in.
2. **Enter** a protein amino-acid sequence (single-letter codes) in the input field. Optionally provide a PDB ID for 3D visualisation.
3. **Analyse** — the engine returns a comprehensive biophysical report including a KPI dashboard, secondary structure prediction, amino-acid group distribution, drug-target strategy classification, electrostatic complementarity, and structural stability assessment.
4. **Export** results as PDF or CSV via the Research Toolbox.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | Flask 3.x (Python) |
| Biophysical computation | Biopython (`Bio.SeqUtils.ProtParam`) |
| Templating | Jinja2 |
| Database | SQLite3 |
| PDF generation | FPDF |
| Frontend | HTML5, CSS3 (custom properties, CSS Grid, Flexbox), Vanilla JavaScript |
| 3D visualisation | PDBe Molstar |
| i18n | Custom JSON-based translation engine (English, Hungarian) |

---

## Project Structure

```
.
├── app.py                 # Flask application factory & entry point
├── bio_engine.py          # Core biophysical analysis (Biopython)
├── analysis.py            # Analysis routes, PDF/CSV export
├── db.py                  # SQLite database operations
├── i18n.py                # Internationalisation engine
├── auth.py                # User registration / authentication
├── config.py              # Configuration (env vars)
├── api.py                 # REST API endpoints
├── main.py                # Landing page & language routes
├── translations/          # JSON translation files (en.json, hu.json)
├── templates/             # Jinja2 templates (index.html, landing.html, auth.html)
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
└── .gitignore
```

---

## Maintenance Guide — Adding New Descriptors

PRISM's modular architecture allows new physicochemical descriptors to be integrated without altering existing logic. Follow these four steps:

### 1. Extend the Computation (`bio_engine.py`)

The `advanced_biophysical_analysis()` function returns a dictionary consumed by the front end. The `ProteinAnalysis` object exposes several additional methods. For example, to add a **flexibility** score:

```python
# After the existing analysis block:
flexibility = analysis.flexibility()

return {
    # ... existing keys remain untouched ...
    "flexibility": round(flexibility, 2),
}
```

Available `ProteinAnalysis` methods include:
- `flexibility()` — mean flexibility along the chain
- `isoelectric_point()` — already in use
- `instability_index()` — already in use
- `charge_at_pH(pH)` — net charge at a given pH
- `amino_acids_percent` — already in use (dictionary)

### 2. Add Translation Keys (optional)

If the new descriptor requires a natural-language description, add the corresponding key to each `translations/*.json` file:

```json
{
    "flexibility_label": "Mean Chain Flexibility",
    "flexibility_desc": "The protein exhibits {flex} mean flexibility, suggesting {interpretation}."
}
```

### 3. Wire the Translation (`analysis.py`)

For dynamic strings containing runtime values (e.g. `{flex}`), pre-substitute using the i18n engine, mirroring the existing pattern for `charge_info_text` and `stability_info_text`:

```python
results['flexibility_text'] = i18n.translate(
    "flexibility_desc",
    flex=results['flexibility']
)
```

### 4. Display in the Template (`templates/index.html`)

Add a new KPI box in the `.kpi-grid` or a new card inside the `.bio-container`:

```html
<div class="kpi-box">
    <div class="kpi-label">{{ _('flexibility_label') }}</div>
    <div class="kpi-value">{{ results.flexibility }}</div>
</div>
```

### Design Guarantees

- **No regression.** The results dictionary is extended, not modified — every consumer that reads existing keys continues to work unchanged.
- **Database isolation.** `db.py::save_entry()` persists only the columns it knows about. New fields do not appear in SQLite until explicitly added via an `ALTER TABLE` migration.
- **Template isolation.** All rendering occurs within `{% if results and not results.error %}`, so partial data cannot be displayed.

---

## Database Backup

The entire user dataset resides in a single SQLite file (`database.db` by default).

### Manual Snapshot (zero-downtime)

```bash
mkdir -p backup
cp database.db backup/$(date +%Y%m%d_%H%M%S)_database.db
```

SQLite's single-writer model guarantees that `cp` either captures a fully committed state or fails — no file corruption.

### Automated (cron)

```cron
0 3 * * * cp /path/to/database.db /path/to/backup/$(date +\%Y\%m\%d)_database.db
```

### Restore

```bash
cp backup/20260622_database.db database.db
python app.py
```

For strict consistency, stop the server before copying (introduces < 1 s downtime):

```bash
systemctl stop prism && cp database.db backup/ && systemctl start prism
```

---

## License

All rights reserved. PRISM™ is a trademark of the project maintainer. This software is provided for evaluation and internal research use. Redistribution or commercial use requires prior written consent.
