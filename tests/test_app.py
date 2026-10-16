import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest
from app import app
from modes import ModeError, explain, parse


@pytest.mark.parametrize("text,expected", [
    ("750", "rwxr-x---"), ("644", "rw-r--r--"), ("0755", "rwxr-xr-x"),
    ("4755", "rwsr-xr-x"), ("1777", "rwxrwxrwt"), ("2750", "rwxr-s---"),
    ("4644", "rwSr--r--"), ("rwxr-x---", "rwxr-x---"), ("-rw-r--r--", "rw-r--r--"),
    ("drwxrwxrwt", "rwxrwxrwt"),
])
def test_symbolic(text, expected):
    assert explain(text)["symbolic"] == expected


@pytest.mark.parametrize("text,octal", [("rwsr-xr-x", "4755"), ("rwxrwxrwt", "1777"), ("rw-r--r--", "644")])
def test_round_trip(text, octal):
    assert explain(text)["octal"] == octal


@pytest.mark.parametrize("bad", ["", "8", "75", "7777x", "999", "rwxrwxrwz", "rm -rf /", "$(id)", "x" * 50, "../../etc/passwd"])
def test_rejects_bad_input(bad):
    with pytest.raises(ModeError):
        parse(bad)


def levels(mode):
    return [w["level"] for w in explain(mode)["warnings"]]


def test_warnings():
    assert "danger" in levels("777")
    assert "danger" in levels("666")
    assert "danger" in levels("4755")
    assert "info" in levels("1777")
    assert "warn" in levels("070")          # owner locked out
    assert levels("644") == ["ok"]
    assert levels("750") == ["ok"]


def test_chmod_commands():
    r = explain("750")
    assert r["chmod_octal"] == "chmod 750 FILE"
    assert r["chmod_symbolic"] == "chmod u=rwx,g=rx,o= FILE"
    assert explain("4755")["chmod_symbolic"] == "chmod u=rwxs,g=rx,o=rx FILE"
    assert explain("1777")["chmod_symbolic"] == "chmod u=rwx,g=rwx,o=rwxt FILE"


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_pages(client):
    r = client.get("/")
    assert r.status_code == 200 and b"rwxr-x---" in r.data
    assert r.headers["X-Frame-Options"] == "DENY"
    r = client.get("/?mode=<script>alert(1)</script>")
    assert r.status_code == 200 and b"<script>alert(1)" not in r.data
    assert client.get("/healthz").get_json() == {"status": "ok"}


def test_api(client):
    r = client.get("/api/mode/4755")
    assert r.status_code == 200 and r.get_json()["symbolic"] == "rwsr-xr-x"
    r = client.get("/api/mode/nope")
    assert r.status_code == 400 and "error" in r.get_json()


def test_cors_only_for_my_site(client):
    r = client.get("/api/mode/750", headers={"Origin": "https://hennashakil.github.io"})
    assert r.headers["Access-Control-Allow-Origin"] == "https://hennashakil.github.io"
    assert "Origin" in r.headers["Vary"]
    r = client.get("/api/mode/750", headers={"Origin": "https://evil.example"})
    assert "Access-Control-Allow-Origin" not in r.headers
    r = client.get("/", headers={"Origin": "https://hennashakil.github.io"})
    assert "Access-Control-Allow-Origin" not in r.headers


def test_beginner_breakdown():
    owner, group, other = explain("750")["classes"]
    assert (owner["label"], owner["sum"]) == ("Owner", "4 + 2 + 1 = 7")
    assert (group["label"], group["sum"]) == ("Group", "4 + 1 = 5")
    assert (other["label"], other["sum"]) == ("Everyone else", "0, every switch off")
    assert [s["on"] for s in group["switches"]] == [True, False, True]
    assert [s["meaning"] for s in owner["switches"]] == ["read", "change", "run"]
    assert explain("640")["classes"][1]["sum"] == "4"


def test_page_explains_the_basics(client):
    r = client.get("/?mode=4755")
    page = r.data.decode()
    assert "New to Linux permissions?" in page
    assert page.count('class="person') == 3
    assert "Number: 4 + 2 + 1 = 7" in page
    assert "special switch" in page          # s in place of x is explained
    assert "special switch" not in client.get("/?mode=750").data.decode()
