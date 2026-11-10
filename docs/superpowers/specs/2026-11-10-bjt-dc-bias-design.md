# BJT DC Bias Web App — Design Document (Lab 02)

- วันที่: 2026-11-10
- รายวิชา: ENG29 2121 Computer Programming for Electrical Engineers (2/2569)
- เจ้าของงาน: Gaga959
- สถานะ: รออนุมัติ (ยังไม่เริ่มเขียนโค้ด)

## 1. Intent — ทำไมต้องมีชิ้นงานนี้

ส่งงาน Lab 02 ให้ครบเกณฑ์ A1–A7 และใช้เป็นจุดเริ่มต้นของ Virtual Transistor Laboratory ปลายภาค
แก่นของงานคือการพิสูจน์ว่าผู้เรียนเข้าใจว่า **เว็บที่มี Backend** ต่างจาก HTML ไฟล์เดียวอย่างไร:
เบราว์เซอร์ส่ง HTTP Request → Flask รับ → Python คำนวณ DC Operating Point → Jinja render HTML กลับ

## 2. Goals

1. เปิดผ่าน `http://127.0.0.1:5000/` ได้จริงและเห็นฟอร์ม (A1)
2. `POST /calculate` แล้ว Python คำนวณจากค่าที่ผู้ใช้กรอก ไม่มีค่าคำตอบฝังใน HTML (A2)
3. ค่า `VB, VE, VC, VCE, IC` ตรงกับการคำนวณอิสระภายใต้ Forward-Active model (A3)
4. Validation: `R ≤ 0`, `β ≤ 0`, `VCC ≤ 0`, ค่าไม่ใช่ตัวเลข/ว่าง → ข้อความ error ภาษาไทยที่อ่านรู้เรื่อง หน้าเว็บไม่ล่ม (A4)
5. Region warning: Cutoff (`VTH ≤ VBE`) และ Saturation/ใกล้ Saturation (`VCE` ต่ำ) (A5)
6. Automated tests ≥ 3 ด้าน engineering + ≥ 1 ผ่าน Flask test client (A6)
7. Clone repo → ติดตั้ง → รัน → test ตาม README ได้ (A7)
8. แสดงผลแบบ **ตัวเลือก B**: ค่าผลลัพธ์สุดท้าย + ส่วน “วิธีคำนวณ” แบบพับได้ ที่แสดง `VTH, RTH, IB, IE` ซึ่ง **คำนวณจาก Python จริง** ไม่ใช่ข้อความคงที่

## 3. Non-goals (ไม่ทำในคาบนี้)

- AC small-signal, Gain, Bode plot, Transient, Signal generator
- SPICE/ngspice, DC load line
- Bias แบบอื่น (Fixed, Emitter) — ทำสัปดาห์ถัดไป
- ฐานข้อมูล, ระบบ login, การ deploy ขึ้น cloud
- กราฟ/แผนภาพวงจรแบบ interactive

## 4. Anti-goals (ถ้าเกิดขึ้นถือว่าล้มเหลว)

- แสดงตัวเลขที่ hardcode ไว้ใน template หรือคำนวณด้วย JavaScript ฝั่ง client
- แสดงผลนอก Forward-Active โดยไม่มี warning หรืออ้างว่าแม่นยำ
- เปิดด้วย `file://` แล้วใช้งานได้ (แปลว่าไม่ได้ใช้ Backend จริง)
- Commit `.venv/`, `.env`, API key หรือไฟล์ cache
- Test ผ่านโดยไม่ได้รันจริง หรือเขียน test ที่ assert ค่าที่ copy มาจาก output ตัวเองโดยไม่มีการคำนวณอิสระ

## 5. Constraints จากใบงาน

| ข้อ | ข้อกำหนด |
|---|---|
| Stack | Python + Flask, หลายไฟล์ |
| อินพุต | `VCC [V]`, `R1, R2, RC, RE`, `β`, `VBE [V]` |
| เอาต์พุต | `VB, VE, VC, VCE [V]`, `IC [mA]` (แสดง `IB, IE` เพิ่มได้) |
| หน่วย | ต้องกำกับหน่วยทุกค่า และแปลง kΩ → Ω ให้สอดคล้องก่อนคำนวณ |
| โมเดล | Forward-Active approximation, β คงที่, VBE คงที่ |
| โครงไฟล์ | `app.py`, `dc_bias.py`, `templates/index.html`, `static/style.css`, `tests/`, `requirements.txt`, `README.md`, `AGENTS.md`, `docs/` |
| เวลา | 75 นาทีสำหรับ build + 25 นาที verification |

## 6. Approaches ที่พิจารณา

### 6.1 การแสดงผล (ผู้ใช้เลือกแล้ว)

