import random
import csv
from pathlib import Path


class ExamQuestions:
    banks = {}

    @classmethod
    def load_bank(cls, path: str, lang: str = "en"):
        bank = {}
        with open(Path(path), 'r', encoding="UTF-8") as question_bank:
            csv_reader = csv.DictReader(question_bank, delimiter=",")
            for rows in csv_reader:
                q_id = int(rows['q_id'])
                bank[q_id] = rows
        cls.banks[lang] = bank

    @classmethod
    def get_question_id(cls, q_id: int, lang: str = "en"):
        return cls.banks.get(lang, cls.banks.get("en", {})).get(q_id, {})

    @classmethod
    def get_all_questions_id(cls, lang: str = "en"):
        return list(cls.banks.get(lang, cls.banks.get("en", {})).keys())

    @classmethod
    def create_question_bank(cls, q_nb: int = 50, lang: str = "en"):
        questions_available = list(cls.banks.get(lang, cls.banks.get("en", {})).keys())
        assert q_nb < len(questions_available)
        random.shuffle(questions_available)
        return questions_available[:q_nb]
