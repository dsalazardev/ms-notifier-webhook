from src.core.config import settings
from src.services.email_service import LEAD_SUBJECT, build_lead_message

PDF_BYTES = b"%PDF-1.7 contenido"
NEED = "modernizar legacy"


def _message():
    return build_lead_message("lead@example.com", NEED, PDF_BYTES)


def test_message_is_multipart_with_essential_info():
    content = _message()["content"]
    assert "html" in content and "plainText" in content
    for body in (content["html"], content["plainText"]):
        assert NEED in body
        assert "Checklist-27-puntos-SALAZAR-Eng.pdf" in body
        assert settings.BOOKING_URL in body
        assert "no recibe respuestas" in body
        assert "SALAZAR Eng." in body


def test_subject_is_branded():
    assert _message()["content"]["subject"] == LEAD_SUBJECT
    assert LEAD_SUBJECT == "Tu checklist: 27 puntos para modernizar tu sistema legacy"


def test_html_has_brand_identity():
    html = _message()["content"]["html"]
    assert "#0B2545" in html
    assert "#1D4ED8" in html
    assert "#F8FAFC" in html
    assert "SALAZAR ENG. · RECURSO GRATUITO" in html
    assert "Agenda tu diagnóstico · 20 min" in html
    assert "— SALAZAR Eng. · Software &amp; Applied AI" in html


def test_html_monogram_by_url_with_alt_and_wordmark():
    html = _message()["content"]["html"]
    assert f'src="{settings.LEAD_EMAIL_LOGO_URL}"' in html
    assert 'alt="SALAZAR Eng."' in html
    assert 'width="72"' in html
    assert 'height="62"' in html
    assert ">SALAZAR Eng.<" in html


def test_html_footer_has_booking_and_whatsapp():
    html = _message()["content"]["html"]
    assert f'href="{settings.BOOKING_URL}"' in html
    assert f'href="{settings.LEAD_EMAIL_WHATSAPP_URL}"' in html
    assert "wa.me/573145919465" in html
    assert "no recibe respuestas" in html


def test_html_has_no_forbidden_constructs():
    html = _message()["content"]["html"]
    assert "<script" not in html.lower()
    assert "data:" not in html
    assert "@font-face" not in html
    assert "cid:" not in html
    assert "display:flex" not in html
    assert "display:grid" not in html


def test_html_uses_table_layout():
    html = _message()["content"]["html"]
    assert 'role="presentation"' in html
    assert 'width="600"' in html


def test_html_size_budget():
    html = _message()["content"]["html"]
    assert len(html.encode("utf-8")) < 50 * 1024


def test_message_has_no_reply_to():
    assert "replyTo" not in _message()


def test_plain_text_is_self_sufficient():
    text = _message()["content"]["plainText"]
    assert NEED in text
    assert "Checklist-27-puntos-SALAZAR-Eng.pdf" in text
    assert settings.BOOKING_URL in text
    assert settings.LEAD_EMAIL_WHATSAPP_URL in text
    assert "— SALAZAR Eng. · Software & Applied AI" in text
    assert "no recibe respuestas" in text
