from pathlib import Path
from shutil import copytree

import pytest

from policyguard.config import APP_ROOT, REPO_ROOT
from policyguard.ingest import IndexValidationError, build_index, validate_index
from policyguard.retrieval import BM25Retriever, tokenize


def _retriever() -> BM25Retriever:
    return BM25Retriever.from_index(APP_ROOT / "data" / "index", default_top_k=15)


def test_tokenizer_keeps_codes_dates_and_section_numbers() -> None:
    tokens = tokenize("WELCOME10 on 2027-02-01 under Section 4.3 and COD")

    assert "welcome10" in tokens
    assert "2027-02-01" in tokens
    assert "4.3" in tokens
    assert "cod" in tokens


def test_shipping_fee_query_surfaces_fee_schedule() -> None:
    results = _retriever().search("What is the shipping fee for Metro cities?")
    ids = {result.chunk.chunk_id for result in results}

    assert "06_shipping_fees_and_free_shipping:1.1" in ids
    assert all("Instruction for assistants" not in result.chunk.text for result in results)


def test_cod_limit_query_surfaces_both_conflicting_sources() -> None:
    results = _retriever().search("What is the maximum cash on delivery order amount?")
    ids = {result.chunk.chunk_id for result in results}

    assert "10_payments:3.2" in ids
    assert "11_cod_and_failed_payments:1.2" in ids


def test_warranty_query_surfaces_electronics_period() -> None:
    results = _retriever().search("How long is the electronics warranty?")
    ids = {result.chunk.chunk_id for result in results}

    assert "08_warranty_policy:2.1" in ids


def test_committed_index_validates_against_corpus() -> None:
    manifest = validate_index(REPO_ROOT / "policies", APP_ROOT / "data" / "index")

    assert manifest.document_count == 22
    assert manifest.chunk_count == 270


def test_validation_rejects_changed_corpus(tmp_path: Path) -> None:
    policies = tmp_path / "policies"
    copytree(REPO_ROOT / "policies", policies)
    index = tmp_path / "index"
    build_index(policies, index)

    target = policies / "00_how_policies_work_together.md"
    target.write_text(target.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")

    with pytest.raises(IndexValidationError, match="changed"):
        validate_index(policies, index)


@pytest.mark.parametrize("initial_newline", [b"\n", b"\r\n"])
def test_index_validates_after_checkout_line_endings_change(
    tmp_path: Path, initial_newline: bytes
) -> None:
    policies = tmp_path / "policies"
    copytree(REPO_ROOT / "policies", policies)
    for path in policies.glob("*.md"):
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", initial_newline))
    index = tmp_path / "index"
    original = build_index(policies, index)

    other_newline = b"\r\n" if initial_newline == b"\n" else b"\n"
    for path in policies.glob("*.md"):
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", other_newline))

    assert validate_index(policies, index).corpus_hash == original.corpus_hash
    rebuilt = build_index(policies, tmp_path / "rebuilt")
    assert [doc.checksum for doc in rebuilt.documents] == [
        doc.checksum for doc in original.documents
    ]
