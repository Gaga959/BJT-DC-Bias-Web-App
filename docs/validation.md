# Validation — BJT DC Bias (Lab 03: Divider / Fixed / Emitter)

ตรวจผลจากโปรแกรมเทียบค่าที่คำนวณมือ (Forward-Active approximation)
วันที่ตรวจ: 2026-11-17
Commit ที่ใช้ตรวจ: `75bf98d` (`feat: draw per-mode schematics and style mode selector`)
ภาพหลักฐาน: `docs/evidence/lab03-a1.png` … `lab03-a5.png`

## วิธีตรวจ

- **Manual (headless Chrome + Flask)** — รันเซิร์ฟเวอร์จริง
  (`flask --app app run --port 5000`) แล้วเปิดฟอร์ม HTML ที่ POST เข้า
  `/calculate` ด้วย Chrome headless (`--headless=new --window-size=1366,768`)
  จับภาพหน้าผลลัพธ์เป็นหลักฐาน แล้วอ่านค่าจากภาพเทียบกับค่ามือ
- **Playwright MCP = NOT RUN** — เครื่องนี้ไม่มี Node.js และไม่ได้ติดตั้ง
  Playwright MCP จึงใช้ Chrome headless เป็นวิธีสำรอง
- เกณฑ์ผ่าน: `|ΔIC| ≤ 0.01 mA` และ `|ΔVCE| ≤ 0.02 V`
  (ค่าที่แสดงถูกปัดเป็น 3 ตำแหน่ง ดังนั้น Δ จากหน้าจอเป็น 0)

## ค่าคงที่ร่วมทุกกรณี

`VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`, หน่วยตัวต้านทาน `kΩ`

> แอปรองรับหน่วย `kΩ`, `Ω` และ `MΩ` (ใช้กับตัวต้านทานทุกตัวพร้อมกัน)
> ตารางนี้ใช้ `kΩ` ตามใบงาน; เทสต์ `test_mohm_matches_kohm_for_same_physical_value`
> ยืนยันว่า `RB = 1 MΩ` ให้ผลเท่ากับ `RB = 1000 kΩ`

## Prediction ของ A4 (บันทึกก่อนรัน)

A4 คือ Emitter Bias ที่เพิ่ม `RE` จาก 1 kΩ เป็น 2 kΩ
**ทำนายว่า IC จะลดลง** เพราะ emitter degeneration มากขึ้นทำให้กระแสอิมิตเตอร์
และกระแสเบสลดลง — ผลจริงตรงกับคำทำนาย (1.026 → 0.940 mA)

## ผลตรวจ A1–A5

| กรณี | โหมด | อินพุตต่าง | ค่ามือ IC / VCE | เห็นจริง IC / VCE | วิธีตรวจ | ผล |
|---|---|---|---|---|---|---|
| A1 | Divider | `R1=100, R2=22, RE=1` | 1.230 mA / 8.052 V | 1.230 mA / 8.052 V | Manual + `lab03-a1.png` | PASS |
| A2 | Fixed | `RB=1000` | 1.130 mA / 9.514 V | 1.130 mA / 9.514 V | Manual + `lab03-a2.png` | PASS |
| A3 | Emitter | `RB=1000, RE=1` | 1.026 mA / 8.705 V | 1.026 mA / 8.705 V | Manual + `lab03-a3.png` | PASS |
| A4 | Emitter | `RB=1000, RE=2` | 0.940 mA / 8.033 V | 0.940 mA / 8.033 V | Manual + `lab03-a4.png` | PASS |
| A5 | Fixed | `RB=0` | error `RB ต้องมากกว่า 0`, ไม่มีเลขผล | `Fixed Bias — RB ต้องมากกว่า 0`, ตารางเป็น `—`, HTTP 200 | Manual + `lab03-a5.png` | PASS |

- **Playwright MCP**: NOT RUN — ไม่มี Node.js/MCP ในเครื่อง (ดูวิธีตรวจข้างบน)

