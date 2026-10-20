"""Unit tests for HDC bitwise code similarity indexing."""

from local_coder.knowledge.hdc_code_index import HDCCodeIndex


def test_should_index_and_retrieve_semantically_similar_code() -> None:
    # Arrange
    index = HDCCodeIndex(dimension=10240)
    index.add_symbol(
        symbol_id="auth.py:verify_jwt",
        file_path="auth.py",
        symbol_type="function",
        code_snippet="def verify_jwt(token: str) -> bool:\n    return decode_token(token)",
    )
    index.add_symbol(
        symbol_id="db.py:connect_db",
        file_path="db.py",
        symbol_type="function",
        code_snippet="def connect_db(uri: str) -> Connection:\n    return sqlite3.connect(uri)",
    )

    # Act
    hits = index.search("verify jwt authentication token", limit=2)

    # Assert
    assert len(hits) > 0
    top_hit = hits[0]
    assert top_hit.symbol_id == "auth.py:verify_jwt"
    assert top_hit.similarity > 0.05
