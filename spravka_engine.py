"""
Модуль генерации справок об оплате образовательных услуг
Форма по КНД 1151158 (Приложение № 1 к приказу ФНС России)
"""

import io
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union

import pypdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Стандартный размер клетки ФНС (5 мм) в типографских пунктах
CELL_SIZE = 14.17323  # 72 / 25.4 * 5 mm

# Поиск шрифта Arial в системе Windows / Linux / macOS
def register_fonts() -> str:
    registered = pdfmetrics.getRegisteredFontNames()
    if 'SpravkaArial' in registered:
        return 'SpravkaArial'
    
    font_candidates = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\Arial.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        os.path.join(os.path.dirname(__file__), "assets", "arial.ttf")
    ]
    for p in font_candidates:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont('SpravkaArial', p))
                return 'SpravkaArial'
            except Exception:
                pass
    return 'Helvetica'

FONT_NAME = register_fonts()


@dataclass
class SpravkaData:
    # 1. Данные организации / ИП (статические)
    org_inn: str = "773610841807"
    org_kpp: str = ""
    org_name_lines: List[str] = field(default_factory=lambda: [
        "ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ",
        "БУРЛАКОВ НИКИТА СЕРГЕЕВИЧ"
    ])
    full_time: int = 0  # 0 - нет, 1 - да
    confirm_last_name: str = "БУРЛАКОВ"
    confirm_first_name: str = "НИКИТА"
    confirm_middle_name: str = "СЕРГЕЕВИЧ"
    signature_path: Optional[str] = "assets/signature.png"

    # 2. Данные справки (динамические)
    doc_number: str = "035"
    correction_num: int = 0
    year: int = 2025
    doc_date: str = "01.07.2026"

    # 3. Данные налогоплательщика (плательщика)
    payer_last_name: str = ""
    payer_first_name: str = ""
    payer_middle_name: str = ""
    payer_inn: str = ""
    payer_birth_date: str = ""
    doc_code: str = "21"  # 21 - Паспорт гражданина РФ
    doc_series: str = ""
    doc_num: str = ""
    doc_issue_date: str = ""

    # 4. Сумма расходов
    amount_rub: int = 0
    amount_kop: int = 0

    # 5. Признак одного лица и данные обучаемого
    is_same_person: int = 1  # 1 - да, 0 - нет
    has_page_2: bool = True  # формировать страницу 2
    student_last_name: str = ""
    student_first_name: str = ""
    student_middle_name: str = ""
    student_inn: str = ""
    student_birth_date: str = ""
    student_doc_code: str = "21"
    student_doc_series: str = ""
    student_doc_num: str = ""
    student_doc_issue_date: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SpravkaData":
        # Очистка и нормализация суммы
        amount_raw = d.get('amount', d.get('amount_rub', 0))
        rub, kop = 0, 0
        if isinstance(amount_raw, (int, float)):
            rub = int(amount_raw)
            kop = int(round((amount_raw - rub) * 100))
        elif isinstance(amount_raw, str):
            clean_amt = amount_raw.replace(' ', '').replace('руб.', '').replace('руб', '').replace(',', '.')
            try:
                val = float(clean_amt)
                rub = int(val)
                kop = int(round((val - rub) * 100))
            except ValueError:
                rub, kop = 0, 0
        
        # Если kop явно передан
        if 'amount_kop' in d:
            try:
                kop = int(d['amount_kop'])
            except (ValueError, TypeError):
                pass

        # Нормализация серий и номеров паспорта
        passport_raw = str(d.get('passport', '')).strip()
        doc_series = str(d.get('doc_series', '')).strip()
        doc_num = str(d.get('doc_num', '')).strip()
        if passport_raw and (not doc_series or not doc_num):
            parts = re.split(r'\s+', passport_raw)
            if len(parts) >= 2:
                doc_series = parts[0]
                doc_num = "".join(parts[1:])
            elif len(passport_raw) == 10:
                doc_series = passport_raw[:4]
                doc_num = passport_raw[4:]

        # Обучаемый паспорт
        st_passport_raw = str(d.get('student_passport', '')).strip()
        st_doc_series = str(d.get('student_doc_series', '')).strip()
        st_doc_num = str(d.get('student_doc_num', '')).strip()
        if st_passport_raw and (not st_doc_series or not st_doc_num):
            parts = re.split(r'\s+', st_passport_raw)
            if len(parts) >= 2:
                st_doc_series = parts[0]
                st_doc_num = "".join(parts[1:])
            elif len(st_passport_raw) == 10:
                st_doc_series = st_passport_raw[:4]
                st_doc_num = st_passport_raw[4:]

        # Нормализация номера справки (031, 032, ...)
        num_str = str(d.get('doc_number', d.get('number', '001'))).strip()
        if num_str.isdigit() and len(num_str) < 3:
            num_str = num_str.zfill(3)

        # Обработка наименования организации
        org_lines = d.get('org_name_lines')
        if not org_lines and 'org_name' in d:
            raw_lines = str(d['org_name']).split('\n')
            org_lines = [l.strip() for l in raw_lines if l.strip()]

        return cls(
            org_inn=str(d.get('org_inn', '773610841807')).strip(),
            org_kpp=str(d.get('org_kpp', '')).strip(),
            org_name_lines=org_lines or [
                "ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ",
                "БУРЛАКОВ НИКИТА СЕРГЕЕВИЧ"
            ],
            full_time=int(d.get('full_time', 0)),
            confirm_last_name=str(d.get('confirm_last_name', 'БУРЛАКОВ')).strip(),
            confirm_first_name=str(d.get('confirm_first_name', 'НИКИТА')).strip(),
            confirm_middle_name=str(d.get('confirm_middle_name', 'СЕРГЕЕВИЧ')).strip(),
            signature_path=d.get('signature_path', 'assets/signature.png'),
            doc_number=num_str,
            correction_num=int(d.get('correction_num', 0)),
            year=int(d.get('year', 2025)),
            doc_date=str(d.get('doc_date', '01.07.2026')).strip(),
            payer_last_name=str(d.get('payer_last_name', d.get('last_name', ''))).strip(),
            payer_first_name=str(d.get('payer_first_name', d.get('first_name', ''))).strip(),
            payer_middle_name=str(d.get('payer_middle_name', d.get('middle_name', ''))).strip(),
            payer_inn=str(d.get('payer_inn', '')).strip(),
            payer_birth_date=str(d.get('payer_birth_date', d.get('birth_date', ''))).strip(),
            doc_code=str(d.get('doc_code', '21')).strip(),
            doc_series=doc_series,
            doc_num=doc_num,
            doc_issue_date=str(d.get('doc_issue_date', d.get('issue_date', ''))).strip(),
            amount_rub=rub,
            amount_kop=kop,
            is_same_person=int(d.get('is_same_person', 1)),
            has_page_2=bool(d.get('has_page_2', True)),
            student_last_name=str(d.get('student_last_name', '')).strip(),
            student_first_name=str(d.get('student_first_name', '')).strip(),
            student_middle_name=str(d.get('student_middle_name', '')).strip(),
            student_inn=str(d.get('student_inn', '')).strip(),
            student_birth_date=str(d.get('student_birth_date', '')).strip(),
            student_doc_code=str(d.get('student_doc_code', '21')).strip(),
            student_doc_series=st_doc_series,
            student_doc_num=st_doc_num,
            student_doc_issue_date=str(d.get('student_doc_issue_date', '')).strip(),
        )


