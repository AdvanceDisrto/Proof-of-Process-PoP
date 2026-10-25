from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


class SovereignTokenizer:
    def __init__(self):
        self.vocab = {"[PAD]": 0, "[UNK]": 1, "[BOS]": 2, "[EOS]": 3}

    def train_on_text(self, text, max_vocab_size=10000):
        tokens = TOKEN_PATTERN.findall(text.lower())
        counts = Counter(tokens)
        for token, _ in counts.most_common(max(0, max_vocab_size - len(self.vocab))):
            if token not in self.vocab:
                self.vocab[token] = len(self.vocab)

    def encode(self, text):
        tokens = TOKEN_PATTERN.findall(text.lower())
        return [2] + [self.vocab.get(token, 1) for token in tokens] + [3]

    def decode(self, ids):
        inverse_vocab = {value: key for key, value in self.vocab.items()}
        return " ".join(
            inverse_vocab.get(token_id, "[UNK]")
            for token_id in ids
            if token_id not in (2, 3)
        )

    def save(self, path):
        Path(path).write_text(
            json.dumps(self.vocab, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path):
        tokenizer = cls()
        tokenizer.vocab = json.loads(
            Path(path).read_text(encoding="utf-8")
        )
        return tokenizer
