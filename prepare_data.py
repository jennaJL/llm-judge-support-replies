"""How the 50 evaluation items were built (run once, before labelling).

1. Sample 50 conversations from the public Bitext customer-support dataset.
2. Add synthetic problems: 4 refund-policy violations (Q2) and 6 generic replies (Q3).
3. Write data/sample_unlabelled.csv. I then labelled it by hand -> data/labels.xlsx.

If data/labels.xlsx exists, the script checks that the rebuilt items match it.
Needs: pip install datasets pandas openpyxl (and internet access for the download).
"""
from pathlib import Path
import pandas as pd
from datasets import load_dataset

df = load_dataset("bitext/Bitext-customer-support-llm-chatbot-training-dataset",
                  split="train").to_pandas()

REFUND = ["get_refund", "check_refund_policy", "track_refund"]
refund = df[df["intent"].isin(REFUND)].sample(20, random_state=42)
complaint = df[df["intent"] == "complaint"].sample(15, random_state=42)
other = df[~df["intent"].isin(REFUND + ["complaint"])].sample(15, random_state=42)

sample = pd.concat([refund, complaint, other]).reset_index(drop=True)
sample.insert(0, "id", range(1, len(sample) + 1))
sample["synthetic"] = 0

# Q2: append one sentence that breaks the refund policy
Q2_EDITS = {
    1: "I've already approved your refund, so no need to check anything.",   # guarantee before checking
    3: "We can also give you the refund in cash at any store.",              # cash refund
    5: "Your money will be back in your account by tomorrow.",               # faster than 5-10 days
    7: "Even though it's been 3 months, I'll make an exception and refund you.",  # after 30 days
}
for i, text in Q2_EDITS.items():
    sample.loc[sample["id"] == i, "response"] += " " + text
    sample.loc[sample["id"] == i, "synthetic"] = 1

# Q3: replace the whole reply with a generic one that says nothing about the request
Q3_EDITS = {
    21: "Thank you for reaching out to us. We value your feedback. Is there anything else I can help you with today?",
    22: "Thanks for contacting us! Our team is always happy to help. Please let us know if there is anything else you need.",
    26: "Thank you for your message. We appreciate you taking the time to get in touch. Have a great day!",
    28: "I understand. Thanks for reaching out, and we're here for you whenever you need us.",
    31: "Thank you for contacting our support team. Your satisfaction is important to us. How else can I help?",
    33: "We appreciate your patience. Thank you for being a valued customer. Let me know if there's anything else I can do for you.",
}
for i, text in Q3_EDITS.items():
    sample.loc[sample["id"] == i, "response"] = text
    sample.loc[sample["id"] == i, "synthetic"] = 1

Path("data").mkdir(exist_ok=True)
sample[["id", "intent", "instruction", "response", "synthetic"]].to_csv("data/sample_unlabelled.csv", index=False)
print("wrote data/sample_unlabelled.csv:", len(sample), "items,", int(sample["synthetic"].sum()), "synthetic")

# check against the labelled file
if Path("data/labels.xlsx").exists():
    labels = pd.read_excel("data/labels.xlsx")
    m = sample.merge(labels, on="id", suffixes=("", "_labelled"))
    diff = m[(m["instruction"] != m["instruction_labelled"]) |
             (m["response"].str.strip() != m["response_labelled"].str.strip())]
    print("items that differ from data/labels.xlsx:", diff["id"].tolist() or "none")
