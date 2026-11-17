# Design — Lab 03: เพิ่ม Fixed Bias และ Emitter Bias

วันที่: 2026-11-17 · ต่อยอดจาก `2026-11-10-bjt-dc-bias-ui-redesign-design.md`
อ้างอิงใบงาน: `ENG29_2121_Lab03_BJT_Bias_Web_App.html`

## ทำไม

Lab 02 ทำได้วงจรเดียว (Voltage Divider) Lab 03 ให้ผู้ใช้เลือกได้ 3 วงจร
โดยใช้ฟอร์มและหน้าผลลัพธ์ชุดเดิม และต้องพิสูจน์ผ่าน browser ว่า
Voltage Divider ยังได้ผลเดิม ขณะที่ Fixed/Emitter คำนวณถูกตามสมการในใบงาน

## เป้าหมาย

- G1 เลือก 3 โหมดได้: Voltage Divider, Fixed Bias (`RB`), Emitter Bias (`RB`, `RE`)
- G2 เลือก Voltage Divider ด้วยอินพุตเดิม → ตัวเลขทุกตัวเท่า Lab 02 เป๊ะ
- G3 ตรวจอินพุตเฉพาะช่องของโหมดนั้น; ช่องที่ไม่ใช้ไม่แสดง
- G4 โหมดที่เลือกต้องเห็นได้ทั้งในฟอร์ม ผลลัพธ์ และข้อความ error
- G5 error ต้องไม่ทิ้งตัวเลขของรอบก่อนไว้ให้ดูเหมือนผลรอบนี้
- G6 ทำงานออฟไลน์ ไม่มี JavaScript ไม่เพิ่ม dependency

## ไม่ทำ

- ไม่ทำ DC load line, AC/transient, bypass capacitor, SPICE
- ไม่ทำ live update ตอนพิมพ์, ไม่ทำ MΩ unit ใหม่ (กรอก `1000` kΩ แทน 1 MΩ)
- ไม่แตะสูตร Divider เดิม, ไม่แตะ region logic ของ Divider
- ไม่ติดตั้ง Node.js/Playwright MCP ในรอบนี้ (ใบงานมีวิธีสำรอง)
- ไม่ deploy ขึ้น host สาธารณะ

## Anti-goal (ถือว่าล้มเหลวถ้าเกิด)

- ตัวเลข Divider เปลี่ยนจาก Lab 02 (`IC = 1.229858 mA`, `VCE = 8.052155 V`)
- สมการหรือเลขคำตอบไปอยู่ใน `templates/index.html`
- โหมดไม่รู้จักแล้วเงียบ ๆ คำนวณเป็น Divider
- หลัง error ยังเห็นเลขผลของรอบก่อนในตาราง
- เลือกโหมดแล้วยังเห็น/ต้องกรอกช่องของโหมดอื่น
- `RB = 0` ผ่านการตรวจเพราะ HTML `required` อย่างเดียว

## แนวทางที่พิจารณา

### การเลือกโหมด

| แนวทาง | ผล | แลกกับ |
|---|---|---|
| **A. แท็บลิงก์ 3 อัน (เลือก)** — `/?mode=fixed` | เปลี่ยนโหมดแล้ว reload ฟอร์มทันที, ไม่มี JS, ปุ่ม Calculate ปุ่มเดียว | ต้องมี hidden `mode` ใน POST |
| B. Dropdown + ปุ่ม "โหลดฟอร์ม" | ตรงรูปใบงาน (dropdown) | ต้องกด 2 จังหวะ (โหลดฟอร์ม → กรอก → คำนวณ), ปุ่มสองปุ่มสับสนใน A5 |
| C. Radios + disable ช่องที่ไม่ใช้ | เห็นทุกช่อง | ไม่มี JS แล้วเปลี่ยน disable ไม่ได้จนกว่าจะ submit; ยังต้องมีปุ่มโหลดฟอร์มอยู่ดี |

### รูปร่างของ core

| แนวทาง | ผล | แลกกับ |
|---|---|---|
| **A. ฟังก์ชันแยก + dataclass แยก (เลือก)** | `calculate_fixed_bias`, `calculate_emitter_bias`; Divider เดิมไม่ถูกแตะ | มี field ซ้ำ 7 ตัวใน 3 dataclass |
| B. `DcBiasResult` เดียว + `vth/rth: float \| None` | formatter ตัวเดียว | เสี่ยงแตะ Divider และ type ของ field ที่เดิมบังคับมีค่า |
| C. ฟังก์ชันเดียวรับ `mode` | โค้ดน้อย | ใบงานสั่งแยกฟังก์ชัน และ validation ปนกัน |

