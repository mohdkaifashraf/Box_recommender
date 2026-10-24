# Test Output

Results recorded on 2026-10-24 after rerunning the project checks.

## Django system check

Command:

```text
python manage.py check
```

Output:

```text
System check identified no issues (0 silenced).
```

## Automated test suite

Command:

```text
python manage.py test
```

Output:

```text
Creating test database for alias 'default'...
..........
----------------------------------------------------------------------
Ran 10 tests in 0.146s

OK
Destroying test database for alias 'default'...
Found 10 test(s).
System check identified no issues (0 silenced).
```

The tests cover Gemini retry/selection, fallback behavior, no eligible boxes,
rejecting an ineligible Gemini selection, API responses and errors, HTTP
method restrictions, and the dashboard, inventory, and box-management pages.

## Migration consistency

Command:

```text
python manage.py makemigrations --check --dry-run
```

Output:

```text
No changes detected
```

## Dependency consistency

Command:

```text
python -m pip check
```

Output:

```text
No broken requirements found.
```

## Inventory eligibility example

Input: item dimensions `10 × 8 × 6 cm`, weight `4 kg`.

```text
item: 10 x 8 x 6 cm; weight: 4 kg
eligible_count: 5
id=5; name=Half Pallet; dimensions=24.00 x 16.00 x 12.00 cm; max_weight=10.00 kg; cost=5.00
id=2; name=Medium Mailer; dimensions=12.00 x 8.00 x 6.00 cm; max_weight=6.00 kg; cost=6.00
id=3; name=Large Mailer; dimensions=16.00 x 12.00 x 8.00 cm; max_weight=10.00 kg; cost=10.00
id=4; name=Pizza Box Standard; dimensions=24.00 x 16.00 x 12.00 cm; max_weight=8.00 kg; cost=10.00
id=6; name=Standard Export; dimensions=24.00 x 16.00 x 16.00 cm; max_weight=20.00 kg; cost=10.00
```

This reports eligible inventory only; it does not imply which box Gemini will
choose on a later request.

## Live Gemini request status

A previous live request through the recommendation service succeeded with
`source: gemini`. The most recent live request could not reach Google's API
because DNS resolution failed (`getaddrinfo failed`), so it returned the
configured fallback. The automated suite does not depend on Google's
availability or network access.
