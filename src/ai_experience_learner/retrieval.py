"""Retrieval algorithms — MMR and keyword fallback."""

import numpy as np

from . import embed


def mmr_select(
    query_vec: np.ndarray,
    candidates: list[dict],
    vec_key: str = "embedding",
    top_k: int = 3,
    lam: float = 0.6,
) -> list[dict]:
    """Maximal Marginal Relevance (paper Section 4).

    Q(x) = λ * relevance + (1-λ) * diversity
    """
    if not candidates:
        return []
    if len(candidates) <= top_k:
        return candidates

    vecs = np.stack([c[vec_key] for c in candidates])
    rel_scores = embed.cosine_similarity_batch(query_vec, vecs)

    selected_indices = []
    remaining = set(range(len(candidates)))

    first = int(np.argmax(rel_scores))
    selected_indices.append(first)
    remaining.discard(first)

    for _ in range(top_k - 1):
        best_score = -float("inf")
        best_idx = -1
        for idx in remaining:
            relevance = rel_scores[idx]
            if selected_indices:
                sim_to_selected = max(
                    embed.cosine_similarity(vecs[idx], vecs[s])
                    for s in selected_indices
                )
                diversity = 1.0 - sim_to_selected
            else:
                diversity = 1.0
            score = lam * relevance + (1 - lam) * diversity
            if score > best_score:
                best_score = score
                best_idx = idx
        selected_indices.append(best_idx)
        remaining.discard(best_idx)

    result = []
    for i in selected_indices:
        candidates[i]["_relevance"] = float(rel_scores[i])
        result.append(candidates[i])
    return result


def keyword_recall(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """TF-IDF-style keyword matching fallback for Tier 1."""
    query_words = set(query.lower().split())
    scored = []
    for c in candidates:
        text = (
            f"{c.get('topic', '')} {c.get('problem_type', '')} "
            f"{c.get('technique', '')} {c['lesson_text']}"
        ).lower()
        text_words = set(text.split())
        overlap = len(query_words & text_words)
        scored.append((overlap, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    max_overlap = max(len(query_words), 1)
    result = []
    for overlap, c in scored[:top_k]:
        c["_relevance"] = overlap / max_overlap
        result.append(c)
    return result
