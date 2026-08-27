import spacy


class NERDetector:

    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

    def detect(self, prompt: str) -> list[dict]:
        doc = self.nlp(prompt)

        entities = []

        for entity in doc.ents:
            entities.append({
                "text": entity.text,
                "label": entity.label_
            })

        return entities