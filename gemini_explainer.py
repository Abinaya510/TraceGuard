import json
import os

from google import genai


def build_investigation_prompt(evidence, risk_score):
    return f"""
You are TraceGuard, a banking transaction investigation assistant.

IMPORTANT:
- You are an explanation assistant, not a fraud decision-maker.
- Do not claim that fraud occurred.
- Do not invent transactions, facts, payees, dates, amounts, or customer history.
- Use ONLY the supplied evidence.
- Every transaction you mention MUST use a transaction_id from the evidence.
- Explain the deterministic risk signals already detected.
- The first finding must clearly state whether attention is required.
- If evidence contains risk signals, identify what should be investigated first.
- The risk score is an investigation-priority score, NOT a probability of fraud.

Deterministic investigation priority score:
{risk_score}

Supplied transaction evidence:
{json.dumps(evidence, indent=2)}

Produce a concise investigation report using exactly these sections:

1. FINDING
State either:
ATTENTION REQUIRED
or
NO ATTENTION REQUIRED

2. PRIORITY TRANSACTIONS
List the transaction IDs that should be reviewed first.

3. TRIGGERED RISK SIGNALS
Explain which deterministic rules were triggered and why.

4. BEHAVIOUR DEVIATION
Explain how the flagged activity differs from the customer's established behaviour, using only the supplied evidence.

5. CONNECTIONS
Explain relationships between the flagged transactions, such as timing, payee, amount, or multiple rules applying to the same transactions.

6. INVESTIGATOR SHOULD CHECK FIRST
Give a short ordered list of practical checks.

7. EVIDENCE
List the transaction IDs supporting the conclusion.

8. DISCLAIMER
State that the findings are investigation signals and that a human investigator must make the final determination.

Do not add unsupported information.
"""


def generate_investigation_report(evidence, risk_score):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return {
            "success": False,
            "report": None,
            "error": "GEMINI_API_KEY is not configured."
        }

    try:
        client = genai.Client(api_key=api_key)

        prompt = build_investigation_prompt(
            evidence,
            risk_score
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt
        )

        report = response.text.strip()

        if not report:
            return {
                "success": False,
                "report": None,
                "error": "Gemini returned an empty response."
            }

        return {
            "success": True,
            "report": report,
            "error": None
        }

    except Exception as exc:
        return {
            "success": False,
            "report": None,
            "error": f"Gemini explanation failed: {exc}"
        }