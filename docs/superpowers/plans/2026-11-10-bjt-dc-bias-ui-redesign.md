# Single-screen layout + dynamic circuit diagram — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ทำให้หน้าเว็บแสดง Input / Circuit / Results เรียง 3 คอลัมน์ในจอเดียว พร้อมรูปวงจรที่กำกับค่าจริงจากฟอร์ม

**Architecture:** ค่าทั้งหมดสำหรับแสดงผล (label วงจร + ข้อความสถานะ) ถูกเตรียมใน `app.py` เป็นสตริง แล้ว template วางลง SVG/HTML ตรง ๆ — ไม่มี JavaScript, ไม่มีตัวเลขฝังใน template, core `dc_bias.py` ไม่ถูกแตะ

**Tech Stack:** Python 3.14 + Flask 3.1.3 + Jinja2 + inline SVG + CSS Grid + unittest

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-ui-redesign-design.md`

## Global Constraints

- UI ภาษาไทย หน่วยอังกฤษ (`V`, `mA`, `µA`, `Ω`, `kΩ`)
- ห้ามใช้ JavaScript คำนวณ/แสดงผล และห้ามพึ่งฟอนต์หรือไลบรารีภายนอก
- template ห้ามมีสมการฟิสิกส์หรือเลขคำตอบ (`1.942`, `8.052`, …)
- `dc_bias.py` ยังเป็น SI-only และไม่ import Flask
- ใช้ `unittest` เท่านั้น; รันด้วย `.venv\Scripts\python.exe -m unittest discover -s tests -v`
- ชื่อ field ฟอร์มเดิม: `vcc, r1, r2, rc, re, beta, vbe, unit`

## Review Focus

1. **จอ 1366×768 ต้องเห็นครบ 3 panel โดยไม่ต้องเลื่อน** — วัดด้วย screenshot จริง (Task 3)
2. **ค่าที่โชว์ในวงจรต้องตรงช่องที่กรอก** (สลับ R1/R2 หรือหน่วยผิดจะหลุดง่ายที่สุด) — test ใน Task 2
3. **ช่องว่าง/ค่าที่ใช้ไม่ได้ต้องขึ้น `—` ไม่ใช่ `None`, ไม่ใช่ `0 kΩ`, และไม่ทำให้หน้า 500** — test ใน Task 1
4. **ก่อนกด Calculate ต้องไม่มีเลขคำตอบและความสูงหน้าต้องไม่กระโดด** — test ใน Task 2
5. **สถานะต้องไม่ขัดกับ region ของ core** (cutoff ต้องไม่ขึ้นเขียว Active) — test ใน Task 1

---

### Task 1: Backend display helpers

**Files:**
- Modify: `app.py`
- Test: `tests/test_web.py`

**Interfaces:**
- Produces:
  - `_diagram_labels(form: Mapping[str, str]) -> dict[str, str]` คืน key `vcc, r1, r2, rc, re, beta` เป็นสตริงพร้อมหน่วย (`"12 V"`, `"100 kΩ"`, `"β = 100"`); ช่องว่าง → `"—"`; หน่วยเป็น `Ω` เมื่อ `form["unit"] == "ohm"` เท่านั้น
  - `_status_note(result: DcBiasResult) -> dict[str, str]` คืน `{"tone": "ok"|"warn"|"danger", "text": str}`

- [ ] **Step 1: เขียน failing tests**

เพิ่มใน `tests/test_web.py`:

```python
from app import _diagram_labels, _status_note, create_app
from dc_bias import DcBiasInput, calculate_dc_bias

class TestDiagramLabels(unittest.TestCase):
    def test_defaults_use_kohm_unit(self):
        labels = _diagram_labels({"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
                                  "re": "1", "beta": "100", "unit": "kohm"})
        self.assertEqual(labels["vcc"], "12 V")
        self.assertEqual(labels["r1"], "100 kΩ")
        self.assertEqual(labels["beta"], "β = 100")

    def test_ohm_unit_changes_suffix(self):
        labels = _diagram_labels({"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
                                  "re": "1", "beta": "100", "unit": "ohm"})
        self.assertEqual(labels["r1"], "100 Ω")

    def test_blank_field_becomes_dash(self):
        labels = _diagram_labels({"vcc": "12", "r1": "", "r2": "22", "rc": "2.2",
                                  "re": "1", "beta": "100", "unit": "kohm"})
        self.assertEqual(labels["r1"], "—")