def _draw_cell_text(canv: canvas.Canvas, text: str, start_x: float, y_baseline: float, font_name: str, font_size: float = 11.0, cell_size: float = CELL_SIZE):
    """Отрисовка текста посимвольно по центру клеток сетки ФНС."""
    canv.setFont(font_name, font_size)
    for i, ch in enumerate(text):
        if ch == ' ':
            continue
        cell_x = start_x + i * cell_size
        ch_width = canv.stringWidth(ch, font_name, font_size)
        x_pos = cell_x + (cell_size - ch_width) / 2.0
        canv.drawString(x_pos, y_baseline, ch)


def _draw_date_cells(canv: canvas.Canvas, date_str: str, start_x: float, y_baseline: float, font_name: str, font_size: float = 11.0, cell_size: float = CELL_SIZE):
    """
    Отрисовка даты в формате ДД.ММ.ГГГГ с учетом типографских точек бланка:
    Клетки 0..1: день, клетка 2: точка бланка, клетки 3..4: месяц, клетка 5: точка, клетки 6..9: год.
    """
    clean_date = re.sub(r'[^0-9]', '', date_str)
    if len(clean_date) != 8:
        return
    cell_indices = [0, 1, 3, 4, 6, 7, 8, 9]
    for ch, idx in zip(clean_date, cell_indices):
        _draw_cell_text(canv, ch, start_x + idx * cell_size, y_baseline, font_name, font_size, cell_size)


