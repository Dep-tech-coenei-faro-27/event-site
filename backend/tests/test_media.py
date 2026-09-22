from pathlib import Path


def test_serve_media_file(client):
    media_dir = Path("media")
    media_dir.mkdir(parents=True, exist_ok=True)

    test_file = media_dir / "test_image.txt"
    test_content = b"This is a test image."
    test_file.write_bytes(test_content)

    try:
        response = client.get("/media/test_image.txt")
        assert response.status_code == 200
        assert response.content == test_content
    finally:
        if test_file.exists():
            test_file.unlink()
