# AI Usage Record

## AI tools used

- **ChatGPT / Copilot coding assistant** — used during planning, debugging,
  implementation, and verification of this Django project.
- **Google Gemini API (Google AI Studio key)** — integrated as the language
  model that selects a shipping box from the application's eligible database
  boxes. The API key is stored in the local `.env` file and is not included in
  this document.

## Original project prompt

The following was the project brief provided to the AI assistant:

> We operate an ecommerce platform. When a customer places an order, the
> warehouse team needs to know which shipping box should be used. Each product
> has dimensions and weight. Each box has internal dimensions, maximum weight
> capacity, and cost.
>
> Your task is to design and build a small Django-based system that recommends
> the most suitable box for an order.
>
> i am making a AI based software which will assist the user which Length
> breadh and height box to select according to item dimension that to be packed,
> for this i am using a LLM(gemini) i will connect it using API this will
> recommend the box
>
> feature I want in this project is
>
> 1 user can save the different box of different dimension in database
> 2 when user give dimension of item then our software should recommend the
> which one to be used to pack that item and that box should be from our
> database box
> 3 gemini should recommend which box to be selected of which dimension
>
> assist me to build this by giving a efficient code i using django framework
> to built this so lets start building thi

## Prompts and assistance requested

During development, the user asked the assistant to:

- Diagnose why the Gemini API recommendation was returning a fallback.
- Check whether the Google AI Studio API key setup and the
  `client.interactions.create(...)` example worked.
- Investigate why all recommendations returned a fallback, explain the
  problem, and ask before making changes.

## Accepted outputs and implementation decisions

- The system validates item dimensions, weight, box activity, physical fit
  across orientations, and weight capacity in Python before asking Gemini to
  choose. The model receives only eligible boxes; its selected ID is checked
  against that eligible set.
- Gemini credentials are read from `.env` through Django settings rather than
  being embedded in application source.
- A deterministic fallback remains available when Gemini is not configured,
  unavailable, or returns invalid output.
- Following the project-wide fix request, the recommendation service was
  updated to call `client.interactions.create(...)`, request JSON constrained
  by a response schema, retry temporary HTTP 429/5xx errors, and log failures.
- Automated tests were added for recommendation eligibility and fallback,
  transient-error retry, invalid model-selected IDs, API request handling,
  and box-management pages.
- Project setup and environment configuration were documented in
  `README.md` and `.env.example`; test results were recorded in
  `Test_output.md`.

## Rejected, reverted, or superseded outputs

- The assistant first suggested keeping `models.generate_content(...)` and
  improving error visibility/retries. That approach was superseded after the
  user asked to use the working Interactions API example.
- After an Interactions API implementation, the user asked to abort all changes.
  The assistant reverted that specific change set. The user later requested a
  project-wide fix, after which the Interactions implementation and related
  tests were added again as part of that new request.
- A proposed exact Gemini recommendation for a sample item was not treated as
  guaranteed: the model can choose differently, and a fallback can be
  returned when the external service is unavailable.

## Mistakes and issues identified

- The recommendation service initially used `models.generate_content(...)`
  while the user was testing the newer Interactions API pattern.
- A broad exception handler hid the underlying Gemini exception and made
  service errors appear only as a generic fallback.
- A live `generate_content` request returned HTTP 503 because of temporary
  high model demand.
- The first live Interactions recommendation attempt did not provide a
  machine-enforced JSON response format; an invalid/non-JSON response caused
  JSON parsing to fail and the service to fall back. The implementation was
  updated to request schema-constrained JSON and still validates the result.
- Another live request later failed before reaching Google due to a local
  DNS/network error (`getaddrinfo failed`). This is an external connectivity
  issue; no application change can guarantee Gemini availability.
- Initial deployment checks exposed unsafe default Django settings, including
  a hard-coded development secret key, debug mode, empty allowed hosts, and
  development-only email configuration. Settings were made environment-driven.

## Verification performed

The following checks were run after the project updates:

- `python manage.py check` — passed with no issues.
- `python manage.py test` — all 10 automated tests passed.
- `python manage.py makemigrations --check --dry-run` — no model changes
  requiring migrations.
- `python -m pip check` — no broken installed dependencies.
- `python manage.py check --deploy` — passed with production-like environment
  values, including a generated strong secret, host configuration, HTTPS, and
  explicit HSTS choices.
- Live Gemini recommendation — one request succeeded with `source: gemini`
  and selected an eligible database box. A later attempt was blocked by DNS
  resolution failure and returned the fallback.
- The example item `10 × 8 × 6 cm`, weight `4 kg`, matched five eligible boxes
  in the local database. That eligibility result is deterministic; Gemini's
  final choice and explanation are not guaranteed to be identical on every
  request.

## Limitations

Gemini depends on Google API availability, model access, free-tier quotas, and
network connectivity. The application can validate fit and use a local
fallback, but it cannot guarantee that the external model will always be
reachable or return the same choice.
