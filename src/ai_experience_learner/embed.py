"""Embedding via OpenAI-compatible API."""

import os

import httpx
import numpy as np


def get_api_key(env_var: str) -> str | None:
    return os.environ.get(env_var) or None


def encode(text: str, api_url: str, api_key: str, model: str) -> np.ndarray | None:
    """Call /v1/embeddings and return float32 vector."""
    try:
        resp = httpx.post(
            f"{api_url}/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"input": text, "model": model},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()["data"][0]["embedding"]
        return np.array(data, dtype=np.float32)
    except Exception as e:
        print(f"Embedding API error: {e}", flush=True)
        return None


def encode_batch(texts: list[str], api_url: str, api_key: str, model: str) -> np.ndarray | None:
    """Batch encode via API. Returns (N, dim) array or None."""
    try:
        resp = httpx.post(
            f"{api_url}/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"input": texts, "model": model},
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        # API may return in different order — sort by index
        data.sort(key=lambda x: x["index"])
        vecs = [d["embedding"] for d in data]
        return np.array(vecs, dtype=np.float32)
    except Exception as e:
        print(f"Embedding API error: {e}", flush=True)
        return None


def to_blob(vec: np.ndarray) -> bytes:
    return vec.astype(np.float32).tobytes()


def from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def cosine_similarity_batch(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    return matrix @ query
