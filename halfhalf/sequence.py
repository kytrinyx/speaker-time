from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class Sequence:
    segments: list

    @property
    def id(self):
        return ",".join(str(seg.id) for seg in sorted(self.segments, key=lambda s: s.id))

    def text(self):
        return " ".join(seg.text for seg in self.segments)

    def cleaned_text(self):
        return " ".join(seg.cleaned_text for seg in self.segments)

    def diffs(self):
        a = self.cleaned_text().split()
        b = self.text().split()
        result = []
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b).get_opcodes():
            if tag == 'replace':
                result.append((" ".join(a[i1:i2]), " ".join(b[j1:j2])))
            elif tag == 'delete':
                result.append((" ".join(a[i1:i2]), ""))
            elif tag == 'insert':
                result.append(("", " ".join(b[j1:j2])))
        return result
