from docpulse.repair.validator import preservation_ratio


def test_identical_text_is_fully_preserved():
    text = "Para one.\n\nPara two.\n\nPara three."
    assert preservation_ratio(text, text) == 1.0


def test_one_changed_block_of_three():
    original = "Keep A.\n\nChange B.\n\nKeep C."
    new = "Keep A.\n\nChanged B entirely.\n\nKeep C."
    assert preservation_ratio(original, new) == 2 / 3


def test_empty_original_is_fully_preserved():
    assert preservation_ratio("", "anything") == 1.0


def test_whitespace_only_separators_split_blocks():
    # A blank line containing spaces/tabs still separates paragraphs.
    original = "Block one.\n \t\nBlock two."
    new = "Block one.\n\nBlock two REWRITTEN."
    assert preservation_ratio(original, new) == 0.5


def test_byte_identical_required_trailing_space_differs():
    # A trailing space makes the block non-identical -> not preserved.
    original = "exact line"
    new = "exact line "
    assert preservation_ratio(original, new) == 0.0


def test_duplicate_blocks_counted_with_multiplicity():
    original = "dup\n\ndup\n\nunique"
    new = "dup\n\nunique"  # only one 'dup' survives
    assert preservation_ratio(original, new) == 2 / 3
