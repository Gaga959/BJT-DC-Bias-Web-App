# BJT DC Bias Web App

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย BJT
Common-Emitter 3 โหมดไบแอส — **Voltage Divider**, **Fixed Bias** และ
**Emitter Bias** — ส่วนหนึ่งของรายวิชา ENG29 2121 Computer Programming for
Electrical Engineers (2/2569)

เลือกโหมดด้วยแท็บ `Divider | Fixed | Emitter` แล้วกรอกค่าผ่านเบราว์เซอร์
Python Backend (`dc_bias.py`) คำนวณ `IB, IC, IE, VB, VE, VC, VCE`
(โหมด Divider คำนวณ `VTH, RTH` เพิ่ม) ส่งกลับมาแสดงพร้อมหน่วย, validation
และ warning เมื่ออยู่นอก Forward-Active

> ค่าที่แสดงทั้งหมดคำนวณจากอินพุตจริง ไม่มีคำตอบฝังใน HTML และไม่คำนวณด้วย JavaScript

## โครงสร้างโปรเจกต์

```
.
├── app.py                  # Flask application + HTTP routes + unit conversion
├── dc_bias.py              # engineering core (SI units, no HTTP/HTML)
├── templates/index.html    # ฟอร์ม + ผลลัพธ์ + "วิธีคำนวณ"
├── static/style.css        # responsive layout
├── tests/test_dc_bias.py   # unit tests ของสมการและ region
├── tests/test_web.py       # Flask test client tests
├── requirements.txt        # Flask 3.1.3
├── README.md
├── AGENTS.md
└── docs/
    ├── design-note.md
    ├── validation.md
    ├── reflection.md
    ├── preflight-checklist.md
    ├── evidence/            # ภาพหลักฐาน A1–A5 (Lab 03)
    ├── superpowers/specs/2026-11-10-bjt-dc-bias-design.md
    ├── superpowers/specs/2026-11-17-lab03-multi-bias-design.md
    ├── superpowers/plans/2026-11-10-bjt-dc-bias.md
    └── superpowers/plans/2026-11-17-lab03-multi-bias.md
```

## ติดตั้ง

ต้องมี Python 3.10+ (พัฒนาและทดสอบบน 3.14.2) และ Internet สำหรับ `pip`

```powershell
# Windows PowerShell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

```bash
# Linux / macOS / Git Bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

> **หมายเหตุ Windows:** ถ้าคำสั่ง `python` เปิด Microsoft Store แทน interpreter จริง
> ให้ใช้ `py -3` **เฉพาะตอนสร้าง venv** (`py -3 -m venv .venv`)
> หลังจาก activate แล้วให้เรียก `python` (ไม่ใช่ `py -3`) เพราะ `py` จะเลือก
> interpreter global ไม่ใช่ venv — หรือไม่ต้อง activate แล้วเรียก
> `.\.venv\Scripts\python.exe -m ...` ตรง ๆ

## รันเว็บ

```powershell
python -m flask --app app run --debug
```

หรือไม่ activate venv:

```powershell
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

เปิด <http://127.0.0.1:5000/> — ต้องเปิดผ่าน Flask เท่านั้น
(การ double-click `templates/index.html` จะใช้ไม่ได้ เพราะไม่มี Backend)

## หน้าจอ

หน้าเว็บเป็น 3 คอลัมน์ในหน้าจอเดียว (ไม่ต้องเลื่อนบนจอ 1366×768 ขึ้นไป):

| Panel | เนื้อหา |
|---|---|
| Input Parameters | แท็บเลือกโหมด + ฟอร์มค่าอินพุตและหน่วยตัวต้านทาน |
| Circuit | วงจร Common-Emitter แบบ inline SVG ที่ **เปลี่ยนตามโหมดและอัปเดตค่าตามที่กรอก** |
| DC Bias Results | ป้ายชื่อโหมด + ตาราง VB/VE/VC/VCE/IB/IC/IE + กล่องสถานะ + `วิธีคำนวณ` (ยุบไว้) |

- เลือกโหมดด้วยลิงก์แท็บ `/?mode=divider|fixed|emitter` — ไม่ใช้ JavaScript
- Fixed Bias แสดงเฉพาะ `RB`; Emitter Bias แสดง `RB, RC, RE`; Divider แสดง `R1, R2, RC, RE`
- ก่อนกด Calculate: ตารางแสดง `—` และกล่องสถานะสีเทา (layout ไม่กระโดด)
- ค่าในวงจรมาจาก `app._diagram_labels()` เป็นข้อความพร้อมหน่วย — ไม่มี JavaScript
- หน้าจอต่ำกว่า 1100 px: เรียงเป็นคอลัมน์เดียวและเลื่อนได้ตามปกติ

## ทดสอบ

```powershell
python -m unittest discover -s tests -v
```

หรือใช้ interpreter ใน venv โดยไม่ต้อง activate:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### ตรวจ A1–A5 ซ้ำในเบราว์เซอร์

รันเซิร์ฟเวอร์แล้วเปิด <http://127.0.0.1:5000/> เลือกโหมดตามตาราง
(ค่าคงที่ `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`, หน่วย `kΩ`):

| กรณี | โหมด | อินพุตต่าง | IC ที่ต้องเห็น | VCE ที่ต้องเห็น |
|---|---|---|---|---|
| A1 | Divider | `R1=100, R2=22, RE=1` | 1.230 mA | 8.052 V |
| A2 | Fixed | `RB=1000` | 1.130 mA | 9.514 V |
| A3 | Emitter | `RB=1000, RE=1` | 1.026 mA | 8.705 V |
| A4 | Emitter | `RB=1000, RE=2` | 0.940 mA | 8.033 V |
| A5 | Fixed | `RB=0` | error `RB ต้องมากกว่า 0` | ไม่มีเลขผล |

เกณฑ์ผ่าน ±0.01 mA (IC) และ ±0.02 V (VCE) — ภาพหลักฐานและวิธีตรวจละเอียด
อยู่ใน `docs/validation.md` และ `docs/evidence/`

## แบบจำลอง

Forward-Active approximation, β คงที่, VBE คงที่ — ทุกโหมดใช้สมการร่วมกันคือ
`IC = β·IB`, `IE = (β+1)·IB`, `VC = VCC − IC·RC`

**Voltage Divider Bias**

```
VTH = VCC · R2 / (R1 + R2)
RTH = R1 · R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β + 1) · RE)
VE  = IE · RE
VB  = VE + VBE
VCE = VC − VE
```

**Fixed Bias** (ไม่มี RE; emitter ต่อลงกราวด์)

```
IB  = (VCC − VBE) / RB
VE  = 0
VB  = VBE
VCE = VC
```

**Emitter Bias**

```
IB  = (VCC − VBE) / (RB + (β + 1) · RE)
VE  = IE · RE
VB  = VE + VBE
VCE = VC − VE
```

### Region และ warning

| เงื่อนไข | Region | การรายงาน |
|---|---|---|
| Divider: `VTH ≤ VBE` / Fixed, Emitter: `IB ≤ 0` | Cutoff | กระแสถูก clamp เป็น 0, `VC = VCE = VCC` + warning |
| `VCE < 0.2 V` | Saturation | รายงานค่าที่คำนวณได้ + warning ว่าไม่น่าเชื่อถือ |
| `0.2 ≤ VCE < 0.5 V` | Near-saturation | รายงานค่าปกติ + warning ว่าอาจคลาดเคลื่อน |
| อื่น ๆ | Active | รายงานปกติ |

## Validation

| อินพุต | ผลลัพธ์ |
|---|---|
| `VCC ≤ 0` | `VCC ต้องมากกว่า 0` |
| Divider: `R1, R2, RC, RE ≤ 0` | `<ชื่อค่า> ต้องมากกว่า 0` |
| Fixed: `RB, RC ≤ 0` / Emitter: `RB, RC, RE ≤ 0` | `<ชื่อค่า> ต้องมากกว่า 0` |
| `β ≤ 0` | `β ต้องมากกว่า 0` |
| `VBE ≤ 0` หรือ `VBE ≥ VCC` | `VBE ต้องมากกว่า 0 และน้อยกว่า VCC` |
| ค่าว่าง / ไม่ใช่ตัวเลข | `กรุณากรอก <ชื่อค่า> เป็นตัวเลข` |
| โหมดไม่ถูกต้อง / ไม่ส่ง `mode` | `โหมดวงจรไม่ถูกต้อง` (ไม่ fallback เป็น Divider) |

ข้อผิดพลาดทั้งหมดแสดงบนหน้าเดิมด้วย HTTP 200 (หน้าเว็บไม่ล่ม), นำหน้าด้วยชื่อโหมด
เช่น `Fixed Bias — RB ต้องมากกว่า 0` และล้างเลขผลรอบก่อนออกจากตาราง

## หน่วย

- อินพุตตัวต้านทานเลือกหน่วยได้ `kΩ` (ค่าเริ่มต้น) หรือ `Ω` — แปลงเป็น Ω ก่อนคำนวณ
- ไม่มีช่องหน่วย `MΩ`: ค่าที่เป็นเมกะโอห์มให้กรอกเป็น kΩ เช่น **`1 MΩ = 1000 kΩ`**
  (ใส่ `1000` ในช่อง RB/R1/R2) — ค่าที่แสดงในวงจรจะตรงกับที่กรอก
- `dc_bias.py` ใช้ SI units เท่านั้น (V, Ω, A)
- แสดงผล: V (3 ตำแหน่ง), mA (3 ตำแหน่ง), µA (2 ตำแหน่ง), kΩ (2 ตำแหน่ง)

## ขอบเขต

ทำ: Voltage-Divider Bias, Fixed Bias, Emitter Bias, DC operating point,
validation, region warning, tests, หลักฐานตรวจ A1–A5 ในเบราว์เซอร์

ไม่ทำใน Lab นี้: AC small-signal, Bode plot, Transient, SPICE/ngspice,
Collector-Feedback Bias, ฐานข้อมูล, ระบบ login, การ deploy

## เอกสารเพิ่มเติม

- ดีไซน์ Lab 02: `docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md`
- แผนงาน Lab 02: `docs/superpowers/plans/2026-11-10-bjt-dc-bias.md`
- ดีไซน์ Lab 03: `docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md`
- แผนงาน Lab 03: `docs/superpowers/plans/2026-11-17-lab03-multi-bias.md`
- ผลตรวจสอบ A1–A5: `docs/validation.md` + ภาพใน `docs/evidence/`