class TestStatusNote(unittest.TestCase):
    def test_active_is_ok(self):
        note = _status_note(calculate_dc_bias(DcBiasInput(12.0, 100e3, 22e3, 2.2e3, 1e3, 100.0, 0.70)))
        self.assertEqual(note["tone"], "ok")
        self.assertIn("Active", note["text"])

    def test_cutoff_is_danger_not_ok(self):
        note = _status_note(calculate_dc_bias(DcBiasInput(12.0, 100e3, 1e3, 2.2e3, 1e3, 100.0, 0.70)))
        self.assertEqual(note["tone"], "danger")
        self.assertIn("Cutoff", note["text"])
        self.assertNotIn("Active", note["text"])
```

- [ ] **Step 2: รันให้ fail**

Run: `.venv\Scripts\python.exe -m unittest tests.test_web -v`
Expected: ImportError `cannot import name '_diagram_labels'`

- [ ] **Step 3: implement ใน `app.py`**

`_diagram_labels` ใช้ข้อความดิบจากฟอร์ม (ไม่ parse) เพื่อให้ตรงกับช่องกรอก, ตัดช่องว่างด้วย `.strip()`, ค่าว่าง → `"—"`, หน่วย `"Ω"` เมื่อ `unit == "ohm"` ไม่เช่นนั้น `"kΩ"`

`_status_note` แปลง `result.region` เป็น tone/text ภาษาไทย โดยอ้าง `VCE` จากผลลัพธ์ (ห้าม hardcode เลขคำตอบ):
`active → ok`, `near-saturation → warn`, `saturation|cutoff → danger`; ข้อความต้องมีชื่อ region ภาษาอังกฤษ (Active / Near Saturation / Saturation / Cutoff)

- [ ] **Step 4: รันให้ pass**

Run: `.venv\Scripts\python.exe -m unittest tests.test_web -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_web.py
git commit -m "feat: add diagram label and status note helpers"
```

---

### Task 2: 3-panel template + inline SVG + results table

**Files:**
- Modify: `templates/index.html`, `app.py` (ส่ง `diagram`, `status`)
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `_diagram_labels`, `_status_note` จาก Task 1; `_format_result` เดิม
- Produces (ให้ Task 3 ผูก CSS): `.workspace`, `.panel`, `.panel-input`, `.panel-circuit`, `.panel-results`, `<svg class="schematic">`, `<table class="results-table">`, `.status.status-{tone}`, `.status-idle`

- [ ] **Step 1: เขียน failing tests**

```python
class TestSingleScreenLayout(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        self.valid = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
                      "re": "1", "beta": "100", "vbe": "0.70", "unit": "kohm"}

    def test_get_renders_three_panels_and_svg(self):
        body = self.client.get("/").get_data(as_text=True)
        for cls in ("panel-input", "panel-circuit", "panel-results"):
            self.assertIn(cls, body)
        self.assertIn("<svg", body)
        self.assertIn("schematic", body)

    def test_get_shows_default_labels_in_circuit(self):
        body = self.client.get("/").get_data(as_text=True)
        for text in ("12 V", "100 kΩ", "22 kΩ", "2.2 kΩ", "1 kΩ", "β = 100"):
            self.assertIn(text, body)

    def test_post_updates_circuit_labels(self):
        body = self.client.post("/calculate", data=dict(self.valid, r1="47")).get_data(as_text=True)
        self.assertIn("47 kΩ", body)
        self.assertNotIn("100 kΩ", body)

    def test_ohm_mode_updates_circuit_labels(self):
        body = self.client.post("/calculate", data=dict(self.valid, unit="ohm")).get_data(as_text=True)
        self.assertIn("100 Ω", body)
        self.assertNotIn("100 kΩ", body)

    def test_blank_field_renders_dash_not_none(self):
        body = self.client.post("/calculate", data=dict(self.valid, r2="")).get_data(as_text=True)
        self.assertIn("—", body)
        self.assertNotIn(">None<", body)

    def test_get_has_no_answer_numbers(self):
        body = self.client.get("/").get_data(as_text=True)
        for leak in ("1.942", "8.052", "9.294"):
            self.assertNotIn(leak, body)

    def test_get_shows_idle_status_and_dashes(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("status-idle", body)
        self.assertIn("—", body)

    def test_post_shows_active_status(self):
        body = self.client.post("/calculate", data=self.valid).get_data(as_text=True)
        self.assertIn("status-ok", body)
        self.assertIn("Active", body)

    def test_cutoff_shows_danger_status(self):
        body = self.client.post("/calculate", data=dict(self.valid, r2="1")).get_data(as_text=True)
        self.assertIn("status-danger", body)
```

- [ ] **Step 2: รันให้ fail**

Run: `.venv\Scripts\python.exe -m unittest tests.test_web -v`
Expected: FAIL — ไม่พบ `panel-input` / `<svg`

- [ ] **Step 3: แก้ `app.py` ให้ส่ง context**

ทั้ง `index` และ `calculate` ส่ง `diagram=_diagram_labels(form)`; `calculate` ส่ง `status=_status_note(result)` (index ส่ง `status=None`, `values=None`, `result=None`)

- [ ] **Step 4: เขียน template ใหม่**

โครง: header บรรทัดเดียว → `{% if error %}` → `<div class="workspace">` 3 panel
- panel-input: ฟอร์มเดิมทั้งก้อน (ไม่เปลี่ยน `name`)
- panel-circuit: `<svg class="schematic" viewBox="0 0 360 400">` วาดราง VCC, R1/R2 ฝั่งซ้าย, RC ฝั่งขวา, Q1 กลางล่าง, RE ใต้ emitter, สัญลักษณ์ ground 3 จุด และ `<text>` ที่ผูก `{{ diagram.vcc }}`, `{{ diagram.r1 }}` …, `{{ diagram.beta }}`
- panel-results: `<table class="results-table">` 7 แถว โดยค่าใช้ `{{ values.vb if values else '—' }}` และหน่วยท้ายค่า; กล่องสถานะ `{% if status %}<div class="status status-{{ status.tone }}">{{ status.text }}</div>{% else %}<div class="status status-idle">กด Calculate DC Bias เพื่อคำนวณ</div>{% endif %}`; `<details class="working">วิธีคำนวณ</details>` เหมือนเดิม
- ลบ `{% for warning in result.warnings %}` เดิม (ข้อความสถานะแทนแล้ว)

- [ ] **Step 5: รันให้ pass**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `OK` (test เดิมต้องไม่พัง)

- [ ] **Step 6: Commit**

```bash
git add app.py templates/index.html tests/test_web.py
git commit -m "feat: render three-panel layout with dynamic circuit diagram"
```

---

### Task 3: CSS จอเดียว + ตรวจ screenshot + เอกสาร

**Files:**
- Modify: `static/style.css`, `README.md`
- Create: ไม่มี
- Test: ตรวจด้วยตา (screenshot 1366×768) + suite เดิม

**Interfaces:**
- Consumes: class names จาก Task 2

- [ ] **Step 1: เขียน CSS**

- `.workspace`: `display:grid; grid-template-columns:minmax(280px,.95fr) minmax(320px,1.1fr) minmax(300px,1fr); gap:16px; max-width:1400px`
- `@media (max-width:1099px)`: `grid-template-columns:1fr`
- `.panel`: พื้นขาว ขอบมน 10px padding 16–20px; หัว panel `.panel-head` เป็น flex + ไอคอน SVG 18px
- ฟอร์มภายใน panel: label/input เป็นแถวเดียว (grid `1fr auto`) เพื่อลดความสูง; ปุ่มเต็มความกว้าง
- `.schematic`: `width:100%; height:auto; max-height:340px`
- `.results-table`: กว้าง 100%, แถวสลับสี `nth-child(odd)`, ค่าชิดขวา ตัวหนา สี navy
- `.status`: `ok` เขียว, `warn` ส้ม, `danger` แดง, `idle` เทา
- header กระชับ: `padding:16px`, h1 `1.25rem`, subtitle บรรทัดเดียว

- [ ] **Step 2: ตรวจ suite**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `OK`

- [ ] **Step 3: ตรวจ screenshot 1366×768**

เปิด `.venv\Scripts\python.exe -m flask --app app run --port 5000` แล้ว capture ที่ viewport 1366×768 ทั้ง状態 GET และหลัง POST
Expected: เห็นครบ 3 panel, ไม่มี scrollbar แนวตั้ง

- [ ] **Step 4: อัปเดต README**

เพิ่มหัวข้อ "หน้าจอ" อธิบาย 3 panel, วงจรอัปเดตตามค่าที่กรอก, และ responsive (<1100px เรียงลง)

- [ ] **Step 5: Commit**

```bash
git add static/style.css README.md
git commit -m "feat: fit input, circuit and results on one screen"
```
