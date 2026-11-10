# BJT DC Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้าง Flask Web App หลายไฟล์ที่รับค่า VCC, R1, R2, RC, RE, β, VBE แล้วคำนวณ DC Operating Point ของ BJT Voltage-Divider Bias พร้อม validation, region warning และชุดทดสอบอัตโนมัติ

**Architecture:** แยก engineering core (`dc_bias.py`, SI units, ไม่รู้จัก HTTP) ออกจาก HTTP layer (`app.py`, Flask factory + Jinja) และ presentation (`templates/index.html`, `static/style.css`) ทดสอบด้วย `unittest` ทั้งระดับสมการและระดับ HTTP

**Tech Stack:** Python 3.14.2, Flask 3.1.3, Jinja2, `unittest` (stdlib), HTML/CSS ไม่มี JavaScript คำนวณ

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md`

## Global Constraints

- ทำงานที่ root ของ repo: `C:\Users\B6815233\Documents\GitHub\BJT DC Bias Web App`
- ใช้ `py -3` (Python 3.14.2) — คำสั่ง `python` บนเครื่องนี้เป็น Microsoft Store stub
- `requirements.txt` ต้องมี `Flask==3.1.3` เท่านั้น
- `dc_bias.py` รับ **SI units** (V, Ω, A) เท่านั้น; การแปลง kΩ → Ω เกิดใน `app.py`
- UI ภาษาไทย หน่วยอังกฤษ: `V`, `mA`, `µA`, `Ω`, `kΩ`
- ห้ามมีตัวเลขคำตอบใน template และห้ามคำนวณผลด้วย JavaScript
- Validation/parse error ต้องคืน **HTTP 200** พร้อมข้อความ ไม่Throw 500
- ใช้ `unittest` เท่านั้น (ไม่มี pytest)
- **ยังไม่ commit ระหว่างทาง** — เจ้าของงาน commit ครั้งเดียวผ่าน GitHub Desktop เมื่อจบ (execution choice C)
- ห้ามสร้าง/commit `.venv/`, `.env`, `__pycache__/`, `*.pyc`
- ค่าคงที่ region: `VCE_SAT = 0.2`, `VCE_NEAR_SAT = 0.5`

## Review Focus

1. **`VTH ≤ VBE` (Cutoff)** — ผู้ใช้กรอก R2 เล็กมากแล้วได้ IB ติดลบ; ต้อง clamp กระแสเป็น 0 และขึ้น warning ไม่ใช่แสดงค่าติดลบ (Task 3)
2. **อินพุตไม่ใช่ตัวเลข/ว่าง เช่น `abc`, ``, `1,5`** — ต้องได้ข้อความ error ภาษาไทย ไม่ใช่ 500 (Task 5)
3. **ปนหน่วย Ω กับ kΩ** — เลือกหน่วยผิดต้องไม่เงียบ ๆ ให้ผลต่าง 1000 เท่า; ทดสอบ conversion ตรง ๆ (Task 5)
4. **ขอบเขต Saturation 0.2 V** — ค่า `VCE` เท่ากับ 0.2 พอดีต้องจัดเป็น near-saturation ไม่ใช่ saturation (Task 3)
5. **`VBE ≥ VCC`** — ต้องถูกปฏิเสธก่อนคำนวณ ไม่ปล่อยให้ได้ IB ติดลบ (Task 2)

---

### Task 1: Engineering core — ค่าอ้างอิง

**Files:**
- Create: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) DcBiasInput(vcc: float, r1: float, r2: float, rc: float, re: float, beta: float, vbe: float)`
  - `@dataclass(frozen=True) DcBiasResult(vth, rth, ib, ic, ie, vb, ve, vc, vce: float, region: str, warnings: tuple[str, ...])`
  - `calculate_dc_bias(inp: DcBiasInput) -> DcBiasResult`
  - `class ValidationError(ValueError)`

- [ ] **Step 1: เขียน failing test**

```python
import unittest
from dc_bias import DcBiasInput, calculate_dc_bias

class TestReferenceCase(unittest.TestCase):
    def test_voltage_divider_reference_case(self):
        res = calculate_dc_bias(DcBiasInput(12.0, 100e3, 22e3, 2.2e3, 1e3, 100.0, 0.70))
        self.assertAlmostEqual(res.vth, 2.163934, places=6)
        self.assertAlmostEqual(res.rth, 18032.786885, places=3)
        self.assertAlmostEqual(res.ib, 12.298581e-6, places=10)
        self.assertAlmostEqual(res.ic, 1.229858e-3, places=8)
        self.assertAlmostEqual(res.ie, 1.242157e-3, places=8)
        self.assertAlmostEqual(res.vb, 1.942157, places=6)
        self.assertAlmostEqual(res.ve, 1.242157, places=6)
        self.assertAlmostEqual(res.vc, 9.294312, places=6)
        self.assertAlmostEqual(res.vce, 8.052155, places=6)
        self.assertEqual(res.region, "active")
        self.assertEqual(res.warnings, ())
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `py -3 -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dc_bias'`

