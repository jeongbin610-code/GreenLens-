# -*- coding: utf-8 -*-
"""Load the GreenLens Policy FAISS index from Amazon S3.

Credentials are resolved by boto3's standard credential chain. Keep credential
values out of this file and out of GitHub.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path, PurePosixPath

import boto3
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings


DEFAULT_BUCKET = "est-7-policyrag"
DEFAULT_PREFIX = "policy/index/current"
DEFAULT_REGION = "ap-northeast-2"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def _setting(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    if not value:
        raise ValueError(f"{name} 값이 비어 있습니다.")
    return value


def _download_atomic(s3_client, bucket: str, key: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    if temporary.exists():
        temporary.unlink()
    try:
        s3_client.download_file(bucket, key, str(temporary))
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise RuntimeError(f"S3에서 빈 파일을 받았습니다: s3://{bucket}/{key}")
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_s3_policy_retriever(search_k: int | None = None):
    """Download, validate, and load the production Policy FAISS retriever."""
    bucket = _setting("GREENLENS_POLICY_BUCKET", DEFAULT_BUCKET)
    prefix = _setting("GREENLENS_POLICY_PREFIX", DEFAULT_PREFIX).strip("/")
    region = _setting("AWS_DEFAULT_REGION", DEFAULT_REGION)
    expected_model = _setting(
        "GREENLENS_POLICY_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL
    )
    k = search_k or int(os.getenv("GREENLENS_POLICY_K", "4"))
    if k < 1:
        raise ValueError("GREENLENS_POLICY_K는 1 이상이어야 합니다.")

    cache_root = Path(
        os.getenv(
            "GREENLENS_POLICY_CACHE_DIR",
            str(Path(tempfile.gettempdir()) / "greenlens_policy_index"),
        )
    ).resolve()
    cache_root.mkdir(parents=True, exist_ok=True)

    s3 = boto3.client("s3", region_name=region)
    for filename in ("manifest.json", "index.faiss", "index.pkl"):
        key = str(PurePosixPath(prefix) / filename)
        _download_atomic(s3, bucket, key, cache_root / filename)

    manifest = json.loads((cache_root / "manifest.json").read_text(encoding="utf-8-sig"))
    actual_model = str(manifest.get("embedding_model", "")).strip()
    if actual_model != expected_model:
        raise RuntimeError(
            "임베딩 모델 불일치: "
            f"manifest={actual_model!r}, expected={expected_model!r}"
        )
    if manifest.get("status") != "READY":
        raise RuntimeError(f"Policy manifest 상태가 READY가 아닙니다: {manifest.get('status')}")

    embeddings = OpenAIEmbeddings(model=expected_model)
    vector_store = FAISS.load_local(
        str(cache_root),
        embeddings,
        # This pickle is trusted only because it comes from the configured GreenLens bucket.
        allow_dangerous_deserialization=True,
    )

    expected_vectors = int(
        manifest.get("faiss_vector_count")
        or manifest.get("chunk_count")
        or manifest.get("corpus_chunk_count")
        or 0
    )
    actual_vectors = int(vector_store.index.ntotal)
    if expected_vectors and actual_vectors != expected_vectors:
        raise RuntimeError(
            f"FAISS 벡터 수 불일치: manifest={expected_vectors}, index={actual_vectors}"
        )

    info = {
        "bucket": bucket,
        "prefix": prefix,
        "region": region,
        "embedding_model": expected_model,
        "vector_count": actual_vectors,
        "search_k": k,
    }
    return vector_store.as_retriever(search_kwargs={"k": k}), info
