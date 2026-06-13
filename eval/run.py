"""
RAGAS evaluation pipeline for Meridian.

Calls the live /query SSE endpoint for each item in golden_set.json,
assembles a Dataset, and scores context_precision using direct Azure OpenAI calls.

Context precision: fraction of retrieved contexts judged relevant by an LLM,
averaged across all questions. Equivalent to the RAGAS context_precision metric.

Usage:
    python -m eval.run
    python -m eval.run --endpoint https://meridian-aca.<hash>.eastus.azurecontainerapps.io

Exit codes:
    0  evaluation completed successfully
    1  evaluation failed to run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from openai import AzureOpenAI

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"
DEFAULT_ENDPOINT = os.getenv("QUERY_ENDPOINT", "http://localhost:8000")
REQUEST_TIMEOUT = 60
RETRY_ATTEMPTS = 2
RETRY_SLEEP = 3
CHAT_DEPLOYMENT = "gpt-4o-mini"
OPENAI_API_VERSION = "2024-02-01"


def _get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.environ["OPENAI_ENDPOINT"],
        api_key=os.environ["OPENAI_KEY"],
        api_version=OPENAI_API_VERSION,
    )


def _parse_sse_stream(raw: str) -> tuple[str, list[str]]:
    answer_parts: list[str] = []
    sources: list[str] = []

    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            break
        try:
            obj: dict[str, Any] = json.loads(payload)
        except json.JSONDecodeError:
            continue

        if obj.get("type") == "token" and "content" in obj:
            answer_parts.append(obj["content"])
        if obj.get("type") == "sources" and obj.get("sources"):
            for src in obj["sources"]:
                content = src.get("content") or src.get("text") or str(src)
                if content and content not in sources:
                    sources.append(content)

    return "".join(answer_parts).strip(), sources


def _query(client: httpx.Client, endpoint: str, tenant_id: str, question: str) -> tuple[str, list[str]]:
    url = endpoint.rstrip("/") + "/query"
    headers = {
        "X-Tenant-ID": tenant_id,
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }
    payload = {"query": question}

    last_exc: Exception | None = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with client.stream("POST", url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT) as resp:
                resp.raise_for_status()
                raw = resp.read().decode("utf-8")
            return _parse_sse_stream(raw)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            print(f"  [attempt {attempt}/{RETRY_ATTEMPTS}] error: {exc}", file=sys.stderr)
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_SLEEP)

    raise RuntimeError(f"all {RETRY_ATTEMPTS} attempts failed for question '{question[:60]}...'") from last_exc


def _is_context_relevant(
    oai: AzureOpenAI,
    question: str,
    context: str,
    ground_truth: str,
) -> bool:
    """
    Ask the LLM whether a single retrieved context is relevant for answering
    the question, given the ground truth. Returns True if relevant.
    """
    prompt = (
        "Given the question and ground truth answer, judge whether the context "
        "contains information useful for answering the question.\n\n"
        f"Question: {question}\n\n"
        f"Ground truth: {ground_truth}\n\n"
        f"Context: {context}\n\n"
        "Reply with only 'yes' or 'no'."
    )
    try:
        resp = oai.chat.completions.create(
            model=CHAT_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=5,
        )
        return resp.choices[0].message.content.strip().lower().startswith("yes")
    except Exception as exc:  # noqa: BLE001
        print(f"  relevance check failed: {exc}", file=sys.stderr)
        return False


def _score_context_precision(
    oai: AzureOpenAI,
    question: str,
    contexts: list[str],
    ground_truth: str,
) -> float:
    """
    Context precision: fraction of retrieved contexts judged relevant.
    Returns 0.0 when index is empty (no contexts retrieved).
    """
    real_contexts = [c for c in contexts if c and c != "No relevant documents found for your query."]
    if not real_contexts:
        return 0.0

    relevant = sum(
        1 for ctx in real_contexts
        if _is_context_relevant(oai, question, ctx, ground_truth)
    )
    return relevant / len(real_contexts)


def run_evaluation(endpoint: str = DEFAULT_ENDPOINT) -> dict[str, float]:
    golden: list[dict[str, Any]] = json.loads(GOLDEN_SET_PATH.read_text())
    print(f"loaded {len(golden)} items from {GOLDEN_SET_PATH}")
    print(f"endpoint: {endpoint}\n")

    oai = _get_openai_client()
    precision_scores: list[float] = []

    with httpx.Client() as client:
        for idx, item in enumerate(golden, start=1):
            q = item["question"]
            tenant = item["tenant_id"]
            gt = item["ground_truth"]
            print(f"[{idx:02d}/{len(golden)}] tenant={tenant}  q={q[:70]}...")

            try:
                answer, ctx = _query(client, endpoint, tenant, q)
            except RuntimeError as exc:
                print(f"  error: {exc}", file=sys.stderr)
                answer, ctx = "", []

            print(f"  answer_len={len(answer)} chars  contexts={len(ctx)}")

            score = _score_context_precision(oai, q, ctx, gt)
            precision_scores.append(score)
            print(f"  context_precision={score:.4f}")

    context_precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0.0
    return {"context_precision": context_precision}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    args = parser.parse_args()

    try:
        scores = run_evaluation(endpoint=args.endpoint)
    except Exception as exc:  # noqa: BLE001
        print(f"\nfatal: evaluation pipeline failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 50)
    print("RAGAS EVALUATION RESULTS")
    print("=" * 50)
    for metric, score in scores.items():
        gate_note = ""
        if metric == "context_precision":
            status = "PASS" if score >= 0.85 else "FAIL"
            gate_note = f"  [{status} - threshold 0.85]"
        print(f"  {metric:<30} {score:.4f}{gate_note}")
    print("=" * 50)

    scores_path = Path(__file__).parent / "scores.json"
    scores_path.write_text(json.dumps(scores, indent=2))
    print(f"\nscores written to {scores_path}")


if __name__ == "__main__":
    main()
