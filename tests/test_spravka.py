import unittest
import os
import io
import pypdf
import sys

# Добавляем родительскую директорию в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from spravka_engine import generate_pdf, SpravkaData


class TestSpravkaGenerator(unittest.TestCase):
    def setUp(self):
        self.output_dir = os.path.join(os.path.dirname(__file__), "test_output")
        os.makedirs(self.output_dir, exist_ok=True)
        self.sample_data = {
            "org_inn": "773610841807",
            "doc_number": "099",
            "correction_num": 0,
            "year": 2025,
            "org_name_lines": [
                "ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ",
                "БУРЛАКОВ НИКИТА СЕРГЕЕВИЧ"
            ],
            "full_time": 0,
            "payer_last_name": "ТЕСТОВ",
            "payer_first_name": "ИВАН",
            "payer_middle_name": "ПЕТРОВИЧ",
            "payer_birth_date": "01.01.1990",
            "doc_code": "21",
            "doc_series": "4510",
            "doc_num": "123456",
            "doc_issue_date": "10.05.2010",
            "amount_rub": 100000,
            "amount_kop": 50,
            "confirm_last_name": "БУРЛАКОВ",
            "confirm_first_name": "НИКИТА",
            "confirm_middle_name": "СЕРГЕЕВИЧ",
            "doc_date": "15.07.2026",
            "is_same_person": 1,
            "has_page_2": True
        }

    def test_pdf_generation_validity(self):
        """Проверка успешной генерации PDF документа и структуры страниц."""
        out_path = os.path.join(self.output_dir, "test_099.pdf")
        pdf_bytes = generate_pdf(self.sample_data, output_path=out_path)

        self.assertGreater(len(pdf_bytes), 50000, "PDF файл слишком маленький")
        self.assertTrue(os.path.exists(out_path), "Файл не был сохранен на диск")

        # Проверка валидности PDF через PyPDF
        reader = pypdf.PdfReader(out_path)
        self.assertEqual(len(reader.pages), 2, "Должно быть ровно 2 страницы")

    def test_different_student_and_payer(self):
        """Проверка генерации, когда обучаемый и плательщик — разные лица."""
        data = dict(self.sample_data)
        data["is_same_person"] = 0
        data["student_last_name"] = "ТЕСТОВА"
        data["student_first_name"] = "АННА"
        data["student_middle_name"] = "ИВАНОВНА"
        data["student_birth_date"] = "12.08.2015"
        data["student_doc_series"] = "4516"
        data["student_doc_num"] = "654321"
        data["student_doc_issue_date"] = "20.08.2025"

        out_path = os.path.join(self.output_dir, "test_diff_student.pdf")
        pdf_bytes = generate_pdf(data, output_path=out_path)

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        self.assertEqual(len(reader.pages), 2)

    def test_single_page_mode(self):
        """Проверка генерации одностраничной справки при has_page_2 = False."""
        data = dict(self.sample_data)
        data["has_page_2"] = False

        out_path = os.path.join(self.output_dir, "test_p1_only.pdf")
        pdf_bytes = generate_pdf(data, output_path=out_path)

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        self.assertEqual(len(reader.pages), 1, "Должна быть 1 страница")

    def test_amount_parsing(self):
        """Проверка парсинга различных строковых форматов сумм."""
        spravka = SpravkaData.from_dict({"amount": "145 678,90 руб."})
        self.assertEqual(spravka.amount_rub, 145678)
        self.assertEqual(spravka.amount_kop, 90)


if __name__ == "__main__":
    unittest.main()
