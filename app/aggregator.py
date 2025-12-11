from collections import Counter

class Aggregator:
    def compute_signals(self, docs):
        tags = []
        positives = Counter()
        negatives = Counter()
        insiders = Counter()

        for d in docs:
            t = d["tags"].split(",") if isinstance(d["tags"], str) else d["tags"]
            for tag in t:
                tags.append(tag)
                if d["sentiment"] == "positive":
                    positives[tag] += 1
                if d["sentiment"] == "negative":
                    negatives[tag] += 1
                if d["is_insider"]:
                    insiders[tag] += 1

        counter = Counter(tags)

        res = []
        for tag, count in counter.items():
            pos = positives[tag]
            neg = negatives[tag]
            ins = insiders[tag]

            if count > 5 and neg > pos * 1.5:
                signal = "problem"
            elif count > 5 and pos > neg * 1.5:
                signal = "opportunity"
            elif count < 3 and ins > 0:
                signal = "early_trend"
            else:
                signal = "none"

            res.append({
                "tag": tag,
                "count": count,
                "positive": pos,
                "negative": neg,
                "insiders": ins,
                "signal": signal
            })

        return res
