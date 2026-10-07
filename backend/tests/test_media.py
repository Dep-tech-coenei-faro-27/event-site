import pytest

from app.core.config import BASE_DIR, settings


@pytest.fixture
def media_file():
    created = []

    def create(name: str, content: bytes = b"This is a test image.") -> bytes:
        path = settings.MEDIA_DIR / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        created.append(path)
        return content

    yield create

    for path in created:
        path.unlink(missing_ok=True)
        if path.parent != settings.MEDIA_DIR:
            path.parent.rmdir()


def test_media_dir_does_not_depend_on_the_working_directory():
    assert settings.MEDIA_DIR == BASE_DIR / "media"
    assert settings.MEDIA_DIR.is_absolute()


def test_serve_media_file(client, media_file):
    content = media_file("test_image.png")

    response = client.get("/media/test_image.png")

    assert response.status_code == 200
    assert response.content == content


def test_media_files_are_served_with_safe_headers(client, media_file):
    media_file("test_image.png")

    response = client.get("/media/test_image.png")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-security-policy"] == "sandbox"
    assert response.headers["cache-control"] == "public, max-age=86400"


def test_media_extensions_are_case_insensitive(client, media_file):
    media_file("PHOTO.PNG")

    assert client.get("/media/PHOTO.PNG").status_code == 200


@pytest.mark.parametrize(
    "name", ["page.html", "image.svg", "script.js", "notes.txt", "no_extension"]
)
def test_files_that_are_not_images_are_not_served(client, media_file, name):
    media_file(name, b"<script>alert(1)</script>")

    assert client.get(f"/media/{name}").status_code == 404


@pytest.mark.parametrize("name", [".hidden.png", ".private/photo.png"])
def test_hidden_files_are_not_served(client, media_file, name):
    media_file(name)

    assert client.get(f"/media/{name}").status_code == 404


@pytest.mark.parametrize(
    "path", ["/media/", "/media/../pyproject.toml", "/media/%2e%2e/pyproject.toml"]
)
def test_directories_and_path_traversal_are_not_served(client, path):
    assert client.get(path).status_code == 404


def test_missing_media_file_returns_404(client):
    assert client.get("/media/missing.png").status_code == 404