| ทางเลือก | ลักษณะ | แลกกับ |
|---|---|---|
| A Minimal | ค่าสุดท้าย + region badge + warning | เร็ว แต่ตรวจย้อนกลับยาก |
| **B Standard (เลือก)** | ค่าสุดท้าย + `<details>` “วิธีคำนวณ” แสดง VTH, RTH, IB, IE จาก Python | งานเพิ่มเล็กน้อย ได้ประโยชน์ด้าน A3 และตอบคำถามท้ายใบงาน |
| C Full teaching | สมการแทนเลขทุกบรรทัด | เวลา/test เพิ่มมาก เสี่ยงไม่จบในคาบ |

### 6.2 วิธีการสร้าง (มีทางเดียวที่สมเหตุสมผล)

- **เลือก: Flask + Jinja server-rendered + `unittest` (stdlib)**
- ทางเลือกที่ตัดออก:
  - HTML + JS คำนวณฝั่ง client → ผิดเงื่อนไข “Python Backend คำนวณ” และ A2
  - SPA + `fetch` JSON API → ซ้ำซ้อนกับเวลาคาบ และทำให้การทดสอบ HTTP form ตรง ๆ ยากขึ้นโดยไม่จำเป็น
  - `pytest` → ต้องเพิ่ม dependency ทั้งที่ `unittest` เป็น stdlib และคำสั่งในใบงานใช้ `python -m unittest discover`
- ผลพลอยได้: template ไม่มีสมการฟิสิกส์, `dc_bias.py` ไม่รู้จัก HTTP/HTML

## 7. Design

### 7.1 โครงไฟล์

```
BJT DC Bias Web App/
├── app.py
├── dc_bias.py
├── templates/index.html
├── static/style.css
├── tests/test_dc_bias.py
├── tests/test_web.py
├── requirements.txt
├── README.md
├── AGENTS.md
├── .gitignore
└── docs/
    ├── preflight-checklist.md   (มีแล้ว)
    ├── design-note.md           (สรุป design นี้ + link)
    ├── validation.md            (ตารางคำนวณอ้างอิง + test log)
    ├── reflection.md            (แบบฟอร์มให้เจ้าของงานเขียน)
    └── superpowers/specs/2026-11-10-bjt-dc-bias-design.md  (ไฟล์นี้)
```

### 7.2 `dc_bias.py` — engineering core (SI units เท่านั้น)

```python
@dataclass(frozen=True)
class DcBiasInput: vcc, r1, r2, rc, re, beta, vbe   # V, Ω, Ω, Ω, Ω, -, V
@dataclass(frozen=True)
class DcBiasResult: vth, rth, ib, ic, ie, vb, ve, vc, vce, region, warnings
```

- `calculate_dc_bias(inp: DcBiasInput) -> DcBiasResult`
- `ValidationError(ValueError)` พร้อมข้อความภาษาไทย:
  - `VCC ต้องมากกว่า 0`
  - `R1, R2, RC, RE ต้องมากกว่า 0`
  - `β ต้องมากกว่า 0`
  - `VBE ต้องมากกว่า 0 และน้อยกว่า VCC`
- สมการ (ตามใบงาน):
  `VTH = VCC·R2/(R1+R2)`, `RTH = R1·R2/(R1+R2)`,
  `IB = (VTH−VBE)/(RTH+(β+1)·RE)`, `IC = β·IB`, `IE = (β+1)·IB`,
  `VE = IE·RE`, `VB = VE+VBE`, `VC = VCC−IC·RC`, `VCE = VC−VE`

### 7.3 Region logic (เป็น call ของผู้เขียน design)

| เงื่อนไข | Region | การรายงาน |
|---|---|---|
| `VTH ≤ VBE` (ได้ IB ≤ 0) | `cutoff` | clamp `IB=IC=IE=0`, `VE=0`, `VB=VTH`, `VC=VCC`, `VCE=VCC` + warning “แบบจำลอง Forward-Active ใช้ไม่ได้ (Cutoff)” |
| `VCE < 0.2 V` | `saturation` | รายงานค่าที่คำนวณได้ แต่ติด warning ว่า “ไม่น่าเชื่อถือ; VCE ควรใกล้ VCE(sat) ≈ 0.2 V” |
| `0.2 ≤ VCE < 0.5 V` | `near-saturation` | รายงานค่าปกติ + warning “ใกล้ Saturation ผลอาจคลาดเคลื่อน” |
| อื่น ๆ | `active` | รายงานปกติ ไม่มี warning |

- ค่าคงที่ `VCE_SAT = 0.2`, `VCE_NEAR_SAT = 0.5` ประกาศเป็น module constant เพื่อทดสอบได้
- Test ต้องครอบทั้ง 4 กรณี

### 7.4 `app.py` — HTTP layer

