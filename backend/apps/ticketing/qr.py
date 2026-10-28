import io

import segno


def ticket_qr(token: str) -> segno.QRCode:
    """QR code holding only the ticket token (RN-26): no personal data, no ids.

    `make_qr` always builds a regular QR code; `segno.make` may pick a Micro QR for short
    data, which many phone scanners cannot read.
    """
    return segno.make_qr(token, error="m")


def ticket_qr_svg(token: str) -> bytes:
    """Black on white with the standard quiet zone, so it scans even with low brightness."""
    buffer = io.BytesIO()
    ticket_qr(token).save(
        buffer, kind="svg", scale=10, border=4, dark="#000", light="#fff", xmldecl=False
    )
    return buffer.getvalue()
