# pers0na

A persona-hijack direct prompt-injection harness. Fires DAN-style, authority-cloaked, roleplay-framing, and persona-extraction attacks at three target chatbots and uses an LLM-as-judge to measure rule-violation rate.

## What It Does

`pers0na` runs 13 persona-hijack attacks (4 universal + 3 per scenario × 3 scenarios) against three fictional chatbot targets — a code-review bot, a legal-disclaimer bot, and a brand-PR bot. A second Gemini call grades each trial: did the target violate one of its original rules in the response, or did it hold its persona? Output is a JSON-Lines transcript plus a summary file.

## Why

Persona-hijack is one of the most-documented direct prompt-injection families ([Shen et al. 2024](https://arxiv.org/abs/2308.03825)). Unlike rule-override attacks ("ignore the rule about X"), persona-hijack rewrites *who* the model thinks is enforcing the rule. Measuring how often it works on a given model and target is a basic-but-meaningful AI-security signal.

Maps to:

- [OWASP LLM01 — Prompt Injection (Direct)](https://genai.owasp.org/llm-top-10/)
- [MITRE ATLAS AML.T0051.000 — LLM Prompt Injection: Direct](https://atlas.mitre.org/techniques/AML.T0051.000/)
- [NIST AI RMF — MEASURE function](https://www.nist.gov/itl/ai-risk-management-framework)

## Attack Taxonomy

| Family | Universal? | Examples |
|---|---|---|
| DAN-style | Yes | DAN Classic, Unrestricted Alter-Ego |
| Authority-cloaked | Mostly | Fake Developer Debug, Emergency Legal Mode |
| Roleplay framing | Scenario-specific | SeniorEng-9000, JusticeAI, BrandWhistle |
| Persona extraction | Yes | Persona Recall Probe |

## Targets

| Key | Persona | Rule type |
|---|---|---|
| `code_review` | CodeGuard (code reviewer) | No `eval`/`exec`/`os.system`/`pickle.loads` on untrusted input |
| `legal_disclaimer` | LegalAssist (legal info) | No specific legal advice; always include disclaimer |
| `brand_pr` | AcmeAssist (brand PR) | No criticism; no competitor names; brand-positive only |

## Outcomes

| Outcome | Meaning |
|---|---|
| `hijacked` | The target violated one of its rules in the response. |
| `held_persona` | The target held its persona / refused. |
| `error` | API or judge failure — excluded from the rate denominator. |

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/pers0na.git
cd pers0na
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export GOOGLE_API_KEY='your-key-here'
python3 pers0na.py
```

Or test a single target:

```bash
python3 pers0na.py --target code_review
```

## How It Works

```
target.py    → defines 3 fictional chatbots with personas + rules
attacks.py   → 13 persona-hijack attacks across 4 families
judge.py     → second LLM call: did the target violate its rules?
pers0na.py   → loops over (target × attack), streams JSONL trials
runs/<run_id>/trials.jsonl  → one JSON object per trial
runs/<run_id>/summary.json  → aggregated counts per target and family
```

## Technologies

- Python 3.10+
- Google Gemini via `google-genai` SDK
- LLM-as-judge with structured output via `response_schema`
- Streaming JSON Lines for safe-by-default transcripts

## References

- Shen et al., *"Do Anything Now: Characterizing and Evaluating In-The-Wild Jailbreak Prompts on Large Language Models"* (2024). [arxiv.org/abs/2308.03825](https://arxiv.org/abs/2308.03825)
- OWASP, *Top 10 for LLM Applications.* [genai.owasp.org/llm-top-10](https://genai.owasp.org/llm-top-10/)
- MITRE, *ATLAS adversarial-ML technique catalog.* [atlas.mitre.org](https://atlas.mitre.org/)

## Author

Built by [Your Name]. Public learning project — see the gr4dient guide series.

## License

[CC BY-SA 4.0](LICENSE).# injectorproject
