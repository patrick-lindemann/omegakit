from omegakit._core.utils.notes import add_note


def test_notes_are_kept_in_order():
    error = ValueError("broken")
    add_note(error, "first")
    add_note(error, "second")
    assert error.__notes__ == ["first", "second"]  # ty: ignore[unresolved-attribute]
