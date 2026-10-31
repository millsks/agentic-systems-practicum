import threading
import urllib.request
from pathlib import Path

import pytest

from practicum import serve as serve_module
from practicum.serve import make_server, serve

pytestmark = pytest.mark.integration


def test_server_serves_site_files(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<title>hi</title>", encoding="utf-8")
    (tmp_path / "app.mjs").write_text("export {}", encoding="utf-8")
    with make_server(tmp_path, "127.0.0.1", 0) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as response:
            assert response.read() == b"<title>hi</title>"
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/app.mjs") as response:
            assert response.headers["Content-Type"].startswith("text/javascript")
        server.shutdown()
        thread.join(timeout=5)


def test_serve_opens_browser_and_stops(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(serve_module.webbrowser, "open", opened.append)

    def stop_immediately(self: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(serve_module.ThreadingHTTPServer, "serve_forever", stop_immediately)
    with pytest.raises(KeyboardInterrupt):
        serve(tmp_path, port=0)
    assert opened and opened[0].startswith("http://127.0.0.1:")
