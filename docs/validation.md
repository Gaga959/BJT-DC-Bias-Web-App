# Validation — BJT DC Bias

ตรวจผลจากโปรแกรมเทียบค่าที่คำนวณมือ (Forward-Active approximation)
วันที่ตรวจ: 2026-11-10

## ค่าอ้างอิง

อินพุต: `VCC = 12 V`, `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RC = 2.2 kΩ`,
`RE = 1 kΩ`, `β = 100`, `VBE = 0.70 V`

| ปริมาณ | คำนวณมือ | ค่าจากโปรแกรม | ผล |
|---|---|---|---|
| VTH | 2.163934 V | 2.163934 V | ตรง |
| RTH | 18.032787 kΩ | 18.032787 kΩ | ตรง |
| IB | 12.298581 µA | 12.298581 µA | ตรง |
| IC | 1.229858 mA | 1.229858 mA | ตรง |
| IE | 1.242157 mA | 1.242157 mA | ตรง |
| VE | 1.242157 V | 1.242157 V | ตรง |
| VB | 1.942157 V | 1.942157 V | ตรง |
| VC | 9.294312 V | 9.294312 V | ตรง |
| VCE | 8.052155 V | 8.052155 V | ตรง |
| Region | Active | Active | ตรง |

## กรณีขอบเขต

| กรณี | อินพุตที่เปลี่ยน | ผลที่คาด | ผลจริง |
|---|---|---|---|
| Cutoff | `R2 = 1 kΩ` | `VTH = 0.119 V ≤ VBE` → กระแส 0 + warning | ตรง |
| Saturation | `R1 = R2 = RC = 10 kΩ, RE = 100 Ω` | `VCE < 0.2 V` + warning | ตรง |
| Near-saturation | `RC = 1.5 kΩ, RE = 10 Ω` | `0.2 ≤ VCE < 0.5 V` + warning | ตรง |
| R = 0 | `R1 = 0` | ValidationError | ตรง |
| ไม่ใช่ตัวเลข | `VCC = abc` | ข้อความ “เป็นตัวเลข” | ตรง |
| หน่วย Ω vs kΩ | `R1 = 100` เปลี่ยนหน่วย | ผลต่างกันจริง | ตรง |

## Test log

รันเมื่อ 2026-11-10 ด้วย `.venv` ใหม่ (Python 3.14.2, Flask 3.1.3):

```
$ .venv\Scripts\python.exe -m unittest discover -s tests -v
...
Ran 25 tests in 0.134s
OK
```

Smoke test ผ่าน HTTP จริง (`flask --app app run --port 5000`):

```
GET / -> 200 | form: True | button: True
POST valid -> 200 | 1.942, 8.052, 1.230, Active, วิธีคำนวณ, VTH, 18.03: True
POST vcc=abc -> 200 | error "เป็นตัวเลข": True
POST r1=0 -> 200 | error "มากกว่า 0": True
POST cutoff (r2=1) -> 200 | warning "Cutoff": True
```

## วิธีรันซ้ำ

```powershell
python -m unittest discover -s tests -v
```
