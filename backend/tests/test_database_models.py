from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import (
    AppSetting,
    Attachment,
    Conversation,
    Message,
    Project,
    UsageLog,
)


def test_sqlite_foreign_keys_enabled(db_session: Session) -> None:
    result = db_session.execute(text("PRAGMA foreign_keys;")).scalar_one()
    assert result == 1


def test_project_conversation_message_relationships(db_session: Session) -> None:
    project = Project(
        name="Local Architecture",
        description="Core workspace design notes",
        instructions="Always keep answers concise and local-first.",
    )
    db_session.add(project)
    db_session.flush()

    conversation = Conversation(
        project_id=project.id,
        title="SQLite Migration Planning",
        provider_id="anthropic",
        model_name="claude-3-7-sonnet",
        system_prompt="You are a careful database architect.",
    )
    db_session.add(conversation)
    db_session.flush()

    msg_user = Message(
        conversation_id=conversation.id,
        role="user",
        content="Review our Alembic setup.",
        content_blocks=[{"type": "text", "text": "Review our Alembic setup."}],
    )
    msg_assistant = Message(
        conversation_id=conversation.id,
        role="assistant",
        content="Alembic batch mode is configured for SQLite.",
        tool_calls=[{"id": "call_1", "name": "inspect_schema", "arguments": {}}],
        model_name="claude-3-7-sonnet",
        provider_name="anthropic",
        token_usage={"input_tokens": 42, "output_tokens": 88},
    )
    db_session.add_all([msg_user, msg_assistant])

    attachment = Attachment(
        conversation_id=conversation.id,
        message_id=msg_user.id,
        project_id=project.id,
        original_filename="schema.sql",
        stored_filename="uuid_schema.sql",
        mime_type="text/plain",
        file_size=512,
        storage_path="storage/uploads/uuid_schema.sql",
    )
    usage = UsageLog(
        conversation_id=conversation.id,
        message_id=msg_assistant.id,
        provider_name="anthropic",
        model_name="claude-3-7-sonnet",
        input_tokens=42,
        output_tokens=88,
        estimated_cost=0.0012,
        request_status="success",
    )
    setting = AppSetting(setting_key="theme", setting_value="dark")

    db_session.add_all([attachment, usage, setting])
    db_session.commit()

    # Verify relationships
    loaded_project = db_session.get(Project, project.id)
    assert loaded_project is not None
    assert len(loaded_project.conversations) == 1
    assert loaded_project.conversations[0].title == "SQLite Migration Planning"
    assert len(loaded_project.conversations[0].messages) == 2
    assert loaded_project.conversations[0].messages[1].token_usage["output_tokens"] == 88

    # Deleting conversation cascades to messages, sets null on usage_logs & attachments
    db_session.delete(conversation)
    db_session.commit()
    db_session.expire_all()

    remaining_messages = db_session.execute(select(Message)).scalars().all()
    assert remaining_messages == []

    remaining_usage = db_session.execute(select(UsageLog)).scalars().all()
    assert len(remaining_usage) == 1
    assert remaining_usage[0].conversation_id is None
