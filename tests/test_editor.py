import pytest
from pathlib import Path
from flux_studio.app import FluxStudioApp
from flux_studio.editor.markdown_editor import MarkdownEditor

@pytest.mark.asyncio
async def test_editor_new_file():
    app = FluxStudioApp()
    async with app.run_test() as pilot:
        editor = app.query_one(MarkdownEditor)

        # Verify initial state
        assert editor.text_area.text == ""
        assert editor.current_file is None

        # Simulate typing
        await pilot.click(editor.text_area)
        await pilot.press("h", "e", "l", "l", "o")

        assert editor.text_area.text == "hello"
        assert editor.is_modified

        # Trigger new file
        await pilot.press("ctrl+n")

        assert editor.text_area.text == ""
        assert editor.current_file is None
        assert not editor.is_modified

@pytest.mark.asyncio
async def test_editor_save_load(tmp_path):
    app = FluxStudioApp()
    test_file = tmp_path / "test.md"

    async with app.run_test() as pilot:
        editor = app.query_one(MarkdownEditor)

        # Write content
        editor.text_area.text = "# Hello World"

        # Save file directly (bypassing UI for testing logic)
        await editor.save_file(test_file)

        assert test_file.exists()
        assert test_file.read_text() == "# Hello World"
        assert editor.current_file == test_file
        assert not editor.is_modified

        # Clear
        editor.new_file()
        assert editor.text_area.text == ""

        # Load file directly
        await editor.load_file(test_file)
        assert editor.text_area.text == "# Hello World"
        assert editor.current_file == test_file

@pytest.mark.asyncio
async def test_autosave(tmp_path):
    # Setup autosave to a temp dir
    backups_dir = tmp_path / "backups"

    app = FluxStudioApp()
    async with app.run_test() as pilot:
        editor = app.query_one(MarkdownEditor)
        # Point autosave manager to temp dir
        editor.autosave_manager.storage_dir = backups_dir
        editor.autosave_manager._ensure_storage()

        # Set a current file so autosave triggers
        test_file = tmp_path / "original.md"
        editor.current_file = test_file

        # Type something to trigger autosave
        # Note: In the actual code, we run_worker, which might be async.
        # run_test pilot usually handles awaiting tasks but we might need to wait.

        editor.text_area.text = "content"
        # Manually trigger the changed handler logic if needed, but modifying text property
        # doesn't always trigger events in tests same as typing unless we use pilot.
        # But let's call the autosave logic directly to verify the manager.

        await editor.autosave_manager.create_backup("content", test_file)

        # We need to compute the expected backup path using the same logic
        backup_path = editor.autosave_manager.get_backup_path(test_file)

        assert backup_path.exists()
        assert backup_path.read_text() == "content"
