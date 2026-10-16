# chmod calculator

[![CI](https://github.com/Hennashakil/chmod-calculator/actions/workflows/ci.yml/badge.svg)](https://github.com/Hennashakil/chmod-calculator/actions/workflows/ci.yml)

**Live:** [chmod-calculator-59m0.onrender.com](https://chmod-calculator-59m0.onrender.com) (Python) and [chmod-calculator-1.onrender.com](https://chmod-calculator-1.onrender.com) (Docker)

Type a Linux permission mode such as `750` or `rwxr-x---` and see, in plain English, what the owner, the group and everyone else can do, plus security red flags like `777` or setuid.

A small Flask web app with a JSON API. It only reads what you type; it never touches the server's files.

Made for beginners too: the page starts with a 30-second guide (owner, group and everyone else; r, w and x; why 7 = 4 + 2 + 1), and every answer shows each person's three switches as yes or no, with the sum that makes their digit.

## Use it

- **Web page:** enter a mode, or try a preset (644, 755, 1777, 4755 ...)
- **API:** `GET /api/mode/<mode>` returns JSON; bad input returns status 400

```bash
curl https://chmod-calculator-59m0.onrender.com/api/mode/4755
```

```json
{
  "octal": "4755",
  "symbolic": "rwsr-xr-x",
  "chmod_symbolic": "chmod u=rwxs,g=rx,o=rx FILE",
  "special": ["setuid"],
  "warnings": [{"level": "danger", "text": "setuid: the program runs with its owner's rights. ..."}]
}
```

## Run it locally

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
flask --app app run            # http://127.0.0.1:5000
```

Run the tests with `pip install pytest && pytest`.

## Deploy

On Render (free web service):

| Setting | Value |
|---|---|
| Runtime | Python 3 |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn app:app` |
| Health check path | `/healthz` |

### With Docker

```bash
sudo docker build -t chmod-calculator .
sudo docker run --rm -p 8080:10000 chmod-calculator    # http://localhost:8080
```

The image installs only what `requirements.txt` lists, copies only the app code, and runs as a non-root user. On Render, choose **Docker** as the language and it builds from the `Dockerfile`.

## Security notes

- Input is validated with strict patterns (3–4 octal digits or 9 permission letters, max 12 characters)
- No file system or shell access anywhere in the code
- Templates auto-escape output; responses send `Content-Security-Policy`, `X-Frame-Options` and `nosniff` headers, and the page runs no JavaScript

Related project: [whycant](https://github.com/Hennashakil/whycant), which explains why a real path gives "Permission denied".

## License

MIT
