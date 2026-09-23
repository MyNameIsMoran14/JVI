from collections.abc import Callable
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.models import Document, DocumentStatus
from app.extraction import tasks as tasks_module
from tests.test_parse_document_task import _make_fixture_document, files_dir  # noqa: F401


async def test_parse_discharge_stores_text_and_notifies(
    session: AsyncSession,
    files_dir: Path,  # noqa: F811
    db_session_maker: Callable[[], AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document, _patient, _user = await _make_fixture_document(session, files_dir)

    async def fake_transcribe(image_b64: str) -> str:
        return "Пациент выписан в удовлетворительном состоянии.\nРекомендовано наблюдение гематолога."

    notifications: list[tuple] = []

    async def fake_notify(uploader, text, markup=None) -> None:  # noqa: ANN001
        notifications.append((uploader, text, markup))

    monkeypatch.setattr(tasks_module, "transcribe_image", fake_transcribe)
    monkeypatch.setattr(tasks_module, "_notify", fake_notify)
    monkeypatch.setattr(tasks_module, "async_session_maker", db_session_maker)

    await tasks_module.parse_discharge({}, document.id)

    async with db_session_maker() as verify_session:
        refreshed = await verify_session.get(Document, document.id)
        assert refreshed is not None
        assert refreshed.status == DocumentStatus.confirmed
        assert refreshed.raw_text is not None
        assert "гематолога" in refreshed.raw_text

    assert len(notifications) == 1
    assert "Распознал выписку" in notifications[0][1]


async def test_parse_discharge_marks_failed_on_error(
    session: AsyncSession,
    files_dir: Path,  # noqa: F811
    db_session_maker: Callable[[], AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document, _patient, _user = await _make_fixture_document(session, files_dir)

    async def failing_transcribe(image_b64: str) -> str:
        raise RuntimeError("boom")

    notifications: list[tuple] = []

    async def fake_notify(uploader, text, markup=None) -> None:  # noqa: ANN001
        notifications.append((uploader, text, markup))

    monkeypatch.setattr(tasks_module, "transcribe_image", failing_transcribe)
    monkeypatch.setattr(tasks_module, "_notify", fake_notify)
    monkeypatch.setattr(tasks_module, "async_session_maker", db_session_maker)

    await tasks_module.parse_discharge({}, document.id)

    async with db_session_maker() as verify_session:
        refreshed = await verify_session.get(Document, document.id)
        assert refreshed is not None
        assert refreshed.status == DocumentStatus.failed

    assert len(notifications) == 1
    assert "не получилось" in notifications[0][1].lower()