## ดีไซน์

### 1. `dc_bias.py` (SI units เท่านั้น)

เพิ่ม โดยไม่แก้ `DcBiasInput`, `DcBiasResult`, `calculate_dc_bias`, `classify_region`:

```python
@dataclass(frozen=True)
class FixedBiasInput:   vcc, rb, rc, beta, vbe

@dataclass(frozen=True)
class EmitterBiasInput: vcc, rb, rc, re, beta, vbe

@dataclass(frozen=True)
class BiasResult:       ib, ic, ie, vb, ve, vc, vce, region, warnings
```

- `calculate_fixed_bias`:
  - `IB = (VCC − VBE) / RB`, `IC = β·IB`, `IE = (β+1)·IB`
  - `VE = 0`, `VB = VBE`, `VC = VCC − IC·RC`, `VCE = VC`
- `calculate_emitter_bias`:
  - `IB = (VCC − VBE) / [RB + (β+1)·RE]`, ที่เหลือเหมือน Divider
  - `VE = IE·RE`, `VB = VE + VBE`, `VC = VCC − IC·RC`, `VCE = VC − VE`
- validation แยกฟิลด์ เพื่อให้ข้อความชี้ช่องผิดชัด:
  - Fixed: `VCC ต้องมากกว่า 0` · `RB ต้องมากกว่า 0` · `RC ต้องมากกว่า 0` · `β ต้องมากกว่า 0` · `VBE ต้องมากกว่า 0 และน้อยกว่า VCC`
  - Emitter: เหมือน Fixed + `RE ต้องมากกว่า 0`
- region ของโหมดใหม่ใช้ helper ใหม่ `classify_operating_point(ib, vce)`:
  `ib ≤ 0` → cutoff · `vce < 0.2` → saturation · `vce < 0.5` → near-saturation · else active
  (ข้อความ warning ไม่พูดถึง VTH เพราะโหมดนี้ไม่มี VTH)

### 2. `app.py`

- `MODES = {"divider": ("Voltage Divider Bias", ...), "fixed": (...), "emitter": (...)}`
- `DEFAULT_FORMS` แยกต่อโหมด: divider ค่าเดิมทุกตัว; fixed `rb=1000`; emitter `rb=1000, re=1`
- `_mode_from(raw)` → คืน key ที่ถูกต้อง หรือ `None`; **ไม่ fallback เป็น divider**
- `calculate()`:
  ```python
  mode = _mode_from(form.get("mode"))
  if mode is None: error "โหมดวงจรไม่ถูกต้อง"
  elif mode == "divider": inp = DcBiasInput(...); result = calculate_dc_bias(inp)
  elif mode == "fixed":   inp = FixedBiasInput(...); result = calculate_fixed_bias(inp)
  else:                   inp = EmitterBiasInput(...); result = calculate_emitter_bias(inp)
  ```
  แปลง kΩ → Ω ด้วย `_to_ohms` เฉพาะช่องที่โหมดนั้นใช้
- `_format_result(result)` คืน 7 ค่าที่ใช้ร่วมกัน (vb/ve/vc/vce/ib/ic/ie) — ไม่มี vth/rth แล้ว
- `_workings(mode, result)` คืน list ของ `{label, value}` สำหรับ `<details>`:
  divider: VTH, RTH, IB, IE · fixed: IB, IE · emitter: IB, IE
- `_diagram_labels(form, mode)` คืน label ตามโหมด (divider: r1/r2/rc/re; fixed: rb/rc; emitter: rb/rc/re)
- error message นำหน้าด้วยชื่อโหมด: `"Fixed Bias — RB ต้องมากกว่า 0"`
- ส่ง `mode`, `mode_label` ให้ template ทุกครั้ง (GET, POST สำเร็จ, POST error)

### 3. `templates/index.html`