## A1 — ค่าเต็ม (ต้องตรงกับ `docs/validation.md` เดิมของ Lab 02)

| ปริมาณ | คำนวณมือ | ค่าจากโปรแกรม | ผล |
|---|---|---|---|
| VTH | 2.163934 V | 2.164 V | ตรง (ปัด 3 ตำแหน่ง) |
| RTH | 18.032787 kΩ | 18.03 kΩ | ตรง |
| IB | 12.298581 µA | 12.30 µA | ตรง |
| IC | 1.229858 mA | 1.230 mA | ตรง |
| IE | 1.242157 mA | 1.242 mA | ตรง |
| VE | 1.242157 V | 1.242 V | ตรง |
| VB | 1.942157 V | 1.942 V | ตรง |
| VC | 9.294312 V | 9.294 V | ตรง |
| VCE | 8.052155 V | 8.052 V | ตรง |
| Region | Active | Active | ตรง |

## A2 — Fixed Bias (ค่าเต็ม)

`IB = (VCC − VBE) / RB = 11.3 V / 1 MΩ = 11.300 µA`;
`IC = β·IB = 1.130 mA`; `IE = 1.1413 mA`;
`VC = VCE = VCC − IC·RC = 12 − 2.486 = 9.514 V`

หน้าจอ: VB 0.700 V, VE 0.000 V, VC 9.514 V, VCE 9.514 V, IB 11.30 µA,
IC 1.130 mA, IE 1.141 mA, Active — ตรงทุกค่า

## A3 — Emitter Bias (ค่าเต็ม)

`IB = 11.3 / (1 MΩ + 101·1 kΩ) = 10.2634 µA`; `IC = 1.02634 mA`;
`IE = 1.03660 mA`; `VE = 1.03660 V`; `VB = 1.73660 V`;
`VC = 9.74205 V`; `VCE = 8.70545 V`

หน้าจอ: VB 1.737 V, VE 1.037 V, VC 9.742 V, VCE 8.705 V, IB 10.26 µA,
IC 1.026 mA, IE 1.037 mA, Active — ตรงทุกค่า

## A4 — Emitter Bias, RE = 2 kΩ (ค่าเต็ม)

`IB = 11.3 / (1 MΩ + 101·2 kΩ) = 9.4010 µA`; `IC = 0.94010 mA`;
`IE = 0.94950 mA`; `VE = 1.89900 V`; `VB = 2.59900 V`;
`VC = 9.93178 V`; `VCE = 8.03278 V`

หน้าจอ: VB 2.599 V, VE 1.899 V, VC 9.932 V, VCE 8.033 V, IB 9.40 µA,
IC 0.940 mA, IE 0.950 mA, Active — ตรงทุกค่า และยืนยันคำทำนายว่า IC ลดลง

## A5 — Fixed Bias, RB = 0 (error path)

- หน้าต่าง error แสดง `Fixed Bias — RB ต้องมากกว่า 0`
- ตารางผลลัพธ์ทุกช่องเป็น `—` (ไม่มีเลขผลรอบก่อนค้าง)
- กล่องสถานะกลับเป็น `status-idle`
- HTTP 200 และยังอยู่ในโหมด Fixed Bias (แท็บ/ป้าย/วงจรตรงโหมด)
- ฟอร์มยังคงค่า `RB = 0` ที่ผู้ใช้กรอก เพื่อให้แก้ไขได้

## Test log

รัน 2026-11-17 ด้วย `.venv` (Python 3.14.2, Flask 3.1.3):

```
$ .venv\Scripts\python.exe -m unittest discover -s tests -v
...
Ran 62 tests in 0.333s
OK
```

## วิธีรันซ้ำ

```powershell
# 1) เทสต์อัตโนมัติ
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# 2) เปิดเซิร์ฟเวอร์
.\.venv\Scripts\python.exe -m flask --app app run --port 5000

# 3) เปิด http://127.0.0.1:5000/ แล้วทำตามตาราง A1–A5
#    (ภาพหลักฐานเดิมอยู่ใน docs/evidence/)
```
