# Box Recommender

A Django application for managing shipping boxes and recommending a box that
fits an item's dimensions and weight. Box fit and weight eligibility are
validated locally; Gemini selects from only the eligible boxes.

## Local setup (Windows PowerShell)

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` in `.env` to a Google AI Studio API key. Generate a Django
secret key with:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Put that value in `DJANGO_SECRET_KEY`. The development settings use
`DJANGO_DEBUG=true`; do not use the development defaults on a public deployment.

Initialize the database and start the development server:

```powershell
python manage.py migrate
python manage.py runserver
```

Open `Local host server`. Add active boxes in the inventory before asking
for a recommendation. The JSON API is `POST /api/recommend/` and accepts
`length`, `breadth`, `height` (cm), and `weight` (kg).

Run automated checks with:

```powershell
python manage.py check
python manage.py test
```
