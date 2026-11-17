# Lab 03 — Fixed Bias + Emitter Bias Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่มโหมด Fixed Bias และ Emitter Bias ให้แอป Flask เดิม โดย Voltage Divider ยังได้ผลเท่าเดิมทุกหลัก และตรวจ A1–A5 ผ่าน browser ได้

**Architecture:** สมการใหม่อยู่ใน `dc_bias.py` เป็นฟังก์ชันบริสุทธิ์คู่กับ dataclass ของตัวเอง; `app.py` เลือกฟังก์ชันด้วย `if/elif` ตาม `mode` ที่ส่งมาจากฟอร์ม แล้วส่งค่าที่จัดรูปแล้วให้ Jinja; template เลือกช่อง/รูปวงจร/ป้ายโหมดตาม `mode` โดยไม่มี JavaScript

**Tech Stack:** Python 3.10+, Flask, Jinja2, unittest (stdlib), inline SVG, CSS ล้วน

**Spec:** `docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md`

## Global Constraints

- UI ภาษาไทย หน่วยอังกฤษ (`V`, `mA`, `µA`, `Ω`, `kΩ`); ห้ามใช้ฟอนต์/ไลบรารีภายนอก
- `dc_bias.py` รับ/คืน SI units (V, Ω, A) เท่านั้น ห้าม import Flask
- template ห้ามมีสมการฟิสิกส์หรือเลขคำตอบ; ห้ามมี JavaScript คำนวณ
- ใช้ `unittest` เท่านั้น; รันด้วย `.venv\Scripts\python.exe -m unittest discover -s tests -v`
- Commit message ภาษาอังกฤษ (`feat:` / `fix:` / `docs:` / `test:`)
- `calculate_dc_bias`, `DcBiasInput`, `DcBiasResult`, `classify_region` ของ Divider ต้องไม่ถูกแก้
- ค่าอ้างอิง A1: `IC = 1.229858 mA`, `VCE = 8.052155 V` (ต้องแสดง `1.230` / `8.052` เหมือน Lab 02)

## Review Focus

1. **Divider regression** — อินพุตเดิมต้องได้ `1.230` และ `8.052` (Task 3 มี regression test)
2. **เลขค้างหลัง error** — response ที่ error ต้องเป็น `—` ทั้งตาราง ไม่มีเลขรอบก่อน (Task 3)
3. **โหมดกับข้อมูลไม่ตรงกัน** — `mode=fixed` แต่ไม่มี `rb` ต้องได้ `กรุณากรอก RB เป็นตัวเลข` ไม่ใช่ผล Divider (Task 3)
4. **`RB = 0`** — Flask ต้องปฏิเสธด้วยข้อความที่เอ่ยถึง `RB` และหน้าไม่ล้ม (Task 3)
5. **โหมดใหม่ต้องไม่หลุดช่องของ Divider** — GET `/?mode=fixed` ต้องไม่มี `name="r1"`/`name="r2"`/`name="re"` และ SVG ต้องไม่มี label `R1` (Task 3, Task 4)

---

### Task 1: Fixed Bias ใน core

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Produces: `FixedBiasInput(vcc, rb, rc, beta, vbe)`, `BiasResult(ib, ic, ie, vb, ve, vc, vce, region, warnings)`, `calculate_fixed_bias(inp: FixedBiasInput) -> BiasResult`, `classify_operating_point(ib: float, vce: float) -> tuple[str, tuple[str, ...]]`
- Consumes: `ValidationError`, `VCE_SAT`, `VCE_NEAR_SAT`

- [ ] **Step 1: เขียน failing tests** — เพิ่มใน `tests/test_dc_bias.py`

