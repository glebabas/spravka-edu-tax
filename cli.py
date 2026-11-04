#!/usr/bin/env python3
"""
CLI инструмент для пакетной и одиночной генерации справок КНД 1151158.
"""

import argparse
import csv
import json
import os
import sys
from typing import List, Dict, Any

from spravka_engine import generate_pdf, SpravkaData

sys.stdout.reconfigure(encoding='utf-8')


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config_data: Dict[str, Any], config_path: str = "config.json"):
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)


def generate_single_from_args(args, cfg: Dict[str, Any]):
    # Базовые статические данные из конфигурации
    data = {
        "org_inn": cfg.get("org_inn", "773610841807"),
        "org_kpp": cfg.get("org_kpp", ""),
        "org_name_lines": cfg.get("org_name_lines", []),
        "full_time": cfg.get("full_time", 0),
        "confirm_last_name": cfg.get("confirm_last_name", "БУРЛАКОВ"),
        "confirm_first_name": cfg.get("confirm_first_name", "НИКИТА"),
        "confirm_middle_name": cfg.get("confirm_middle_name", "СЕРГЕЕВИЧ"),
        "signature_path": cfg.get("signature_path", "assets/signature.png"),
        "doc_number": args.number or f"{cfg.get('last_number', 34) + 1:03d}",
        "correction_num": args.correction,
        "year": args.year or cfg.get("default_year", 2025),
        "doc_date": args.date or "01.07.2026",
        "payer_last_name": args.last_name or "",
        "payer_first_name": args.first_name or "",
        "payer_middle_name": args.middle_name or "",
        "payer_inn": args.inn or "",
        "payer_birth_date": args.birth_date or "",
        "doc_code": args.doc_code or "21",
        "doc_series": args.doc_series or "",
        "doc_num": args.doc_num or "",
        "doc_issue_date": args.doc_issue_date or "",
        "amount_rub": args.amount or 0,
        "amount_kop": args.kop or 0,
        "is_same_person": 1,
        "has_page_2": True,
    }

    # Если ФИО передано одной строкой через --fio
    if args.fio:
        parts = args.fio.strip().split()
        if len(parts) >= 1:
            data["payer_last_name"] = parts[0]
        if len(parts) >= 2:
            data["payer_first_name"] = parts[1]
        if len(parts) >= 3:
            data["payer_middle_name"] = " ".join(parts[2:])

    # Если паспорт передан одной строкой через --passport
    if args.passport:
        p_parts = args.passport.strip().split()
        if len(p_parts) >= 2:
            data["doc_series"] = p_parts[0]
            data["doc_num"] = "".join(p_parts[1:])
        elif len(args.passport.strip()) == 10:
            data["doc_series"] = args.passport.strip()[:4]
            data["doc_num"] = args.passport.strip()[4:]

    out_file = args.out
    name_part = data["payer_last_name"] or "клиент"
    default_filename = f"{data['doc_number']} {name_part} справка.pdf"
    if not out_file:
        out_file = os.path.join("output", default_filename)
    elif os.path.isdir(out_file):
        out_file = os.path.join(out_file, default_filename)

    print(f"Генерация справки № {data['doc_number']} для {data['payer_last_name']} {data['payer_first_name']}...")
    generate_pdf(data, output_path=out_file)
    print(f"✓ Файл успешно сохранен: {out_file}")

    # Обновление last_number
    if data['doc_number'].isdigit():
        num_int = int(data['doc_number'])
        if num_int > cfg.get('last_number', 0):
            cfg['last_number'] = num_int
            save_config(cfg)


def get_field_val(rec: Dict[str, Any], *patterns) -> Any:
    """Поиск значения по частичному совпадению названий колонок."""
    for p in patterns:
        p_lower = p.lower()
        for k, v in rec.items():
            if k and p_lower in str(k).lower():
                return v
    return ""