- `create_app() -> Flask` (factory เพื่อ test) และ `app = create_app()` สำหรับ `flask --app app run`
- `GET /` → render ฟอร์มพร้อมค่าเริ่มต้นจากใบงาน (12, 100, 22, 2.2, 1, 100, 0.7)
- `POST /calculate` → parse → แปลงหน่วย → `calculate_dc_bias` → render หน้าเดิมพร้อมผล
- **อินพุตตัวต้านทาน:** ฟิลด์ตัวเลข 4 ช่อง + **ตัวเลือกหน่วยร่วม 1 ตัว (`Ω` / `kΩ`, ค่าเริ่มต้น `kΩ`)** แปลงเป็น Ω ใน `app.py` ก่อนเรียก `dc_bias.py` (core ไม่รับ kΩ)
- ค่าไม่ใช่ตัวเลข/ว่าง → แสดง error ใต้ฟิลด์, คงค่าที่กรอกไว้, HTTP **200** (ไม่ throw 500)
- `ValidationError` จาก core → แสดงเป็น error banner
- ไม่มี JavaScript ที่คำนวณผล

### 7.5 Template (ตัวเลือก B) — ร่างหน้าจอ

```
┌───────────────────────────────────────────────┐
│ BJT DC Bias Calculator — Voltage Divider      │
├───────────────────────────────────────────────┤
│ VCC [V]      [ 12    ]                        │
│ R1  [100] R2 [22] RC [2.2] RE [1]  หน่วย [kΩ] │
│ β   [100]   VBE [0.70 V]                      │
│                [ Calculate DC Bias ]          │
├───────────────────────────────────────────────┤
│ ● Active region            (badge)            │
│ VB 1.942 V   VE 1.242 V   VC 9.294 V          │
│ VCE 8.052 V  IC 1.230 mA  IB 12.30 µA  IE 1.242 mA │
│ ▸ วิธีคำนวณ (details)                         │
│    VTH = 2.164 V   RTH = 18.03 kΩ             │
│    IB = 12.30 µA   IE = 1.242 mA              │
│    (ค่าทั้งหมดมาจาก Python)                    │
└───────────────────────────────────────────────┘
```

- ทุกค่าที่แสดงมาจาก `DcBiasResult` ผ่าน Jinja (ห้ามมีเลขคำตอบใน HTML)
- Warning แสดงเป็นการ์ดสีส้ม/แดงตามระดับ
- ฟอร์มใช้ `method="post" action="/calculate"`
- ป้ายภาษาไทยเป็นหลัก หน่วยอังกฤษ (V, mA, µA, Ω, kΩ)

### 7.6 `static/style.css`

- Responsive 1 คอลัมน์บนมือถือ, 2 คอลัมน์บนจอใหญ่
- ไม่ใช้ framework, ไม่ใช้ฟอนต์ภายนอก (ออฟไลน์ได้)
- โทนสีน้ำเงินเข้ม/เทา, badge สีเขียว (active) / ส้ม (near-sat) / แดง (cutoff, saturation)

### 7.7 Tests

`tests/test_dc_bias.py` (≥ 3 เคส):
1. Reference case ตามใบงาน → ตรวจ `VTH, RTH, IB, IC, IE, VB, VE, VC, VCE` ด้วย `assertAlmostEqual` (places=3 ตามหน่วยที่แสดง)
2. Validation: `R1=0`, `β=0`, `VCC=0`, `VBE>VCC` → `ValidationError`
3. Cutoff: `R2` เล็กมากจน `VTH ≤ VBE` → region `cutoff`, กระแสเป็น 0, มี warning
4. Saturation: `RC` ใหญ่/`RE` เล็กจน `VCE < 0.2` → region `saturation` + warning
5. Near-saturation: ปรับค่าให้ `0.2 ≤ VCE < 0.5` → warning

`tests/test_web.py` (≥ 1 เคส):
1. `GET /` → 200 และมี `name="vcc"`, `name="beta"` ฯลฯ
2. `POST /calculate` ค่าอ้างอิง → 200 และ HTML มี `1.942` / `8.052` (ค่าที่คำนวณจริง)
3. `POST /calculate` `R1=0` → 200 + ข้อความ error
4. `POST /calculate` `vcc=abc` → 200 + ข้อความ error (ไม่ 500)
5. เปลี่ยน `VCC` แล้วผลเปลี่ยน (พิสูจน์ว่าไม่ได้ hardcode)

### 7.8 Reference values (ใช้ตรวจเทียบ ไม่ได้ copy จากโปรแกรม)

| ปริมาณ | ค่า |
|---|---|
| VTH | 2.163934 V |
| RTH | 18.032787 kΩ |
| IB | 12.298581 µA |
| IC | 1.229858 mA |
| IE | 1.242157 mA |
| VE | 1.242157 V |
| VB | 1.942157 V |
| VC | 9.294312 V |
| VCE | 8.052155 V |
| Region | active |