```python
from dc_bias import FixedBiasInput, calculate_fixed_bias, classify_operating_point


class TestFixedBias(unittest.TestCase):
    def test_reference_case(self):
        res = calculate_fixed_bias(FixedBiasInput(12.0, 1e6, 2.2e3, 100.0, 0.70))
        self.assertAlmostEqual(res.ib, 11.3e-6, places=12)
        self.assertAlmostEqual(res.ic, 1.13e-3, places=12)
        self.assertAlmostEqual(res.ie, 1.1413e-3, places=12)
        self.assertAlmostEqual(res.vb, 0.70, places=9)
        self.assertEqual(res.ve, 0.0)
        self.assertAlmostEqual(res.vc, 9.514, places=9)
        self.assertAlmostEqual(res.vce, 9.514, places=9)
        self.assertEqual(res.region, "active")
        self.assertEqual(res.warnings, ())

    def test_zero_rb_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate_fixed_bias(FixedBiasInput(12.0, 0.0, 2.2e3, 100.0, 0.70))
        self.assertIn("RB ต้องมากกว่า 0", str(ctx.exception))

    def test_zero_rc_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate_fixed_bias(FixedBiasInput(12.0, 1e6, 0.0, 100.0, 0.70))
        self.assertIn("RC ต้องมากกว่า 0", str(ctx.exception))


class TestClassifyOperatingPoint(unittest.TestCase):
    def test_cutoff_when_ib_not_positive(self):
        self.assertEqual(classify_operating_point(0.0, 9.0)[0], "cutoff")

    def test_saturation_boundaries(self):
        self.assertEqual(classify_operating_point(1e-5, 0.199)[0], "saturation")
        self.assertEqual(classify_operating_point(1e-5, 0.2)[0], "near-saturation")
        self.assertEqual(classify_operating_point(1e-5, 0.5)[0], "active")
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p test_dc_bias.py -v`
Expected: FAIL — `ImportError: cannot import name 'FixedBiasInput'`

- [ ] **Step 3: implement ใน `dc_bias.py`**

- `FixedBiasInput` และ `BiasResult` เป็น `@dataclass(frozen=True)` ตาม Interfaces
- `classify_operating_point`: `ib <= 0` → cutoff (warning `Cutoff: IB ≤ 0 — แบบจำลอง Forward-Active ใช้ไม่ได้`) แล้วจึงเช็ก `vce < VCE_SAT` / `vce < VCE_NEAR_SAT` / active — ใช้ข้อความ Saturation/Near Saturation ชุดเดียวกับ `classify_region`
- `calculate_fixed_bias`: ตรวจ `vcc > 0`, `rb > 0`, `rc > 0`, `beta > 0`, `0 < vbe < vcc` (ข้อความ: `VCC ต้องมากกว่า 0`, `RB ต้องมากกว่า 0`, `RC ต้องมากกว่า 0`, `β ต้องมากกว่า 0`, `VBE ต้องมากกว่า 0 และน้อยกว่า VCC`)
- สูตร: `IB = (VCC − VBE) / RB`, `IC = β·IB`, `IE = (β+1)·IB`, `VE = 0`, `VB = VBE`, `VC = VCC − IC·RC`, `VCE = VC`
- ไม่แตะ `calculate_dc_bias` หรือ `classify_region`

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: OK (41 เดิม + 5 ใหม่)

- [ ] **Step 5: Commit**

```bash
git add dc_bias.py tests/test_dc_bias.py
git commit -m "feat: add fixed bias calculation to core"
```

---

### Task 2: Emitter Bias ใน core

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: `BiasResult`, `classify_operating_point` จาก Task 1
- Produces: `EmitterBiasInput(vcc, rb, rc, re, beta, vbe)`, `calculate_emitter_bias(inp: EmitterBiasInput) -> BiasResult`

- [ ] **Step 1: เขียน failing tests**

