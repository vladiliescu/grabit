# Image regression fixtures

Captured on 2026-09-09 from the reported pages:

- `boring-table.html`: the first three table rows from https://boringtechnology.club/.
- `substack-image.html`: the first image link and picture from https://erictopol.substack.com/p/a-review-of-outlive.
- `outlive.jpg`: the JPEG response for that image's CDN URL. Its upstream filename ends in `.png`; the response is JPEG.

The HTTP tests serve the captured image bytes locally, including a `.png` URL with an `image/jpeg` response, to reproduce CDN format negotiation without mocking the downloader.
