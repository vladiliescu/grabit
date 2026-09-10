from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest


@pytest.fixture
def image_server(tmp_path):
    directory = tmp_path / "http"
    directory.mkdir()
    image_bytes = (Path(__file__).parent / "fixtures" / "outlive.jpg").read_bytes()
    for filename in ("photo.JPEG", "converted.png", "banner"):
        (directory / filename).write_bytes(image_bytes)
    received_requests = []

    class Handler(SimpleHTTPRequestHandler):
        # A CDN can return JPEG content even when its URL ends in .png.
        extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".png": "image/jpeg"}

        def do_GET(self):
            received_requests.append(self.path)
            super().do_GET()

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(directory)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", directory, received_requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
