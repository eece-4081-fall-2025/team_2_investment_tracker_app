# Investment Tracker (Team 2)

This Django project implements the **Core Investment Management MVP** for our Investment Tracking App.

## Features (MVP)
- Create, edit, and delete portfolios
- Add, edit, and delete investments within a portfolio
- Automatic calculation of amount invested and gain/loss
- Validation for positive quantity and purchase price

## Epics Implemented
| Epic | Description | Unit Tests |
|------|--------------|------------|
| 1 | Add Investment | `AddInvestmentTests` |
| 2 | Edit Investment | `EditInvestmentTests` |
| 3 | Delete Investment | `DeleteInvestmentTests` |

## Run Locally
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
