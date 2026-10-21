from html.parser import HTMLParser

_BREAKS = {"br", "p", "div", "h1", "h2", "h3", "tr", "li"}
_SKIPPED = {"style", "head", "title"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0
        self._href: str | None = None
        self._link_text = ""

    def handle_starttag(self, tag, attrs) -> None:
        if tag in _SKIPPED:
            self._skip += 1
        elif tag in _BREAKS:
            self.parts.append("\n")
        elif tag == "a":
            self._href = dict(attrs).get("href")
            self._link_text = ""

    def handle_endtag(self, tag) -> None:
        if tag in _SKIPPED:
            self._skip = max(0, self._skip - 1)
        elif tag in _BREAKS:
            self.parts.append("\n")
        elif tag == "a":
            href, self._href = self._href, None
            if href and href.startswith(("http://", "https://")):
                if href != self._link_text.strip():
                    self.parts.append(f" ({href})")

    def handle_data(self, data) -> None:
        if self._skip:
            return
        self.parts.append(data)
        if self._href is not None:
            self._link_text += data


def html_to_text(html: str) -> str:
    """A plain-text version of an email body, for clients that do not show HTML.

    Links keep their address (``label (https://...)``) so nothing is lost.
    """
    extractor = _TextExtractor()
    extractor.feed(html)
    lines = [" ".join(line.split()) for line in "".join(extractor.parts).splitlines()]
    text = "\n".join(lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip() + "\n"
