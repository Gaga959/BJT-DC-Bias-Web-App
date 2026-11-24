# BJT Amplifier Simulator & DC Bias Web App (Lab 04)

Flask Web Application สำหรับจำลองและคำนวณวงจรขยายทรานซิสเตอร์ **BJT Common-Emitter Amplifier**
ต่อยอดจาก Lab 3 สู่ระบบจำลองทางวิศวกรรมที่เชื่อมต่อกับ **ngspice** จำลองสภาวะจริง
ส่วนหนึ่งของรายวิชา **ENG29 2121 Computer Programming for Electrical Engineers (2/2569)**

---

## คุณสมบัติหลัก (Features)

1. **โหมดคำนวณ DC Bias ดั้งเดิม (Lab 3 Analytical):**
   - รองรับ 3 โหมดไบแอส: **Voltage Divider**, **Fixed Bias**, และ **Emitter Bias**
   - คำนวณ operating point: `IB, IC, IE, VB, VE, VC, VCE` ด้วยแบบจำลอง Forward-Active
   - แสดงผลพร้อมหน่วย, validation ของอินพุต และ warning เมื่ออยู่นอก Forward-Active

2. **โหมดจำลอง SPICE จำลองจริง (Lab 4 ngspice Integration):**
   - จำลองวงจรอ้างอิง **Common-Emitter Voltage Divider Amplifier** ร่วมกับ $C_{IN}, C_{OUT}, R_L$ และแหล่งกำเนิดสัญญาณ
   - **DC Operating Point (`.op`)**: ดึงค่าแรงดันและกระแสจากผลของ ngspice solver จริง
   - **AC Frequency Response (`.ac`)**: วิเคราะห์การตอบสนองความถี่ (10 Hz – 100 MHz) วาดกราฟ **Bode Plot** (Gain Magnitude & Phase) พร้อมคำนวณ Midband Gain และ Lower Cutoff ($f_L$)
   - **Transient Analysis (`.tran`)**: จำลองรูปคลื่นสัญญาณตามเวลา แสดงกราฟเปรียบเทียบ $V_{in}$ และ $V_{out}$ พร้อมแสดงการกลับเฟส 180°
   - **Provenance & Inspection**: แสดง Netlist จริงที่ส่งไปยัง ngspice, เวลาที่ใช้รัน, รหัสโมเดล และสถานะของ Engine แบบโปร่งใส

3. **หน้าจอ Single-Screen Responsive Layout:**
   - ออกแบบแบ่ง 3 คอลัมน์สำหรับ Desktop:
     1. **Circuit & Parameters**: ปรับเปลี่ยนพารามิเตอร์ของวงจรและแหล่งสัญญาณ
     2. **Simulation & Plots**: เลือกโหมดวิเคราะห์ DC / AC / Transient และดูกราฟ
     3. **Engineering Results**: ตารางสรุปค่าเปรียบเทียบ SPICE vs Analytical
   - รองรับหน้าจอมือถือ (Responsive Single Column) ใช้งานง่าย ไม่ตัดปุ่มหรือกราฟ

---

## โครงสร้างโปรเจกต์

```text
.
├── app.py                     # Flask web layer, routing, request validation & dispatch
├── dc_bias.py                 # Analytical DC calculations (Lab 3 reference)
├── spice_engine.py            # ngspice adapter: Netlist generation, subprocess, raw output parsing
├── plotting.py                # Pure Python SVG chart generator (Bode plot & Waveforms)
├── templates/index.html       # Single-screen UI (Forms, Circuit schematic, Plots, Results)
├── static/style.css           # Clean responsive stylesheet
├── requirements.txt           # Dependencies (Flask 3.1.3)
├── README.md                  # Project overview, setup and execution instructions
├── AGENTS.md                  # Rules for AI assistance & engineering provenance
├── tests/
│   ├── test_dc_bias.py        # Lab 3 analytical calculation tests
│   ├── test_spice_engine.py   # ngspice adapter & netlist tests
│   ├── test_plotting.py       # SVG plot rendering tests
│   └── test_web.py            # Flask route & full integration tests (108 tests total)
└── docs/
    ├── validation.md          # รายงานการตรวจสอบผล A1–A5 (Lab 3) และ B1–B8 (Lab 4)
    ├── reflection.md          # บันทึกการเรียนรู้และการตรวจสอบ
    ├── design-note.md         # บันทึกการออกแบบวงจรและสถาปัตยกรรม
    └── evidence/              # ภาพหลักฐานการทดสอบเบราว์เซอร์จริง (A1–A5, B2, B4, B5, B8)
```