def generate_batch(file_path: str, out_dir: str, cfg: Dict[str, Any]):
    if not os.path.exists(file_path):
        print(f"Ошибка: файл '{file_path}' не найден!")
        return

    os.makedirs(out_dir, exist_ok=True)
    records = []

    if file_path.endswith('.xlsx'):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                print("Таблица пуста.")
                return
            headers = [str(h).strip().lower() if h else "" for h in rows[0]]
            for r in rows[1:]:
                if not any(r):
                    continue
                row_dict = {}
                for h, val in zip(headers, r):
                    row_dict[h] = val
                records.append(row_dict)
        except Exception as e:
            print(f"Ошибка чтения Excel: {e}")
            return
    elif file_path.endswith('.csv'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = list(reader)
        except Exception as e:
            print(f"Ошибка чтения CSV: {e}")
            return
    else:
        print("Поддерживаются только форматы .xlsx и .csv")
        return

    print(f"Найдено записей для генерации: {len(records)}")
    success_count = 0
    max_num = cfg.get('last_number', 0)

    for idx, raw_rec in enumerate(records, 1):
        rec = {str(k).lower().strip(): v for k, v in raw_rec.items() if k is not None}

        # Определение номера справки
        num_raw = get_field_val(rec, 'number', 'номер справки', 'номер')
        num = str(num_raw).strip() if num_raw is not None else ""
        if not num or num == 'None':
            max_num += 1
            num = f"{max_num:03d}"
        elif num.isdigit() and len(num) < 3:
            num = num.zfill(3)

        if num.isdigit():
            max_num = max(max_num, int(num))

        # ФИО
        last_name = str(get_field_val(rec, 'last_name', 'фамилия') or "").strip()
        first_name = str(get_field_val(rec, 'first_name', 'имя') or "").strip()
        middle_name = str(get_field_val(rec, 'middle_name', 'отчество') or "").strip()
        fio_raw = str(get_field_val(rec, 'fio', 'фио') or "").strip()
        if fio_raw and not last_name:
            f_parts = fio_raw.split()
            if len(f_parts) >= 1:
                last_name = f_parts[0]
            if len(f_parts) >= 2:
                first_name = f_parts[1]
            if len(f_parts) >= 3:
                middle_name = " ".join(f_parts[2:])

        # Паспорт
        passport = str(get_field_val(rec, 'passport', 'паспорт') or "").strip()
        series = str(get_field_val(rec, 'doc_series', 'серия') or "").strip()
        p_num = str(get_field_val(rec, 'doc_num', 'номер паспорта') or "").strip()
        if passport and (not series or not p_num):
            clean_p = passport.replace('-', ' ').strip()
            parts = clean_p.split()
            if len(parts) >= 2:
                series = parts[0]
                p_num = "".join(parts[1:])
            elif len(clean_p) == 10 and clean_p.isdigit():
                series = clean_p[:4]
                p_num = clean_p[4:]

        # Сумма
        amt_raw = get_field_val(rec, 'amount', 'сумма')

        # Даты
        b_date = str(get_field_val(rec, 'birth_date', 'дата рождения', 'рождения') or "").strip()
        issue_date = str(get_field_val(rec, 'issue_date', 'дата выдачи паспорта', 'дата выдачи', 'выдачи') or "").strip()
        doc_date = str(get_field_val(rec, 'doc_date', 'дата справки', 'дата') or "01.07.2026").strip()
        year_val = get_field_val(rec, 'year', 'отчетный год', 'год') or cfg.get('default_year', 2025)

        item_data = {
            "org_inn": cfg.get("org_inn", "773610841807"),
            "org_kpp": cfg.get("org_kpp", ""),
            "org_name_lines": cfg.get("org_name_lines", []),
            "full_time": cfg.get("full_time", 0),
            "confirm_last_name": cfg.get("confirm_last_name", "БУРЛАКОВ"),
            "confirm_first_name": cfg.get("confirm_first_name", "НИКИТА"),
            "confirm_middle_name": cfg.get("confirm_middle_name", "СЕРГЕЕВИЧ"),
            "signature_path": cfg.get("signature_path", "assets/signature.png"),
            "doc_number": num,
            "correction_num": int(rec.get('correction', rec.get('корректировка', 0)) or 0),
            "year": int(year_val or 2025),
            "doc_date": doc_date,
            "payer_last_name": last_name,
            "payer_first_name": first_name,
            "payer_middle_name": middle_name,
            "payer_inn": str(rec.get('inn', rec.get('инн', ''))).strip(),
            "payer_birth_date": b_date,
            "doc_code": str(rec.get('doc_code', '21')),
            "doc_series": series,
            "doc_num": p_num,
            "doc_issue_date": issue_date,
            "amount": amt_raw,
            "is_same_person": 1,
            "has_page_2": True,
        }

        filename = f"{num} {last_name or 'клиент'} справка.pdf"
        out_path = os.path.join(out_dir, filename)

        try:
            generate_pdf(item_data, output_path=out_path)
            print(f"[{idx}/{len(records)}] Создана справка: {filename}")
            success_count += 1
        except Exception as err:
            print(f"[{idx}/{len(records)}] Ошибка создания {filename}: {err}")

    cfg['last_number'] = max_num
    save_config(cfg)
    print(f"\nГотово! Успешно создано {success_count} из {len(records)} файлов в папке '{out_dir}'.")


def main():
    parser = argparse.ArgumentParser(description="Генератор справок об оплате образовательных услуг КНД 1151158")
    parser.add_argument("--batch", "-b", help="Путь к файлу Excel (.xlsx) или CSV для пакетной генерации")
    parser.add_argument("--out", "-o", help="Выходной файл или каталог (по умолчанию output/)")
    parser.add_argument("--config", "-c", default="config.json", help="Путь к файлу конфигурации (по умолчанию config.json)")

    # Параметры для одиночной генерации
    parser.add_argument("--number", "-n", help="Номер справки (например, 035)")
    parser.add_argument("--fio", help="ФИО клиента одной строкой")
    parser.add_argument("--last-name", help="Фамилия")
    parser.add_argument("--first-name", help="Имя")
    parser.add_argument("--middle-name", help="Отчество")
    parser.add_argument("--birth-date", help="Дата рождения (ДД.ММ.ГГГГ)")
    parser.add_argument("--passport", help="Паспорт: серия и номер (например, '4508 123456')")
    parser.add_argument("--doc-series", help="Серия паспорта (4 цифры)")
    parser.add_argument("--doc-num", help="Номер паспорта (6 цифр)")
    parser.add_argument("--doc-issue-date", help="Дата выдачи паспорта (ДД.ММ.ГГГГ)")
    parser.add_argument("--doc-code", default="21", help="Код документа (по умолчанию 21)")
    parser.add_argument("--inn", default="", help="ИНН плательщика (при наличии)")
    parser.add_argument("--amount", type=int, default=0, help="Сумма в рублях")
    parser.add_argument("--kop", type=int, default=0, help="Копейки (0..99)")
    parser.add_argument("--year", type=int, help="Отчетный год")
    parser.add_argument("--date", help="Дата составления справки (ДД.ММ.ГГГГ)")
    parser.add_argument("--correction", type=int, default=0, help="Номер корректировки (0..)")

    args = parser.parse_args()
    cfg = load_config(args.config)

    if args.batch:
        out_dir = args.out or "output"
        generate_batch(args.batch, out_dir, cfg)
    elif args.last_name or args.fio:
        generate_single_from_args(args, cfg)
    else:
        # Если аргументы не переданы, показываем справку
        parser.print_help()


if __name__ == "__main__":
    main()