- ใน panel Input: แท็บ 3 อัน (ลิงก์ GET) + `<input type="hidden" name="mode">`
- ฟอร์มแสดงเฉพาะช่องของโหมด; `id`/`name` ตรงกับที่ `app.py` อ่าน (`rb`, `r1`, `r2`, `rc`, `re`)
- panel Circuit: เลือก SVG 3 แบบตาม `mode` — คงสไตล์ซิกแซก + Q1 วงกลม
  - divider: R1 (บน), R2 (ล่าง), RC, RE
  - fixed: RB จากราง VCC ลง base, RC, emitter ลงกราวด์ตรง
  - emitter: RB, RC, RE (มี RE ระหว่าง emitter กับกราวด์)
- panel Results: ป้ายโหมด (`mode_label`) ใต้หัวข้อ + ตาราง 7 แถวเดิม
- ก่อนคำนวณ/หลัง error: ทุกช่องเป็น `—`, กล่องสถานะ idle — ไม่มีเลขค้าง
- `<details>วิธีคำนวณ</details>` loop จาก `workings` (template ไม่รู้สมการ)

### 4. `static/style.css`

- `.mode-tabs` เป็นแถวปุ่มลิงก์ใน panel Input, `.mode-tab.is-active` เด่น
- `.mode-badge` ใน panel Results
- คง grid 3 คอลัมน์ ≥ 1100 px; ต้องยังพอดี 1366×768 (วัดด้วย screenshot)

### 5. `tests/`

- คง assertion เดิมทั้ง 41 ตัว; payload ของ test ที่ POST `/calculate` เพิ่ม `"mode": "divider"`
  (สัญญาณอินพุตเปลี่ยนเพราะมีช่องใหม่ — ไม่ใช่การผ่อน assertion)
- เพิ่ม: ค่าอ้างอิง fixed/emitter (รวม RE=2k), validation รายฟิลด์, region ของโหมดใหม่
- เพิ่ม: route — GET แต่ละโหมดเห็นเฉพาะช่องที่ใช้, POST fixed/emitter ได้ผล, ป้ายโหมดในผล/error, โหมดไม่รู้จัก, error แล้วไม่มีเลขค้าง, A1 ยังได้ 1.230/8.052
- `_diagram_labels(form, mode="divider")` มี default เพื่อให้ test เดิมเรียกแบบเดิมได้

### 6. เอกสาร

- `docs/validation.md`: ตาราง A1–A5 (ค่ามือ, ค่าที่เห็น, วิธีตรวจ, PASS/FAIL/NOT RUN) + A4 prediction ก่อนรัน + ระบุ Playwright MCP = NOT RUN (ไม่มี Node.js/MCP) และวิธีที่ใช้จริง
- `README.md`: โหมดที่รองรับ, วิธีกรอก 1 MΩ = `1000` kΩ, วิธีตรวจซ้ำ

## สิ่งที่ผมตัดสินเอง (เจ้าของงานยังไม่ระบุ)

- ใช้แท็บลิงก์แทน dropdown (เหตุผลในตารางแนวทาง)
- ไม่เพิ่มหน่วย MΩ — ใบงานเองระบุ `1 MΩ = 1,000 kΩ` และลดช่องที่ต้อง validate
- ค่า default ของโหมดใหม่: `RB = 1000 kΩ`, `RE = 1 kΩ`, ค่าที่เหลือตาม Lab 02
- โหมดไม่รู้จักทั้ง GET และ POST → error + ฟอร์ม Divider ว่าง ๆ (ไม่คำนวณ)
- `BiasResult` ใช้ร่วมกันสองโหมดใหม่; Divider คง `DcBiasResult` เดิม
- ข้อความ validation ของโหมดใหม่แยกฟิลด์ (ต่างจาก Divider ที่รวมกลุ่ม) เพื่อให้ A5 ชี้ `RB` ได้ตรง

## เกณฑ์ยอมรับ

1. test ทั้งหมดผ่าน (41 เดิม + ใหม่)
2. A1 ตรง `docs/validation.md` เดิมทุกหลัก
3. A2–A4 อยู่ในเกณฑ์ ±0.01 mA (IC) และ ±0.02 V (VCE)
4. A5 แสดงข้อความจาก Flask ที่เอ่ยถึง `RB`, หน้าไม่ล้ม, ไม่มีเลขค้าง
5. หน้า 1366×768 เห็นครบ 3 panel โดยไม่ต้องเลื่อน
6. มี screenshot เป็นหลักฐานอย่างน้อย 1 กรณี