- [ ] **Step 3: implement `dc_bias.py`**

สร้าง dataclasses ตาม Interfaces และฟังก์ชันที่ใช้สมการ:
`VTH = vcc*r2/(r1+r2)`, `RTH = r1*r2/(r1+r2)`, `IB = (vth-vbe)/(rth+(beta+1)*re)`,
`IC = beta*ib`, `IE = (beta+1)*ib`, `VE = ie*re`, `VB = ve+vbe`, `VC = vcc-ic*rc`, `VCE = vc-ve`
ตั้ง `region="active"`, `warnings=()` ไว้ก่อน (Task 3 เติม logic)

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `py -3 -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: `OK` 1 test

---

### Task 2: Core validation

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: `DcBiasInput`, `calculate_dc_bias`, `ValidationError` จาก Task 1
- Produces: ข้อความ error คงที่ (ใช้ตรวจใน Task 5 ด้วย)
  - `"VCC ต้องมากกว่า 0"`
  - `"R1, R2, RC, RE ต้องมากกว่า 0"`
  - `"β ต้องมากกว่า 0"`
  - `"VBE ต้องมากกว่า 0 และน้อยกว่า VCC"`

- [ ] **Step 1: เขียน failing tests**

```python
from dataclasses import replace
from dc_bias import DcBiasInput, ValidationError, calculate_dc_bias

BASE = DcBiasInput(12.0, 100e3, 22e3, 2.2e3, 1e3, 100.0, 0.70)

class TestValidation(unittest.TestCase):
    def assert_rejects(self, field, value, message):
        with self.assertRaises(ValidationError) as ctx:
            calculate_dc_bias(replace(BASE, **{field: value}))
        self.assertIn(message, str(ctx.exception))

    def test_zero_vcc(self):
        self.assert_rejects("vcc", 0.0, "VCC ต้องมากกว่า 0")

    def test_zero_r1(self):
        self.assert_rejects("r1", 0.0, "R1, R2, RC, RE ต้องมากกว่า 0")

    def test_negative_r2(self):
        self.assert_rejects("r2", -1.0, "R1, R2, RC, RE ต้องมากกว่า 0")

    def test_zero_beta(self):
        self.assert_rejects("beta", 0.0, "β ต้องมากกว่า 0")

    def test_vbe_not_below_vcc(self):
        self.assert_rejects("vbe", 12.0, "VBE ต้องมากกว่า 0 และน้อยกว่า VCC")
```

- [ ] **Step 2: รันให้ fail**

Run: `py -3 -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: FAIL — ไม่มี `ValidationError`

- [ ] **Step 3: เพิ่ม guard ที่ต้นฟังก์ชัน `calculate_dc_bias`**

ตรวจตามลำดับ: `vcc > 0`, `r1 > 0 and r2 > 0 and rc > 0 and re > 0`, `beta > 0`, `0 < vbe < vcc`
ถ้าไม่ผ่าน `raise ValidationError(<ข้อความคงที่>)`

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `py -3 -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: `OK` 6 tests

---

### Task 3: Region detection + warnings

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Produces: `classify_region(vth: float, vbe: float, vce: float) -> tuple[str, tuple[str, ...]]`
  - คืน `(region, warnings)` โดย `region ∈ {"cutoff", "saturation", "near-saturation", "active"}`
- `calculate_dc_bias` ใช้ `classify_region` และเมื่อ `region == "cutoff"` ให้ clamp
  `ib=ic=ie=0.0`, `ve=0.0`, `vb=vth`, `vc=vcc`, `vce=vcc`

- [ ] **Step 1: เขียน failing tests**

```python
from dc_bias import DcBiasInput, calculate_dc_bias, classify_region