```python
class TestEmitterBias(unittest.TestCase):
    def test_reference_case(self):
        res = calculate_emitter_bias(EmitterBiasInput(12.0, 1e6, 2.2e3, 1e3, 100.0, 0.70))
        self.assertAlmostEqual(res.ib, 1.026339691e-5, places=12)
        self.assertAlmostEqual(res.ic, 1.026339691e-3, places=12)
        self.assertAlmostEqual(res.ie, 1.036603088e-3, places=12)
        self.assertAlmostEqual(res.ve, 1.036603088, places=8)
        self.assertAlmostEqual(res.vb, 1.736603088, places=8)
        self.assertAlmostEqual(res.vc, 9.742052679, places=8)
        self.assertAlmostEqual(res.vce, 8.705449591, places=8)
        self.assertEqual(res.region, "active")

    def test_larger_re_lowers_ic(self):
        one_k = calculate_emitter_bias(EmitterBiasInput(12.0, 1e6, 2.2e3, 1e3, 100.0, 0.70))
        two_k = calculate_emitter_bias(EmitterBiasInput(12.0, 1e6, 2.2e3, 2e3, 100.0, 0.70))
        self.assertLess(two_k.ic, one_k.ic)
        self.assertAlmostEqual(two_k.ic, 0.9400998336e-3, places=12)
        self.assertAlmostEqual(two_k.vce, 8.032778702, places=8)

    def test_zero_re_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            calculate_emitter_bias(EmitterBiasInput(12.0, 1e6, 2.2e3, 0.0, 100.0, 0.70))
        self.assertIn("RE ต้องมากกว่า 0", str(ctx.exception))
```

- [ ] **Step 2: รันให้ fail** (ImportError `EmitterBiasInput`)

- [ ] **Step 3: implement `calculate_emitter_bias` + `EmitterBiasInput`**

- validation: `VCC`, `RB`, `RC`, `RE`, `β`, `VBE` (ข้อความเดียวกับ Task 1 + `RE ต้องมากกว่า 0`)
- `IB = (VCC − VBE) / [RB + (β + 1)·RE]`; `IC = β·IB`; `IE = (β+1)·IB`
- `VE = IE·RE`; `VB = VE + VBE`; `VC = VCC − IC·RC`; `VCE = VC − VE`
- region จาก `classify_operating_point(ib, vce)`

- [ ] **Step 4: รัน test ให้ผ่าน** — Expected: OK

- [ ] **Step 5: Commit**

```bash
git add dc_bias.py tests/test_dc_bias.py
git commit -m "feat: add emitter bias calculation to core"
```

---

### Task 3: เลือกโหมดใน Flask + ฟอร์ม/ผล/ป้ายโหมด

**Files:**
- Modify: `app.py`, `templates/index.html`, `tests/test_web.py`

**Interfaces:**
- Consumes: `FixedBiasInput`, `EmitterBiasInput`, `calculate_fixed_bias`, `calculate_emitter_bias` จาก Task 1–2
- Produces (ให้ Task 4): template variable `mode`, `mode_label`, `tabs`; class `.mode-tab`, `.mode-tab.is-active`, `.mode-badge`, `.mode-tabs`

- [ ] **Step 1: อัปเดต payload ของ test เดิม + เขียน failing tests**

เติม `"mode": "divider"` ใน `self.valid` ทั้ง 3 class (`TestCalculateRoute`, `TestResultsPresentation`, `TestSingleScreenLayout`) แล้วเพิ่ม:

```python
class TestModeSelection(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        self.divider = {"mode": "divider", "vcc": "12", "r1": "100", "r2": "22",
                        "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.70", "unit": "kohm"}
        self.fixed = {"mode": "fixed", "vcc": "12", "rb": "1000",
                      "rc": "2.2", "beta": "100", "vbe": "0.70", "unit": "kohm"}
        self.emitter = dict(self.fixed, mode="emitter", re="1")

    def test_tabs_link_each_mode(self):
        body = self.client.get("/").get_data(as_text=True)
        for mode in ("divider", "fixed", "emitter"):
            self.assertIn(f'href="/?mode={mode}"', body)

    def test_fixed_form_hides_divider_fields(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertIn('name="rb"', body)
        for hidden in ('name="r1"', 'name="r2"', 'name="re"'):
            self.assertNotIn(hidden, body)

    def test_emitter_form_shows_rb_and_re(self):
        body = self.client.get("/?mode=emitter").get_data(as_text=True)
        for field in ('name="rb"', 'name="rc"', 'name="re"'):
            self.assertIn(field, body)
        self.assertNotIn('name="r1"', body)

    def test_fixed_result_has_mode_badge(self):
        body = self.client.post("/calculate", data=self.fixed).get_data(as_text=True)
        self.assertIn('class="mode-badge"', body)
        self.assertIn("Fixed Bias", body)
        self.assertIn("1.130", body)
        self.assertIn("9.514", body)

    def test_emitter_result_values(self):
        body = self.client.post("/calculate", data=self.emitter).get_data(as_text=True)
        self.assertIn("1.026", body)
        self.assertIn("8.705", body)

    def test_unknown_mode_is_rejected(self):
        body = self.client.post("/calculate", data=dict(self.divider, mode="inverter")).get_data(as_text=True)
        self.assertIn("โหมดวงจรไม่ถูกต้อง", body)
        self.assertIn("status-idle", body)

    def test_missing_mode_is_rejected(self):
        data = {k: v for k, v in self.divider.items() if k != "mode"}
        body = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("โหมดวงจรไม่ถูกต้อง", body)

    def test_fixed_zero_rb_names_rb_and_shows_no_numbers(self):
        body = self.client.post("/calculate", data=dict(self.fixed, rb="0")).get_data(as_text=True)
        self.assertIn("RB ต้องมากกว่า 0", body)
        self.assertIn("Fixed Bias", body)
        self.assertNotIn("1.130", body)
        self.assertNotIn("9.514", body)

    def test_wrong_mode_payload_asks_for_rb(self):
        data = {k: v for k, v in self.divider.items() if k != "r1"}
        data["mode"] = "fixed"
        body = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn("กรุณากรอก RB เป็นตัวเลข", body)

    def test_divider_values_stay_identical(self):
        body = self.client.post("/calculate", data=self.divider).get_data(as_text=True)
        self.assertIn("1.230", body)
        self.assertIn("8.052", body)
```