### 7.9 README / AGENTS / docs

- `README.md`: ภาพรวม, วิธีติดตั้ง (venv, pip, flask run), วิธี test, สมมติฐานโมเดล, ตาราง validation, โครงไฟล์, ขอบเขต
- `AGENTS.md`: กติกา — UI ไทย, หน่วย SI ภายใน core, ห้ามใส่สมการใน template, ใช้ `unittest`, ห้าม commit `.venv`
- `docs/validation.md`: ตารางเทียบค่ามือ vs โปรแกรม + test log
- `docs/reflection.md`: คำถามสะท้อนคิด (เหตุใด `file://` ไม่เท่า Flask, form ส่งค่าไป Python อย่างไร, แก้สมการต้องแก้ HTML ไหม, ทำไมต้องมี warning)

## 8. Acceptance mapping

| เกณฑ์ | กลไกใน design |
|---|---|
| A1 | `GET /` คืน 200 + ฟอร์ม |
| A2 | `POST /calculate` → `dc_bias.calculate_dc_bias` (ไม่มีเลขใน template) |
| A3 | ตาราง reference §7.8 + unit test ด้วย `assertAlmostEqual` |
| A4 | `ValidationError` + parse error ที่ `app.py`, HTTP 200 + ข้อความ |
| A5 | region logic §7.3 + warning text |
| A6 | test_dc_bias (5 เคส) + test_web (5 เคส) |
| A7 | README ขั้นตอน venv/pip/run/test |

## 9. สิ่งที่เหลือให้ผู้สร้างตัดสินใจ

- ถ้อยคำ/ลำดับป้ายกำกับภาษาไทยใน UI และการจัดวางละเอียด
- สี/ระยะห่าง/ฟอนต์ใน CSS
- จะแสดงสูตรเป็นข้อความใน `<details>` ด้วยหรือไม่ (ไม่บังคับ)
- โครงสร้าง helper ใน `app.py` (เช่น `_parse_float`) และชื่อ test
- รูปแบบตารางใน README

## 10. ความเสี่ยง

1. **Python 3.14 ใหม่มาก** — Flask 3.1 ใช้ได้ แต่ถ้าพบปัญหา ให้ระบุ `py -3` และ pin Flask ใน `requirements.txt`
2. **เวลาคาบจำกัด** — ถ้าเกิน 75 นาที ให้ตัด near-saturation test และรายละเอียด CSS ก่อน (ไม่ตัด validation/warning)
3. **ค่า kΩ ปนกับ Ω** — แก้ด้วยตัวเลือกหน่วยร่วม + unit test การแปลง
4. **Commit ผ่าน GitHub Desktop** — ต้อง Publish repository ครั้งแรกก่อน (ยังไม่มี remote)

## 11. การส่งงานและหลักฐาน (อ่านจากใบงานแล้ว ไม่ต้องถามเพิ่ม)

- ส่ง **Repository URL + Commit SHA** ผ่าน Moodle (ไม่ต้องมีรายงาน PDF แยก)
- แนบ **ภาพหน้าจอเว็บที่คำนวณสำเร็จ** และ **Test Log**
- Reference case ที่ใช้ตรวจคือค่าทดลองในใบงาน: `12 V, 100 kΩ, 22 kΩ, 2.2 kΩ, 1 kΩ, β=100, VBE=0.70 V` (นักศึกษาคำนวณอิสระเอง)
- ไฟล์ที่ต้องมีใน repo: ฝั่ง Server, Templates, CSS, Logic, Tests, README
- `docs/validation.md` ต้องเก็บ **ตารางค่ามือ vs ค่าโปรแกรม + test log จริง** ไม่ใช่แค่ตารางเปล่า
- รูปแบบอินพุต: ใบงานไม่ได้บังคับหน่วย เป็น Ω อย่างเดียว แต่กำหนดให้แปลง kΩ ↔ Ω ให้สอดคล้อง → design ใช้ตัวเลือกหน่วยร่วม (Ω/kΩ)

## 12. Commit / Publish workflow (ตกลงกับเจ้าของงาน)

- **เจ้าของงานเป็นผู้ commit ผ่าน GitHub Desktop** (ตามที่ตกลงไว้) — agent เตรียมไฟล์และข้อความ commit ให้
- ลำดับ: commit ไฟล์ basis (design + checklist) → Publish repository → ต่อด้วย commit ต่อ Task
- หลัง Publish แล้ว การตรวจ A7 ทำได้ด้วย `git clone` จริง; ก่อน Publish ใช้วิธีคัดลอกโฟลเดอร์ไป temp + สร้าง venv ใหม่แทน
- ทุก commit ต้องตรวจ Diff และต้องไม่มี `.venv/`, `.env`, `__pycache__/`
