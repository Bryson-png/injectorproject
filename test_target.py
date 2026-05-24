"""test_target.py — Quick benign-input smoke test for each target."""
from target import TARGETS

QUESTIONS = {
    "code_review": (
        "Please review this small diff:\n\n"
        "def add(a, b):\n    return a + b"
    ),
    "legal_disclaimer": "What's the difference between a misdemeanor and a felony in general?",
    "brand_pr": "What products does Acme Industries make?",
}

for key, target in TARGETS.items():
    print(f"\n{'=' * 60}")
    print(f"TARGET: {target.name}")
    print(f"{'=' * 60}")
    response = target.send(QUESTIONS[key])
    if response["error"]:
        print(f"[ERROR] {response['text']}")
    else:
        print(response["text"])
