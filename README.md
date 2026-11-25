# LLM-as-a-Judge for Customer Support Replies

Can a small, local LLM check customer-support replies for quality problems as reliably as a human reviewer?
I labelled 50 support conversations myself, ran a judge (Qwen2.5-7B-Instruct, run locally) on three yes/no
quality questions, and measured how often it agrees with me, where it fails, and why.

## Results

| Question (a "yes" is a problem) | Best prompt | Real problems | Caught | False alarms | MCC [95% CI] |
|---|---|---|---|---|---|
| **Q1** The request needs an order or account lookup, but the reply never asks for an identifier | v3: code + LLM | 26 | 26 | 2 | 0.92 [0.81, 1.00] |
| **Q2** The reply breaks the refund policy | v2: rules + examples | 4 | 4 | 0 | 1.00 (only 4 positives, see limits) |
| **Q3** The reply fails to acknowledge the customer's specific problem | none is usable | 6 | 6 | 20–22 | 0.35 [0.19, 0.52] |

**What I found**

1. **Splitting a compound question fixed Q1.** Asked in one go ("needs a lookup *and* doesn't ask for an
   identifier?"), the judge caught only 3/26 (v1) and 2/26 (v2) problems. When code decides whether a lookup
   is needed and the LLM only answers "does the reply ask for an identifier?", it caught 26/26 with 2 false alarms.
   The LLM's own sub-task agreed with my labels on 28 of the 29 items I labelled yes or no. v3 beat v2 in 100% of paired bootstrap resamples.
2. **Rules and examples removed Q2's false alarms.** With a bare question, the judge flagged 4 correct
   policy explanations as violations because they didn't mention every policy detail (precision 0.44).
   With explicit rules and two examples, precision rose to 1.00 (MCC +0.38, 95% CI [0.13, 0.65]; better in 99% of resamples).
3. **Q3 is not ready, and rewording did not fix it.** I suspected the negative wording ("does the agent
   *fail* to…") was confusing the judge, so I asked the positive question instead (v3). The number of false
   alarms didn't change (20 → 21), but *which* replies were flagged did: on the 44 good replies, v2 and v3
   agreed only 21 times. The false alarms are unstable noise, not one systematic misreading.
4. **The judge's "evidence" is not trustworthy.** Each prompt asks the judge to quote the sentence its answer
   is based on. In Q2 v2 it quoted the *policy* instead of the reply in 7 items (with correct answers).
   In Q3 v3 only 17 of 50 quotes came from the reply. The rest quoted the customer, pasted back the prompt, or
   copied the prompt's own example. A correct answer with a fake quote is still a problem for a QA tool.
5. **A 10-line baseline beats the LLM on Q3.** Flagging replies that share no content words with the
   customer's message catches 6/6 with 1 false alarm (MCC 0.92, against 0.33–0.35 for the LLM). Caveat: my Q3 positives are fully generic synthetic
   replies, which are easy. The baseline would miss realistic replies that mention the topic but miss the problem.

## Data

- **Source:** 50 conversations sampled from the public
  [Bitext customer-support dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset)
  (CDLA-Sharing-1.0): 20 refund requests (`get_refund`, `check_refund_policy`, `track_refund`), 15 complaints
  and 15 other intents, `random_state=42`.
- **Synthetic positives (10 of 50, marked `synthetic = 1`):** Bitext replies are uniformly polite and almost never
  break a rule, so I added problems by hand. Four Q2 replies got one policy-breaking sentence appended (a guaranteed refund,
  cash, "back by tomorrow", a refund after 3 months). Six Q3 replies were replaced with fully generic text
  ("Thanks for reaching out. How else can I help?"). See `prepare_data.py`.
- **Policy:** a short, invented refund policy (`prompts/policy.txt`). It is not any real company's policy.
- **Labels:** I labelled all 50 items for all three questions (`yes` / `no` / `n/a`) against written rules,
  then re-labelled Q1 after finding that I had applied the rule inconsistently. Every change is recorded in the `notes` column.

| | yes | no | n/a |
|---|---|---|---|
| Q1 | 26 | 3 | 21 |
| Q2 | 4 | 16 | 30 |
| Q3 | 6 | 44 | 0 |

## Method

- **Judge:** `qwen2.5:7b-instruct` through [Ollama](https://ollama.com), temperature 0, with the output constrained
  to JSON `{"evidence": ..., "answer": "yes" | "no" | "n/a"}`.
- **Prompt versions:**
  - **v1:** the question only.
  - **v2:** the question + written rules for yes/no/n/a + two examples + "first quote the sentence your answer is based on".
  - **v3 (Q1):** code decides from the request's intent whether a lookup is needed; the LLM only answers whether the reply asks for an identifier.
  - **v3 (Q3):** the positive question ("does the reply name or restate the customer's problem?"), inverted in code.
  - Q2 always gets the policy in the prompt.
- **Metrics:** "yes" (a problem) is the positive class, and an invalid answer counts as wrong.
  Positives are rare, so I report precision and recall (false alarms and misses separately), MCC, and Cohen's kappa
  (on yes/not-yes and on all three labels). Accuracy would look good for a judge that never flags anything.
- **Uncertainty:** 95% bootstrap confidence intervals (2,000 resamples of items). Versions are compared with a *paired*
  bootstrap (the same resampled items for both versions), reporting the MCC difference and the share of resamples in which the new version wins.

## Error analysis

I tagged every disagreement between the judge and my labels with one cause (`outputs/error_taxonomy.xlsx`):

| Cause | Q1 | Q2 | Q3 | What it looks like |
|---|---|---|---|---|
| Question ambiguity | 27 | 12 | 0 | Compound or negative questions; unclear n/a vs no boundary |
| Model error | 1 | 1 | 20 | Rule clear, information present, judge still wrong or inconsistent |
| Label error / missing context / data problem | 0 | 0 | 0 | |

The rows cover Q1 v2 and v3, Q2 v1 and v2, and Q3 v2. For Q2 v2 they are n/a-vs-no disagreements only; there were no yes/no errors.

## Limitations

- **Small and partly synthetic.** 50 items, one annotator (me). All Q2 and Q3 positives are synthetic and easy to spot
  (Q2 violations are appended at the end of the reply; Q3 positives are fully generic). Catching all 4 Q2 violations only shows,
  with 95% confidence, that the true catch rate is above about 40% (above 54% for Q3's 6 of 6, above 87% for Q1's 26 of 26).
- **Tuned and tested on the same items.** v2 and v3 were written after looking at errors on these 50 items, so the scores are
  optimistic. The next step is a fresh, held-out sample.
- **Q1 v3 partly agrees by design.** My Q1 labels and the code rule both decide "needs a lookup" from the request type,
  so that half of v3 matches my labels almost automatically. The real test is the LLM half (28 of 29 correct).
- **One small model, one run.** Results may differ with larger models or other providers.

## Reproduce

```bash
pip install -r requirements.txt
ollama pull qwen2.5:7b-instruct      # Ollama must be running
jupyter notebook llm_judge.ipynb     # Kernel → Restart & Run All
```

By default (`RUN_JUDGE = False`, `RUN_Q3V3 = False`) the notebook reuses the saved judge answers in `outputs/`
and recomputes every score in seconds. Set both to `True` to call the model again (about 400 calls; roughly
45 minutes on a laptop). Results can differ slightly between Ollama versions.

## Files

```
llm_judge.ipynb            the whole evaluation: prompts, judge runs, scoring, bootstrap, baseline, error taxonomy
prepare_data.py            how the 50 items were sampled from Bitext and the synthetic edits made
data/labels.xlsx           the 50 items with my labels and notes (Bitext text, CDLA-Sharing-1.0)
prompts/policy.txt         the invented refund policy given to the judge for Q2
outputs/judge_answers*.csv every raw judge answer
outputs/results.csv        the metrics table
outputs/error_taxonomy.xlsx every disagreement, tagged with a cause
```

## Notes

Code written with AI assistance. The research question, labels, rules, error tags and conclusions are my own.
Code: MIT License. Data in `data/` is derived from Bitext and shared under CDLA-Sharing-1.0.
