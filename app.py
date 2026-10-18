#!/usr/bin/env python3
"""
Локальный веб-сервер приложения SpravkaEduTax.
Запуск веб-интерфейса в браузере.
"""

import http.server
import json
import os
import socketserver
import sys
import urllib.parse
import webbrowser
from typing import Dict, Any

from spravka_engine import generate_pdf, SpravkaData

PORT = 8080
CONFIG_FILE = "config.json"
OUTPUT_DIR = "output"

sys.stdout.reconfigure(encoding='utf-8')


def get_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки config.json: {e}")
    return {}


def save_config(cfg: Dict[str, Any]):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


class SpravkaHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Корневая директория для статики
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "":
            self.send_response(302)
            self.send_header("Location", "/web/index.html")
            self.end_headers()
            return

        if path == "/api/config":
            cfg = get_config()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(cfg, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/last-number":
            cfg = get_config()
            last_num = cfg.get("last_number", 34)
            next_num = f"{last_num + 1:03d}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"next_number": next_num, "last_number": last_num}).encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if path == "/api/config":
            try:
                new_cfg = json.loads(body.decode("utf-8"))
                save_config(new_cfg)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "message": "Настройки сохранены"}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        if path == "/api/generate":
            try:
                data = json.loads(body.decode("utf-8"))
                
                # Определяем сохранение на диск
                save_to_disk = data.get("save_to_disk", True)
                doc_num = data.get("doc_number", "001")
                last_name = data.get("payer_last_name", "клиент")
                
                out_path = None
                if save_to_disk:
                    os.makedirs(OUTPUT_DIR, exist_ok=True)
                    out_path = os.path.join(OUTPUT_DIR, f"{doc_num} {last_name} справка.pdf")

                pdf_bytes = generate_pdf(data, output_path=out_path)

                # Обновляем last_number в config если число больше
                if doc_num.isdigit():
                    num_val = int(doc_num)
                    cfg = get_config()
                    if num_val > cfg.get("last_number", 0):
                        cfg["last_number"] = num_val
                        save_config(cfg)

                ascii_name = f"{doc_num}_spravka.pdf"
                encoded_name = urllib.parse.quote(f"{doc_num}_{last_name}_справка.pdf")
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", f'inline; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded_name}')
                self.send_header("Content-Length", str(len(pdf_bytes)))
                self.end_headers()
                self.wfile.write(pdf_bytes)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        if path == "/api/batch":
            # Пакетная генерация из JSON-массива записей
            try:
                req_data = json.loads(body.decode("utf-8"))
                items = req_data.get("items", [])
                cfg = get_config()
                
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                results = []
                max_num = cfg.get("last_number", 0)

                for item in items:
                    # Слияние со статическими настройками
                    full_item = {**cfg, **item}
                    num = str(full_item.get("doc_number", "")).strip()
                    if not num or num == "None":
                        max_num += 1
                        num = f"{max_num:03d}"
                        full_item["doc_number"] = num
                    elif num.isdigit() and len(num) < 3:
                        num = num.zfill(3)
                        full_item["doc_number"] = num

                    if num.isdigit():
                        max_num = max(max_num, int(num))

                    fname = f"{num} {full_item.get('payer_last_name', 'клиент')} справка.pdf"
                    fpath = os.path.join(OUTPUT_DIR, fname)
                    generate_pdf(full_item, output_path=fpath)
                    results.append({"filename": fname, "number": num, "path": fpath})

                cfg["last_number"] = max_num
                save_config(cfg)

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "count": len(results), "files": results}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


def run_server(port=PORT):
    # Поиск доступного порта
    for p in range(port, port + 20):
        try:
            with socketserver.TCPServer(("", p), SpravkaHandler) as httpd:
                url = f"http://localhost:{p}/web/index.html"
                print("=" * 65)
                print(f"🚀 Генератор справок об оплате образовательных услуг (КНД 1151158)")
                print(f"   Сервер успешно запущен: {url}")
                print(f"   Выходные файлы сохраняются в папку: {os.path.abspath(OUTPUT_DIR)}")
                print(f"   Для остановки нажмите Ctrl + C")
                print("=" * 65)
                try:
                    webbrowser.open(url)
                except Exception:
                    pass
                httpd.serve_forever()
                break
        except OSError:
            continue


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