class TestRegion(unittest.TestCase):
    def test_cutoff_clamps_currents(self):
        res = calculate_dc_bias(DcBiasInput(12.0, 100e3, 1e3, 2.2e3, 1e3, 100.0, 0.70))
        self.assertEqual(res.region, "cutoff")
        self.assertEqual((res.ib, res.ic, res.ie), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(res.vce, 12.0, places=9)
        self.assertTrue(any("Cutoff" in w for w in res.warnings))

    def test_saturation_warns(self):
        res = calculate_dc_bias(DcBiasInput(12.0, 10e3, 10e3, 10e3, 100.0, 100.0, 0.70))
        self.assertLess(res.vce, 0.2)
        self.assertEqual(res.region, "saturation")
        self.assertTrue(any("Saturation" in w for w in res.warnings))

    def test_near_saturation_warns(self):
        res = calculate_dc_bias(DcBiasInput(12.0, 100e3, 22e3, 1500.0, 10.0, 100.0, 0.70))
        self.assertGreaterEqual(res.vce, 0.2)
        self.assertLess(res.vce, 0.5)
        self.assertEqual(res.region, "near-saturation")
        self.assertTrue(any("Saturation" in w for w in res.warnings))

    def test_vce_boundary_at_02_is_near_saturation(self):
        self.assertEqual(classify_region(2.0, 0.7, 0.199)[0], "saturation")
        self.assertEqual(classify_region(2.0, 0.7, 0.2)[0], "near-saturation")
        self.assertEqual(classify_region(2.0, 0.7, 0.5)[0], "active")

    def test_cutoff_checked_before_saturation(self):
        self.assertEqual(classify_region(0.5, 0.7, 0.1)[0], "cutoff")
```

- [ ] **Step 2: รันให้ fail**

Run: `py -3 -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: FAIL — `cannot import name 'classify_region'`

- [ ] **Step 3: implement `classify_region` และต่อเข้ากับ `calculate_dc_bias`**

ลำดับการตัดสิน: `vth <= vbe` → cutoff; `vce < VCE_SAT` → saturation;
`vce < VCE_NEAR_SAT` → near-saturation; else active
ข้อความ warning ต้องมีคำว่า `Cutoff` หรือ `Saturation` ตามกรณี (ภาษาไทยต่อท้ายได้)

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `py -3 -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: `OK` 11 tests

---

### Task 4: Flask skeleton + ฟอร์ม (GET /)

**Files:**
- Create: `app.py`, `requirements.txt`, `templates/index.html`, `tests/test_web.py`

**Interfaces:**
- Produces: `create_app() -> Flask` และ module-level `app = create_app()`
- Template ต้องมี `input` ที่มี `name` = `vcc, r1, r2, rc, re, beta, vbe` และ `select name="unit"` (`ohm`/`kohm`, default `kohm`)

- [ ] **Step 1: เขียน failing test**

```python
import unittest
from app import create_app

class TestHomePage(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_home_returns_form(self):
        res = self.client.get("/")
        body = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 200)
        for field in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
            self.assertIn(f'name="{field}"', body)
        self.assertIn('name="unit"', body)
        self.assertIn("Calculate DC Bias", body)
```

- [ ] **Step 2: รันให้ fail**

Run: `py -3 -m unittest discover -s tests -p "test_web.py" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: สร้าง `requirements.txt`, `app.py`, `templates/index.html`**

- `requirements.txt`: `Flask==3.1.3`
- `app.py`: `create_app()` ผูก route `GET /` → `render_template("index.html")`; ค่าเริ่มต้นในฟอร์ม = `12, 100, 22, 2.2, 1, 100, 0.70`, หน่วย `kohm`
- `templates/index.html`: ฟอร์ม `method="post" action="/calculate"` พร้อม label/หน่วย, ปุ่มข้อความ `Calculate DC Bias`, ยังไม่ต้องมีผลลัพธ์

- [ ] **Step 4: ติดตั้ง Flask แล้วรัน test**

Run: `py -3 -m pip install -r requirements.txt`
Run: `py -3 -m unittest discover -s tests -p "test_web.py" -v`
Expected: `OK` 1 test

---

### Task 5: POST /calculate + แปลงหน่วย + parse error

**Files:**
- Modify: `app.py`, `templates/index.html`
- Test: `tests/test_web.py`

**Interfaces:**
- Produces:
  - `_parse_float(raw: str, label: str) -> float` — ว่าง/ไม่ใช่ตัวเลข → `ValueError(f"กรุณากรอก {label} เป็นตัวเลข")`
  - `_to_ohms(raw: str, unit: str, label: str) -> float` — `unit == "kohm"` คูณ 1000
  - `_format_result(res: DcBiasResult) -> dict[str, str]` — key: `vb, ve, vc, vce` (3 ตำแหน่ง), `ic, ie` (3 ตำแหน่ง), `ib` (2 ตำแหน่ง), `vth` (3 ตำแหน่ง), `rth` (2 ตำแหน่ง, หน่วย kΩ)
- Route: `POST /calculate` → สำเร็จ/ผิดพลาดคืน `render_template("index.html", ...)` status 200

- [ ] **Step 1: เขียน failing tests**

```python
class TestCalculateRoute(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        self.valid = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
                      "re": "1", "beta": "100", "vbe": "0.70", "unit": "kohm"}

    def test_valid_input_shows_computed_values(self):
        res = self.client.post("/calculate", data=self.valid)
        body = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 200)
        for expected in ("1.942", "1.242", "9.294", "8.052", "1.230"):
            self.assertIn(expected, body)

    def test_zero_resistor_shows_validation_error(self):
        data = dict(self.valid, r1="0")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn("มากกว่า 0", res.get_data(as_text=True))

    def test_non_numeric_input_shows_error(self):
        data = dict(self.valid, vcc="abc")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn("เป็นตัวเลข", res.get_data(as_text=True))

    def test_result_changes_with_input(self):
        res = self.client.post("/calculate", data=dict(self.valid, vcc="24"))
        self.assertIn("3.778", res.get_data(as_text=True))

    def test_kohm_and_ohm_differ(self):
        kohm = self.client.post("/calculate", data=self.valid).get_data(as_text=True)
        ohm = self.client.post("/calculate", data=dict(self.valid, r1="100", unit="ohm")).get_data(as_text=True)
        self.assertNotEqual(kohm, ohm)
        self.assertIn("เป็นตัวเลข", self.client.post("/calculate", data=dict(self.valid, beta="")).get_data(as_text=True))
```

- [ ] **Step 2: รันให้ fail**

Run: `py -3 -m unittest discover -s tests -p "test_web.py" -v`
Expected: FAIL — 404 ที่ `POST /calculate`

- [ ] **Step 3: implement route + helpers**

อ่าน `request.form`; แปลง `VCC`, `β`, `VBE` ตรง ๆ และแปลงตัวต้านทานผ่าน `_to_ohms`
ครอบ `ValueError` (parse) และ `ValidationError` → render ฟอร์มเดิมพร้อม `error` และคงค่าที่กรอก
สำเร็จ → `_format_result` แล้ว render; template แสดงผลขั้นต่ำเป็นรายการค่า + หน่วย

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `py -3 -m unittest discover -s tests -p "test_web.py" -v`
Expected: `OK` 6 tests

---

### Task 6: หน้าผลลัพธ์แบบ B + CSS

**Files:**
- Modify: `templates/index.html`, `app.py` (ถ้าต้องส่ง `region`/`warnings`)
- Create: `static/style.css`

**Interfaces:**
- Consumes: `_format_result` จาก Task 5, `DcBiasResult.region`/`warnings`
- Produces: HTML ที่มี `<details>` สรุป “วิธีคำนวณ”, badge region, การ์ด warning, ลิงก์ `static/style.css`

- [ ] **Step 1: เขียน failing tests**

```python
class TestResultsPresentation(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        self.valid = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
                      "re": "1", "beta": "100", "vbe": "0.70", "unit": "kohm"}

    def test_shows_intermediate_values_in_details(self):
        body = self.client.post("/calculate", data=self.valid).get_data(as_text=True)
        for expected in ("วิธีคำนวณ", "VTH", "RTH", "2.164", "18.03", "12.30"):
            self.assertIn(expected, body)
        self.assertIn("<details", body)

    def test_shows_active_badge_and_units(self):
        body = self.client.post("/calculate", data=self.valid).get_data(as_text=True)
        self.assertIn("Active", body)
        for unit in ("V", "mA", "µA", "kΩ"):
            self.assertIn(unit, body)

    def test_cutoff_warning_is_visible(self):
        data = dict(self.valid, r2="1")
        body = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("Cutoff", body)

    def test_stylesheet_linked(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("static/style.css", body)
```

- [ ] **Step 2: รันให้ fail**

Run: `py -3 -m unittest discover -s tests -p "test_web.py" -v`
Expected: FAIL — ไม่พบ `วิธีคำนวณ` / `<details`

- [ ] **Step 3: ปรับ template + เขียน CSS**

- ผลลัพธ์หลัก: `VB`, `VE`, `VC`, `VCE` (V), `IC`, `IE` (mA), `IB` (µA)
- `<details><summary>วิธีคำนวณ</summary>` แสดง `VTH`, `RTH`, `IB`, `IE` พร้อมหน่วย
- badge ข้อความ region (`Active`, `Cutoff`, `Saturation`, `Near-saturation`)
- warning ทุกข้อเป็น `<p class="warning">`
- `static/style.css`: responsive (≥ 720px เป็นสองคอลัมน์), ไม่ใช้ฟอนต์/ไลบรารีภายนอก

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `py -3 -m unittest discover -s tests -p "test_web.py" -v`
Expected: `OK` 10 tests

---

### Task 7: README, AGENTS, docs

**Files:**
- Create: `README.md`, `AGENTS.md`, `docs/design-note.md`, `docs/validation.md`, `docs/reflection.md`

**Interfaces:**
- Consumes: ชื่อไฟล์/คำสั่งจริงจาก Task 1–6

- [ ] **Step 1: เขียน `README.md`**

ต้องมี: ภาพรวม, โครงไฟล์, วิธีติดตั้ง (`py -3 -m venv .venv`, activate ทั้ง PowerShell และ bash, `py -3 -m pip install -r requirements.txt`), วิธีรัน (`py -3 -m flask --app app run --debug`), วิธี test (`py -3 -m unittest discover -s tests -v`), สมมติฐาน Forward-Active, ตาราง validation, ขอบเขต/ไม่ทำ, หมายเหตุว่า `python` บนเครื่องนี้อาจเป็น Store stub ให้ใช้ `py -3`

- [ ] **Step 2: เขียน `AGENTS.md`**

กติกา: UI ไทย/หน่วยอังกฤษ, SI ภายใน core, ห้ามสมการใน template, `unittest`, ห้าม commit `.venv`/`.env`, ทุกค่าที่แสดงต้องมาจาก backend

- [ ] **Step 3: เขียน `docs/design-note.md`**

สรุป 1 หน้า: ทางเลือก A/B/C, เหตุผลที่เลือก B, region thresholds, link ไป spec

- [ ] **Step 4: เขียน `docs/validation.md`**

ตารางค่าอ้างอิง §7.8 ของ spec เทียบค่าจากโปรแกรม + ช่องสำหรับแปะ test log จริง (เติมใน Task 8)

- [ ] **Step 5: เขียน `docs/reflection.md`**

คำถาม 4 ข้อจากใบงาน + ช่องว่างให้เขียนคำตอบ (เหตุใด `file://` ไม่เท่า Flask, ฟอร์มส่งค่าไป Python อย่างไร, แก้สมการต้องแก้ HTML ไหม, ทำไมต้องมี warning)

---

### Task 8: Verification + smoke test

**Files:**
- Modify: `docs/validation.md` (เติมผลจริง)

- [ ] **Step 1: สร้าง venv ใหม่และติดตั้ง**

Run: `py -3 -m venv .venv`
Run: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
Expected: `Successfully installed Flask-3.1.3 ...`

- [ ] **Step 2: รัน test ทั้งหมด**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `OK` 21 tests, `Ran 21 tests`

- [ ] **Step 3: smoke test ผ่าน HTTP จริง**

Run (background): `.\.venv\Scripts\python.exe -m flask --app app run --port 5000`
Run: `curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:5000/` → `200`
Run: `curl.exe -s -X POST -d "vcc=12&r1=100&r2=22&rc=2.2&re=1&beta=100&vbe=0.70&unit=kohm" http://127.0.0.1:5000/calculate`
Expected: มี `1.942`, `8.052`, `Active` ใน HTML
Run: `curl.exe -s -X POST -d "vcc=abc" http://127.0.0.1:5000/calculate` → มี `เป็นตัวเลข`
หยุด server

- [ ] **Step 4: ตรวจความสะอาดของ repo**

Run: `git status --short`
Expected: เห็นเฉพาะไฟล์โปรเจกต์ ไม่มี `.venv/`, `__pycache__/`, `.env`

- [ ] **Step 5: เติมผลลง `docs/validation.md`**

แปะ output ของ Step 2 และค่าที่ได้จาก Step 3 (จำกัดความยาว)

- [ ] **Step 6: หยุด — ส่งให้เจ้าของงานตรวจและ commit ผ่าน GitHub Desktop**

ยังไม่ commit เอง (execution choice C) — สรุปไฟล์ที่เปลี่ยนและข้อความ commit ที่แนะนำ:
`feat: implement BJT voltage-divider DC bias web app with tests`