---

## ความต้องการของระบบ (Prerequisites)

1. **Python**: เวอร์ชัน 3.10 ขึ้นไป (พัฒนาและทดสอบบน Python 3.14.2)
2. **ngspice**: ติดตั้งโปรแกรมจำลองวงจร ngspice บนเครื่อง
   - *Windows*: ติดตั้ง ngspice (เช่นที่ `C:\Users\<User>\AppData\Local\ngspice\Spice64\bin\ngspice_con.exe` หรือเพิ่มเข้า PATH)
   - *Linux/macOS*: ติดตั้งผ่าน `sudo apt install ngspice` หรือ `brew install ngspice`

---

## วิธีติดตั้งและรันเว็บแอป

### 1. ติดตั้ง Virtual Environment และ Dependencies

```powershell
# Windows PowerShell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. รันเซิร์ฟเวอร์ Flask

```powershell
python -m flask --app app run --debug
```

หรือรันผ่าน Python interpreter ใน `.venv` โดยตรง:

```powershell
.\.venv\Scripts\python.exe -m flask --app app run --port 5000
```

เปิดเว็บเบราว์เซอร์ไปที่: **<http://127.0.0.1:5000/>**

---

## วิธีทดสอบระบบ (Automated Tests)

รันชุดทดสอบ 108 รายการด้วย `unittest`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

> **ผลการทดสอบ:** 108 tests ผ่าน 100% ครอบคลุมการคำนวณ DC Bias, การสร้าง Netlist, การเรียก ngspice จริง, การวาดกราฟ SVG และการทำงานของทุก Flask endpoints

---

## การวิเคราะห์เปรียบเทียบทางวิศวกรรม (Engineering Summary)

| โหมดวิเคราะห์ | แหล่งข้อมูล (Provenance) | ข้อมูลที่แสดง | ผลลัพธ์อ้างอิง (Baseline: VCC=12V, R1=100k, R2=22k, RC=2.2k, RE=1k, RL=10k, β=100) |
|---|---|---|---|
| **DC Analytical** | `dc_bias.py` (สมการมือ) | $V_B, V_E, V_C, V_{CE}, I_B, I_C$ | $I_C = 1.230\,\text{mA},\; V_{CE} = 8.052\,\text{V}$ |
| **DC SPICE** | `ngspice .op` (BJT Model) | $V_B, V_E, V_C, V_{CE}, I_B, I_C$ จาก solver | $I_C = 1.278\,\text{mA},\; V_{CE} = 7.902\,\text{V}$ (ต่างกัน 3.9% จาก Early effect & junction physics) |
| **AC Small-Signal** | `ngspice .ac` (10Hz–100MHz) | Bode Plot, Midband Gain, Phase, $f_L$ | $\text{Midband Gain} = 1.749\,\times\;(4.85\,\text{dB}),\; \text{Phase} = -180.00^\circ,\; f_L = 1.91\,\text{Hz}$ |
| **Transient** | `ngspice .tran` (10mV peak, 1kHz) | Time waveform, $V_{in}, V_{out}$ peak, Inversion | $V_{in} = 10.00\,\text{mV},\; V_{out} = 17.50\,\text{mV},\; \text{Inversion} = 180^\circ$ |

รายละเอียดและตารางบันทึกผลการทดสอบ B1–B8 ฉบับเต็ม ดูได้ใน **[docs/validation.md](docs/validation.md)**