- [ ] **Step 2: รันให้ fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p test_web.py -v`
Expected: FAIL — ไม่มี `href="/?mode=fixed"` และ `name="rb"`

- [ ] **Step 3: implement `app.py`**

- `MODE_LABELS = {"divider": "Voltage Divider Bias", "fixed": "Fixed Bias", "emitter": "Emitter Bias"}`
- `MODE_TABS = {"divider": "Divider", "fixed": "Fixed", "emitter": "Emitter"}`
- `DEFAULT_FORMS` ต่อโหมด (divider = ค่าเดิม; fixed `rb="1000"`; emitter `rb="1000", re="1"`); คง `DEFAULT_FORM = DEFAULT_FORMS["divider"]`
- `_mode_from(raw)` → key ที่อยู่ใน `MODE_LABELS` หรือ `None`
- `_render(mode, form, *, error=None, result=None, values=None, status=None, workings=None)` เรียก `render_template` ด้วย `mode`, `mode_label`, `tabs`, `diagram=_diagram_labels(form, mode)`
- `GET /`: `mode = request.args.get("mode", "divider")`; ถ้าไม่รู้จัก → error `โหมดวงจรไม่ถูกต้อง` + ฟอร์ม divider
- `POST /calculate`: โหมดไม่รู้จัก/หาย → error `โหมดวงจรไม่ถูกต้อง`; `if/elif/else` สร้าง input ตามโหมด แปลงหน่วยด้วย `_to_ohms(..., unit, "RB"|"RC"|"RE"|...)`
- error ที่มาจาก parse/core → `f"{MODE_LABELS[mode]} — {exc}"`, `values=None`, `status=None`, `workings=None`
- `_format_result` คืนเฉพาะ `vb, ve, vc, vce, ib, ic, ie, region` (ตัด `vth/rth`)
- `_workings(mode, result)` → `list[dict[str, str]]`: divider มี `VTH`/`RTH` แล้วต่อด้วย `IB`/`IE`; fixed/emitter มี `IB`/`IE` เท่านั้น (หน่วย `V`, `kΩ`, `µA`, `mA`)
- `_diagram_labels(form, mode="divider")` คืน key ตามโหมด: divider `r1/r2/rc/re`, fixed `rb/rc`, emitter `rb/rc/re` + `vcc`/`beta` ทุกโหมด

- [ ] **Step 4: implement `templates/index.html`**

- header: `ENG29 2121 · Lab 03`, subtitle `วงจรขยาย Common-Emitter — {{ mode_label }}`
- ใน panel Input ก่อนฟอร์ม: `<nav class="mode-tabs">` ลูป `tabs.items()` → `<a class="mode-tab{% if key == mode %} is-active{% endif %}" href="{{ url_for('index', mode=key) }}">{{ label }}</a>`
- ใน `<form>`: `<input type="hidden" name="mode" value="{{ mode }}">` เป็นช่องแรก
- ช่อง: `vcc` เสมอ → `r1`,`r2` เฉพาะ divider → `rb` เฉพาะ fixed/emitter → `rc` เสมอ → `re` เฉพาะ divider/emitter → `unit` → `beta` → `vbe`
- panel Results: หลัง `<h2>` เพิ่ม `<p class="mode-badge">{{ mode_label }}</p>`
- `<details>` เปลี่ยนเป็นลูป `{% for row in workings %}<div><dt>{{ row.label }}</dt><dd>{{ row.value }}</dd></div>{% endfor %}`
- ห้ามมีสูตร/เลขคำตอบใน template

- [ ] **Step 5: รัน test ให้ผ่าน**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: OK (49 เดิม + 10 ใหม่)

- [ ] **Step 6: Commit**

```bash
git add app.py templates/index.html tests/test_web.py
git commit -m "feat: dispatch bias mode and render per-mode form and results"
```

---

### Task 4: SVG ต่อโหมด + CSS

**Files:**
- Modify: `templates/index.html`, `static/style.css`, `tests/test_web.py`

**Interfaces:**
- Consumes: `mode` จาก Task 3; `diagram` keys `rb`, `re` จาก `_diagram_labels`
- Produces: SVG ที่มีจำนวน `res-zigzag` ต่างกันต่อโหมด (divider 4, fixed 2, emitter 3)

- [ ] **Step 1: เขียน failing tests**

```python
class TestModeSchematics(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_fixed_schematic_has_rb_and_rc_only(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertEqual(body.count("res-zigzag"), 2)
        self.assertIn(">RB<", body)
        self.assertNotIn(">R1<", body)
        self.assertNotIn(">RE<", body)

    def test_emitter_schematic_has_rb_rc_re(self):
        body = self.client.get("/?mode=emitter").get_data(as_text=True)
        self.assertEqual(body.count("res-zigzag"), 3)
        self.assertIn(">RB<", body)
        self.assertIn(">RE<", body)
        self.assertNotIn(">R1<", body)

    def test_fixed_shows_rb_value_in_schematic(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertIn("1000 kΩ", body)
```

- [ ] **Step 2: รันให้ fail** — fixed ยังได้ 4 ตัวและมี `R1`

- [ ] **Step 3: implement SVG 3 แบบใน template**

- ใช้ `{% if mode == 'divider' %}` (markup เดิมทั้งหมด) `{% elif mode == 'fixed' %}` `{% else %}` (emitter)
- fixed: ราง VCC เดิม; `RB` เป็นซิกแซกแนวตั้งที่ x=100 จากรางลงมา แล้วลากไป base; `RC` ตำแหน่งเดิม; emitter ลากตรงลงกราวด์ (ไม่มี RE); label ซ้าย `RB`
- emitter: เหมือน fixed แต่ emitter ผ่าน `RE` (ซิกแซก 250–300) ลงกราวด์ และมี label `RE`
- คง `class="res-zigzag"`, `class="q1-circle"`, และสไตล์ซิกแซกเดิม
- label ทุกตัวมาจาก `diagram.*` (ห้าม hardcode ค่า)

- [ ] **Step 4: เพิ่ม CSS**

- `.mode-tabs { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px }`
- `.mode-tab` ปุ่มลิงก์ขอบบาง, `.mode-tab.is-active` พื้น navy ตัวอักษรขาว
- `.mode-badge` ข้อความเล็ก สี muted ใต้หัวข้อผล
- ห้ามใช้ฟอนต์/ไลบรารีภายนอก

- [ ] **Step 5: รัน test + ตรวจภาพ**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v` → OK
Run (แยก terminal): `.venv\Scripts\python.exe -m flask --app app run --port 5000`
Screenshot 1366×768 ทุกโหมดด้วย headless Chrome แล้วเปิดดู — ต้องเห็น 3 panel ครบ ไม่มี scroll แนวนอน และแท็บไม่ล้น panel

- [ ] **Step 6: Commit**

```bash
git add templates/index.html static/style.css tests/test_web.py
git commit -m "feat: draw per-mode circuit schematics and mode tabs"
```

---

### Task 5: ตรวจ A1–A5 และเอกสาร

**Files:**
- Modify: `docs/validation.md`, `README.md`
- Create: `docs/evidence/lab03-a1.png` … `lab03-a5.png`

**Interfaces:**
- Consumes: แอปที่รันได้จาก Task 4

- [ ] **Step 1: เตรียม probe ต่อกรณี (นอก repo, ที่ `%TEMP%\opencode`)**

HTML หนึ่งไฟล์ต่อกรณี: `<form method="post" action="http://127.0.0.1:5000/calculate">` พร้อม hidden/input ครบทุกช่องของโหมดนั้น + `<script>document.forms[0].submit()</script>` (ไฟล์ทดสอบ ไม่ใช่แอป)

- [ ] **Step 2: รันเซิร์ฟเวอร์และเก็บภาพ**

- A1 Divider: `r1=100, r2=22, re=1, rc=2.2, vcc=12, beta=100, vbe=0.70, unit=kohm`
- A2 Fixed: `rb=1000`
- A3 Emitter: `rb=1000, re=1`
- A4 Emitter: `rb=1000, re=2`
- A5 Fixed: `rb=0`
- บันทึกภาพด้วย `chrome.exe --headless=new --disable-gpu --window-size=1366,768 --virtual-time-budget=3000 --screenshot=<path> <probe-file>`

- [ ] **Step 3: ตัดสินผลเทียบค่ามือ**

| กรณี | IC ที่ต้องเห็น | VCE ที่ต้องเห็น |
|---|---|---|
| A1 | 1.230 mA | 8.052 V |
| A2 | 1.130 mA | 9.514 V |
| A3 | 1.026 mA | 8.705 V |
| A4 | 0.940 mA | 8.033 V |
| A5 | error `RB ต้องมากกว่า 0`, ไม่มีเลขผล, หน้า 200 | — |

เกณฑ์: `|ΔIC| ≤ 0.01 mA`, `|ΔVCE| ≤ 0.02 V`; A1 ต้องเท่า `docs/validation.md` เดิม
บันทึก A4 prediction ก่อนรัน: `IC ลดลงเพราะ RE มากขึ้น`

- [ ] **Step 4: เขียน `docs/validation.md`**

- ตาราง A1–A5: อินพุต / ค่ามือ / เห็นจริง / วิธีตรวจ / PASS–FAIL–NOT RUN
- วิธีตรวจระบุ `Manual (headless Chrome + Flask)` และระบุ `Playwright MCP = NOT RUN — ไม่มี Node.js/MCP ในเครื่อง`
- ระบุ commit SHA ที่ใช้ตรวจ, วันที่, และ path ของภาพหลักฐาน

- [ ] **Step 5: อัปเดต `README.md`**

- โหมดที่รองรับ + สมการย่อของแต่ละโหมด
- วิธีกรอก `1 MΩ = 1000 kΩ`
- วิธีรัน test และวิธีตรวจ A1–A5 ซ้ำ

- [ ] **Step 6: Commit**

```bash
git add docs/validation.md README.md docs/evidence
git commit -m "docs: record lab 03 browser acceptance for A1-A5"
```

---

### Task 6: Commit เอกสาร design/plan

**Files:**
- Add: `docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md`
- Add: `docs/superpowers/plans/2026-11-17-lab03-multi-bias.md`

- [ ] **Step 1: ตรวจ `git status` ว่าไม่มีไฟล์ไม่พึงประสงค์** (`.venv/`, `__pycache__/`, `*.pyc`)

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md docs/superpowers/plans/2026-11-17-lab03-multi-bias.md
git commit -m "docs: add lab 03 design and implementation plan"
```

- [ ] **Step 3: รายงานสถานะ push**

`git status -sb` ต้องบอก ahead กี่ commit; แจ้งเจ้าของงานให้กด Push origin ใน GitHub Desktop (CLI ไม่มี credential)
