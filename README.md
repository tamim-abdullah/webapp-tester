# Web App Tester

Automated functional + performance tester for LMS platforms using Playwright. Logs in, discovers pages, runs tests, and outputs a JSON report.

## Requirements

```bash
pip install playwright
playwright install chromium
```

## Usage

```bash
python3 webapp_tester.py --url https://yoursite.com --email youradmin@mail --password yourpassword
```


## What It Tests

| Test          | Description                                                |
| ------------- | ---------------------------------------------------------- |
| Login         | Fills credentials, handles cookie banners, checks redirect |
| Dashboard     | Verifies stats content loads                               |
| Nav Links     | Checks all nav links return 200                            |
| Search        | Submits a query, counts results                            |
| Create Course | Clicks button, checks form opens                           |
| Notifications | Clicks bell, checks panel appears                          |
| Profile Menu  | Opens user menu                                            |
| Page Loads    | Checks every discovered page for HTTP errors               |
| Performance   | Flags pages slower than 3 seconds                          |
| Logout        | Verifies session ends properly                             |

## Output

Results saved to `test_results.json`:

```json
{
  "total": 32,
  "passed": 27,
  "failed": 0,
  "warnings": 5,
  "pass_rate": "84%",
  "results": [...]
}
```

## Debug Mode

Set `HEADLESS = False` in the script to watch the browser live.

## Tested On

- IQRA LMS (iqralms.com)
- Playwright 1.x + Python 3.10+