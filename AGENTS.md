# AGENTS.md — กติกาสำหรับผู้พัฒนา/AI ในโปรเจกต์นี้

## ภาษาและ UI

- ข้อความ UI เป็นภาษาไทย หน่วยเป็นอังกฤษ (`V`, `mA`, `µA`, `Ω`, `kΩ`)
- ใช้ HTML/CSS ล้วน ไม่ใช้ JavaScript คำนวณผล

## สถาปัตยกรรม

- `dc_bias.py` = engineering core รับ/คืน **SI units** (V, Ω, A) เท่านั้น
  ห้าม import Flask หรือรู้จัก HTTP/HTML
- `app.py` = HTTP layer: parse ฟอร์ม, แปลง kΩ → Ω, เรียก core, format ผล
- `templates/index.html` = presentation เท่านั้น **ห้ามมีสมการฟิสิกส์หรือเลขคำตอบ**
- `static/style.css` = หน้าตา; ห้ามพึ่งฟอนต์/ไลบรารีภายนอก (ต้องทำงานออฟไลน์)

## รูปแบบโค้ด

- Python 3.10+ syntax, type hints, `from __future__ import annotations`
- ใช้ `unittest` (stdlib) เท่านั้น ไม่เพิ่ม pytest
- ข้อความ validation เป็นภาษาไทยและคงที่ (test อ้างข้อความเหล่านี้)

## การทดสอบ

- ทุกพฤติกรรมใหม่ต้องมี test ก่อน implement (TDD)
- รันทั้งชุดก่อนอ้างว่างานเสร็จ: `python -m unittest discover -s tests -v`
  (หลัง activate venv; ถ้าไม่ activate ใช้ `.venv\Scripts\python.exe -m ...`)
- Test ต้องตรวจค่าจริงจากการคำนวณ ไม่ใช่ค่าที่ copy จาก output

## Git

- ห้าม commit `.venv/`, `.env`, `__pycache__/`, `*.pyc`, API key
- ตรวจ `git status` และ diff ก่อน commit ทุกครั้ง
- ข้อความ commit ภาษาอังกฤษ รูปแบบ `feat:` / `fix:` / `docs:` / `test:`
