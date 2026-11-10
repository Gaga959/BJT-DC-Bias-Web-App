# BJT DC Bias Web App

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย BJT
Common-Emitter แบบ **Voltage-Divider Bias** — ส่วนหนึ่งของรายวิชา
ENG29 2121 Computer Programming for Electrical Engineers (2/2569)

กรอกค่า `VCC, R1, R2, RC, RE, β, VBE` ผ่านเบราว์เซอร์ แล้ว Python Backend
(`dc_bias.py`) คำนวณ `VTH, RTH, IB, IC, IE, VB, VE, VC, VCE` ส่งกลับมาแสดง
พร้อมหน่วย, validation และ warning เมื่ออยู่นอก Forward-Active

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
    ├── superpowers/specs/2026-11-10-bjt-dc-bias-design.md
    └── superpowers/plans/2026-11-10-bjt-dc-bias.md
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

## ทดสอบ

```powershell
python -m unittest discover -s tests -v
```

หรือใช้ interpreter ใน venv โดยไม่ต้อง activate:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## แบบจำลอง

Forward-Active approximation, β คงที่, VBE คงที่:

```
VTH = VCC · R2 / (R1 + R2)
RTH = R1 · R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β + 1) · RE)
IC  = β · IB
IE  = (β + 1) · IB
VE  = IE · RE
VB  = VE + VBE
VC  = VCC − IC · RC
VCE = VC − VE
```

### Region และ warning

| เงื่อนไข | Region | การรายงาน |
|---|---|---|
| `VTH ≤ VBE` | Cutoff | กระแสถูก clamp เป็น 0, `VC = VCE = VCC` + warning |
| `VCE < 0.2 V` | Saturation | รายงานค่าที่คำนวณได้ + warning ว่าไม่น่าเชื่อถือ |
| `0.2 ≤ VCE < 0.5 V` | Near-saturation | รายงานค่าปกติ + warning ว่าอาจคลาดเคลื่อน |
| อื่น ๆ | Active | รายงานปกติ |

## Validation

| อินพุต | ผลลัพธ์ |
|---|---|
| `VCC ≤ 0` | `VCC ต้องมากกว่า 0` |
| `R1, R2, RC, RE ≤ 0` | `R1, R2, RC, RE ต้องมากกว่า 0` |
| `β ≤ 0` | `β ต้องมากกว่า 0` |
| `VBE ≤ 0` หรือ `VBE ≥ VCC` | `VBE ต้องมากกว่า 0 และน้อยกว่า VCC` |
| ค่าว่าง / ไม่ใช่ตัวเลข | `กรุณากรอก <ชื่อค่า> เป็นตัวเลข` |

ข้อผิดพลาดทั้งหมดแสดงบนหน้าเดิมด้วย HTTP 200 (หน้าเว็บไม่ล่ม)

## หน่วย

- อินพุตตัวต้านทานเลือกหน่วยได้ `kΩ` (ค่าเริ่มต้น) หรือ `Ω` — แปลงเป็น Ω ก่อนคำนวณ
- `dc_bias.py` ใช้ SI units เท่านั้น (V, Ω, A)
- แสดงผล: V (3 ตำแหน่ง), mA (3 ตำแหน่ง), µA (2 ตำแหน่ง), kΩ (2 ตำแหน่ง)

## ขอบเขต

ทำ: Voltage-Divider Bias, DC operating point, validation, region warning, tests

ไม่ทำใน Lab นี้: AC small-signal, Bode plot, Transient, SPICE/ngspice,
Bias แบบอื่น, ฐานข้อมูล, ระบบ login, การ deploy

## เอกสารเพิ่มเติม

- ดีไซน์: `docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md`
- แผนงาน: `docs/superpowers/plans/2026-11-10-bjt-dc-bias.md`
- ผลตรวจสอบ: `docs/validation.md`