def _draw_amount_cells(canv: canvas.Canvas, amount_rub: int, amount_kop: int, dot_cell_x: float, y_baseline: float, font_name: str, font_size: float = 11.0, cell_size: float = CELL_SIZE):
    """
    Отрисовка суммы: рубли выравниваются по правому краю к точке, копейки — 2 цифры после точки.
    """
    rub_str = str(amount_rub)
    for i, ch in enumerate(reversed(rub_str)):
        cell_x = dot_cell_x - (i + 1) * cell_size
        ch_width = canv.stringWidth(ch, font_name, font_size)
        canv.drawString(cell_x + (cell_size - ch_width) / 2.0, y_baseline, ch)
    kop_str = f"{amount_kop:02d}"
    _draw_cell_text(canv, kop_str, dot_cell_x + cell_size, y_baseline, font_name, font_size, cell_size)


def generate_pdf(data: Union[SpravkaData, Dict[str, Any]], template_path: str = "assets/example.pdf", signature_path: Optional[str] = "assets/signature.png", output_path: Optional[str] = None) -> bytes:
    """
    Генерирует готовый PDF-документ справки по форме КНД 1151158.
    Если output_path указан, сохраняет файл на диск.
    Возвращает бинарные данные (bytes) готового сжатого PDF.
    """
    if isinstance(data, dict):
        spravka = SpravkaData.from_dict(data)
    else:
        spravka = data

    font_name = FONT_NAME

    # Проверка наличия шаблона бланка
    if not os.path.exists(template_path):
        # Попробуем альтернативные пути
        alt_paths = ["example.pdf", os.path.join(os.path.dirname(__file__), "assets", "example.pdf"), os.path.join(os.path.dirname(__file__), "example.pdf")]
        for ap in alt_paths:
            if os.path.exists(ap):
                template_path = ap
                break
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Файл бланка '{template_path}' не найден.")

    # Проверка наличия подписи
    sig_file = signature_path or spravka.signature_path
    if sig_file and not os.path.exists(sig_file):
        alt_sig = os.path.join(os.path.dirname(__file__), sig_file)
        if os.path.exists(alt_sig):
            sig_file = alt_sig
        else:
            sig_file = None

    pages_count = 2 if spravka.has_page_2 else 1

    # --- СТРАНИЦА 1 (Наложение текста) ---
    packet1 = io.BytesIO()
    c1 = canvas.Canvas(packet1, pagesize=A4)

    # ИНН в шапке (12 клеток)
    _draw_cell_text(c1, spravka.org_inn, 198.42, 814.33, font_name)

    # Номер справки, номер корректировки, отчетный год
    _draw_cell_text(c1, spravka.doc_number, 85.03, 699.03, font_name)
    _draw_cell_text(c1, str(spravka.correction_num), 382.67, 699.03, font_name)
    _draw_cell_text(c1, str(spravka.year), 524.40, 699.03, font_name)

    # Наименование организации / ИП (до 4 строк)
    org_ys = [655.13, 632.43, 609.73, 587.03]
    for idx, line in enumerate(spravka.org_name_lines[:4]):
        if line and line.strip():
            _draw_cell_text(c1, line.strip().upper(), 14.17, org_ys[idx], font_name)

    # Обучение по очной форме (0 - нет, 1 - да)
    _draw_cell_text(c1, str(spravka.full_time), 240.94, 545.39, font_name)

    # Данные налогоплательщика
    _draw_cell_text(c1, spravka.payer_last_name.upper(), 70.86, 503.93, font_name)
    _draw_cell_text(c1, spravka.payer_first_name.upper(), 70.86, 478.43, font_name)
    _draw_cell_text(c1, spravka.payer_middle_name.upper(), 70.86, 452.83, font_name)
    if spravka.payer_inn:
        _draw_cell_text(c1, spravka.payer_inn, 70.86, 427.33, font_name)
    if spravka.payer_birth_date:
        _draw_date_cells(c1, spravka.payer_birth_date, 368.50, 427.33, font_name)

    # Документ налогоплательщика
    _draw_cell_text(c1, spravka.doc_code or '21', 113.38, 381.99, font_name)
    doc_sn = f"{spravka.doc_series} {spravka.doc_num}".strip() if spravka.doc_series and spravka.doc_num else f"{spravka.doc_series}{spravka.doc_num}".strip()
    if doc_sn:
        _draw_cell_text(c1, doc_sn, 297.63, 381.99, font_name)
    if spravka.doc_issue_date:
        _draw_date_cells(c1, spravka.doc_issue_date, 113.38, 356.49, font_name)

    # Налогоплательщик и обучаемый являются одним лицом (0 / 1)
    _draw_cell_text(c1, str(spravka.is_same_person), 269.29, 330.99, font_name)

    # Сумма расходов
    _draw_amount_cells(c1, spravka.amount_rub, spravka.amount_kop, 453.54, 302.23, font_name)

    # Подтверждающее лицо
    _draw_cell_text(c1, spravka.confirm_last_name.upper(), 14.17, 242.33, font_name)
    _draw_cell_text(c1, spravka.confirm_first_name.upper(), 14.17, 219.63, font_name)
    _draw_cell_text(c1, spravka.confirm_middle_name.upper(), 14.17, 196.93, font_name)

    # Факсимиле подписи на странице 1
    if sig_file and os.path.exists(sig_file):
        try:
            c1.drawImage(sig_file, 58.98, 151.47, width=80.09, height=24.23, mask='auto')
        except Exception as e:
            print(f"Предупреждение: не удалось вставить изображение подписи: {e}")

    # Дата справки (стр. 1 в клетки)
    if spravka.doc_date:
        _draw_date_cells(c1, spravka.doc_date, 161.29, 156.53, font_name)

    # Количество страниц
    _draw_cell_text(c1, f"{pages_count:03d}", 127.55, 126.73, font_name)

    c1.showPage()
    c1.save()
    packet1.seek(0)
    overlay_p1 = pypdf.PdfReader(packet1)

    # --- СТРАНИЦА 2 (Наложение текста) ---
    overlay_p2 = None
    if pages_count == 2:
        packet2 = io.BytesIO()
        c2 = canvas.Canvas(packet2, pagesize=A4)

        # ИНН в шапке стр. 2
        _draw_cell_text(c2, spravka.org_inn, 184.25, 814.33, font_name)

        # Данные обучаемого (если не указаны отдельно, берутся из плательщика)
        st_last = (spravka.student_last_name or spravka.payer_last_name).upper()
        st_first = (spravka.student_first_name or spravka.payer_first_name).upper()
        st_mid = (spravka.student_middle_name or spravka.payer_middle_name).upper()
        st_inn = spravka.student_inn or (spravka.payer_inn if spravka.is_same_person else "")
        st_birth = spravka.student_birth_date or spravka.payer_birth_date
        st_code = spravka.student_doc_code or spravka.doc_code or "21"
        st_series = spravka.student_doc_series or (spravka.doc_series if spravka.is_same_person else "")
        st_num = spravka.student_doc_num or (spravka.doc_num if spravka.is_same_person else "")
        st_issue = spravka.student_doc_issue_date or (spravka.doc_issue_date if spravka.is_same_person else "")

        _draw_cell_text(c2, st_last, 70.86, 723.63, font_name)
        _draw_cell_text(c2, st_first, 70.86, 698.13, font_name)
        _draw_cell_text(c2, st_mid, 70.86, 672.63, font_name)
        if st_inn:
            _draw_cell_text(c2, st_inn, 70.86, 647.13, font_name)
        if st_birth:
            _draw_date_cells(c2, st_birth, 368.50, 647.13, font_name)

        _draw_cell_text(c2, st_code, 113.38, 598.93, font_name)
        st_doc_sn = f"{st_series} {st_num}".strip() if st_series and st_num else f"{st_series}{st_num}".strip()
        if st_doc_sn:
            _draw_cell_text(c2, st_doc_sn, 297.63, 598.93, font_name)
        if st_issue:
            _draw_date_cells(c2, st_issue, 113.38, 573.43, font_name)

        # Факсимиле подписи на странице 2
        if sig_file and os.path.exists(sig_file):
            try:
                c2.drawImage(sig_file, 161.09, 13.34, width=62.09, height=18.79, mask='auto')
            except Exception:
                pass

        # Дата внизу страницы 2 (простым текстом ДД.ММ.ГГГГ)
        if spravka.doc_date:
            c2.setFont(font_name, 11)
            c2.drawString(378.00, 16.13, spravka.doc_date)

        c2.showPage()
        c2.save()
        packet2.seek(0)
        overlay_p2 = pypdf.PdfReader(packet2)

    # --- ОБЪЕДИНЕНИЕ С ШАБЛОНОМ И СЖАТИЕ ---
    template_reader = pypdf.PdfReader(template_path)
    writer = pypdf.PdfWriter()

    # Стр 1
    p1 = writer.add_page(template_reader.pages[0])
    p1.merge_page(overlay_p1.pages[0])

    # Стр 2
    if pages_count == 2 and len(template_reader.pages) > 1:
        p2 = writer.add_page(template_reader.pages[1])
        p2.merge_page(overlay_p2.pages[0])

    # Сжатие потоков страниц для минимального веса файла
    for page in writer.pages:
        try:
            page.compress_content_streams()
        except Exception:
            pass

    out_stream = io.BytesIO()
    writer.write(out_stream)
    pdf_bytes = out_stream.getvalue()

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes
