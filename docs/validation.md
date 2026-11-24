# Validation — BJT DC Bias & CE Amplifier Simulator

ตรวจผลจากโปรแกรมเทียบค่าที่คำนวณมือ (Analytical) และผลการจำลอง SPICE จริงจาก ngspice
รายวิชา ENG29 2121 Computer Programming for Electrical Engineers (2/2569)

---

# ส่วนที่ 1: Lab 03 — Multi-Bias DC (Divider / Fixed / Emitter)

ตรวจผลจากโปรแกรมเทียบค่าที่คำนวณมือ (Forward-Active approximation)  
วันที่ตรวจ: 2026-11-17  
Commit ที่ใช้ตรวจ: `75bf98d`  
ภาพหลักฐาน: `docs/evidence/lab03-a1.png` … `lab03-a5.png`  

## วิธีตรวจ Lab 03

- **Manual (headless Chrome + Flask)** — รันเซิร์ฟเวอร์จริง
  (`flask --app app run --port 5000`) แล้วเปิดฟอร์ม HTML ที่ POST เข้า
  `/calculate` ด้วย Chrome headless (`--headless=new --window-size=1366,768`)
  จับภาพหน้าผลลัพธ์เป็นหลักฐาน แล้วอ่านค่าจากภาพเทียบกับค่ามือ
- **Playwright MCP = NOT RUN** — เครื่องนี้ไม่มี Node.js และไม่ได้ติดตั้ง
  Playwright MCP จึงใช้ Chrome headless เป็นวิธีสำรอง
- เกณฑ์ผ่าน: `|ΔIC| ≤ 0.01 mA` และ `|ΔVCE| ≤ 0.02 V`

## ค่าคงที่ร่วมทุกกรณี Lab 03

`VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`, หน่วยตัวต้านทาน `kΩ`

## ผลตรวจ A1–A5

| กรณี | โหมด | อินพุตต่าง | ค่ามือ IC / VCE | เห็นจริง IC / VCE | วิธีตรวจ | ผล |
|---|---|---|---|---|---|---|
| A1 | Divider | `R1=100, R2=22, RE=1` | 1.230 mA / 8.052 V | 1.230 mA / 8.052 V | Manual + `lab03-a1.png` | PASS |
| A2 | Fixed | `RB=1000` | 1.130 mA / 9.514 V | 1.130 mA / 9.514 V | Manual + `lab03-a2.png` | PASS |
| A3 | Emitter | `RB=1000, RE=1` | 1.026 mA / 8.705 V | 1.026 mA / 8.705 V | Manual + `lab03-a3.png` | PASS |
| A4 | Emitter | `RB=1000, RE=2` | 0.940 mA / 8.033 V | 0.940 mA / 8.033 V | Manual + `lab03-a4.png` | PASS |
| A5 | Fixed | `RB=0` | error `RB ต้องมากกว่า 0`, ไม่มีเลขผล | `Fixed Bias — RB ต้องมากกว่า 0`, ตารางเป็น `—`, HTTP 200 | Manual + `lab03-a5.png` | PASS |

---

# ส่วนที่ 2: Lab 04 — BJT Common-Emitter Amplifier Simulator (ngspice)

ทดสอบการจำลองวงจรขยาย Common-Emitter (Voltage Divider Reference) ด้วย **ngspice**  
วิเคราะห์ครอบคลุม **DC Operating Point (.op)**, **AC Frequency Response (.ac)** และ **Transient Response (.tran)**  
วันที่ตรวจ: 2026-11-24  
ภาพหลักฐาน: `docs/evidence/lab04-b2-dc.png`, `lab04-b4-ac.png`, `lab04-b5-tran.png`, `lab04-b8-desktop.png`, `lab04-b8-mobile.png`  

## เครื่องมือและสภาพแวดล้อมที่ใช้ตรวจ

- **Python**: 3.14.2 (ผ่าน `.venv`) + Flask 3.1.3
- **SPICE Engine**: ngspice-43 (ติดตั้งที่ `C:\Users\B6815233\AppData\Local\ngspice\Spice64\bin\ngspice_con.exe`)
- **BJT Model**: `QNPN (IS=1e-14, BF=100, VAF=100, RB=10, RC=1, RE=0.5)`
- **Browser Automation / Verification**: 
  - **Playwright MCP = NOT RUN** — เครื่องนี้ไม่มี Node.js (`node: not found`) จึงไม่ได้ติดตั้ง Playwright MCP
  - **วิธีสำรองที่ใช้จริง**: ตรวจผ่าน Headless Google Chrome (`C:\Program Files\Google\Chrome\Application\chrome.exe`) + Automated Test Client (`tests/test_web.py`, `tests/test_spice_engine.py`) ครอบคลุม 108 tests

## วงจร CE Voltage Divider อ้างอิง (Baseline Fixture)

- `VCC = 12 V`, `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RC = 2.2 kΩ`, `RE = 1 kΩ`, `RL = 10 kΩ`
- `CIN = 10 µF`, `COUT = 10 µF`
- แหล่งสัญญาณ: Sine `Amplitude = 10 mV (peak)`, `Frequency = 1 kHz`
- ทรานซิสเตอร์: NPN Q1 (`β = 100`)

---

## สรุปผลตรวจ B1–B8 (Lab 04 Quality Gate)

| Case | หัวข้อ | Action / Input | Expected / Reference | Observed ที่เห็นจริง | หลักฐาน | Status |
|---|---|---|---|---|---|---|
| **B1** | Regression | ทดสอบโหมด Fixed, Emitter, Divider จาก Lab 3 | ผลคำนวณ analytical ตรงค่าเดิม ไม่เสียหาย | คำนวณ A1–A5 ผ่านครบทุกเงื่อนไข, 108 unit tests ผ่าน 100% | `tests/test_web.py`, `tests/test_dc_bias.py` | **PASS** |
| **B2** | DC SPICE | Run DC (`.op`) ด้วยพารามิเตอร์ Baseline | ngspice คืน VB, VE, VC, VCE, IC จาก output จริง ใกล้เคียง analytical | VB=1.949 V, VE=1.289 V, VC=9.191 V, VCE=7.902 V, IC=1.278 mA, IB=11.91 µA (Status: Success) | `lab04-b2-dc.png`, Netlist log | **PASS** |
| **B3** | Change RE | เปลี่ยน RE จาก 1 kΩ เป็น 2.2 kΩ แล้ว Run DC | Emitter degeneration เพิ่มขึ้น -> IC ต้องลดลง, VCE เพิ่มขึ้น | IC ลดลงจาก 1.278 mA เป็น 0.638 mA, VCE เพิ่มจาก 7.902 V เป็น 9.181 V | `test_op_changes_when_re_changes` | **PASS** |
| **B4** | AC Response | Run AC (`.ac`) sweep 10 Hz – 100 MHz | แสดงกราฟ Bode (Magnitude/Phase), Midband gain สอดคล้องทฤษฎี | Midband gain = 1.749 × (4.85 dB), Phase = -180.00°, fL = 1.91 Hz, กราฟ SVG สร้างจากจุดจริง | `lab04-b4-ac.png` | **PASS** |
| **B5** | Transient | Run `.tran` ที่ 10 mV peak, 1 kHz | คลื่น Vin และ Vout รูป Sine สัญญาณกลับเฟส 180° | Vin peak = 10.00 mV, Vout peak = 17.50 mV, Gain = 1.75 ×, สัญญาณกลับเฟส 180° ตามคุณสมบัติ CE | `lab04-b5-tran.png` | **PASS** |
| **B6** | Change Source | เปลี่ยน Amplitude (เช่น 20 mV) หรือความถี่ | รูปร่างคลื่นและช่วงเวลาเปลี่ยนตามสัญญาณใหม่ ไม่ใช่ mock | คลื่น Waveform และสเกลเวลาปรับเปลี่ยนตามพารามิเตอร์แหล่งสัญญาณจริง | `test_transient_amplitude_tracks_input` | **PASS** |
| **B7** | Invalid / Fail | ใส่ `RE = 0` หรือทดสอบกรณี engine error | แจ้งข้อความเตือนชัดเจน ไม่ crash, ไม่แสดงผลสำเร็จปลอม | แสดง error: `RE ต้องมากกว่า 0`, กล่องสถานะไม่เป็น Success, ตารางเป็น `—` | `test_zero_re_reports_error_and_no_success` | **PASS** |
| **B8** | UI & Layout | ตรวจสอบ Desktop (1280 px) และ Mobile (390 px) | แสดงผลชัดเจน แบ่งสัดส่วน 3 คอลัมน์บนจอใหญ่ และเรียงคอลัมน์เดียวบนจอมือถือ | Desktop 3 panels อ่านค่าง่าย; Mobile layout responsive ไม่ตัดปุ่มหรือกราฟ | `lab04-b8-desktop.png`, `lab04-b8-mobile.png` | **PASS** |

---

## รายละเอียดเชิงวิศวกรรมของผลการจำลอง

### 1. เปรียบเทียบผล DC: Analytical (Lab 3) vs. SPICE (Lab 4)

| ปริมาณ | Analytical (dc_bias.py) | SPICE (ngspice .op) | ส่วนต่าง (Difference) | หมายเหตุเชิงวิศวกรรม |
|---|---|---|---|---|
| **VB** | 1.942 V | 1.949 V | +0.007 V (+0.36%) | SPICE คิดผล junction potential จากสมการไดโอดจริง |
| **VE** | 1.242 V | 1.289 V | +0.047 V (+3.78%) | VBE ใน SPICE คือ ~0.660 V ที่กระแสดังกล่าว (Analytical ฟิกซ์ 0.70 V) |
| **VC** | 9.294 V | 9.191 V | -0.103 V (-1.11%) | สอดคล้องกับ IC ที่ไหลผ่าน RC สูงกว่าเล็กน้อย |
| **VCE** | 8.052 V | 7.902 V | -0.150 V (-1.86%) | อยู่ในย่าน Forward-Active ที่เสถียรทั้งคู่ |
| **IB** | 12.30 µA | 11.91 µA | -0.39 µA (-3.17%) | ผลจาก Early voltage (VAF=100) และเบต้าจริงในโมเดล |
| **IC** | 1.230 mA | 1.278 mA | +0.048 mA (+3.90%) | ใกล้เคียงกันมาก (คลาดเคลื่อน < 4%) ยืนยันความถูกต้องของทั้งสองโมเดล |

### 2. ผลการวิเคราะห์ AC Small-Signal (.ac)

- **สมการประมาณตามทฤษฎี**:
  $$\text{Gain} \approx \frac{R_C \parallel R_L}{r_e + R_E} \approx \frac{2.2\,\text{k}\Omega \parallel 10\,\text{k}\Omega}{\frac{26\,\text{mV}}{1.28\,\text{mA}} + 1\,\text{k}\Omega} \approx \frac{1.803\,\text{k}\Omega}{20.3\,\Omega + 1\,\text{k}\Omega} \approx 1.767\,\times \quad (4.94\,\text{dB})$$
- **ผลจาก ngspice**:
  - **Midband Gain**: **1.749 ×** (4.85 dB) — ตรงกับทฤษฎี (คลาดเคลื่อนเพียง 1%)
  - **Phase**: **-180.00°** (กลับเฟสอย่างสมบูรณ์ในย่าน midband)
  - **Lower Cutoff ($f_L$)**: **1.91 Hz** (กำหนดโดย coupling capacitors $C_{IN}=10\,\mu\text{F}$ และ $C_{OUT}=10\,\mu\text{F}$)
  - **Upper Cutoff ($f_H$)**: ไม่พบจุด -3 dB ในช่วง sweep 100 MHz เนื่องจากไม่ได้ใส่ parasitic capacitance เพิ่มเติมในโมเดล

### 3. ผลการวิเคราะห์ Transient (.tran)

- **Input**: Sine 10 mV peak, 1 kHz ($T = 1\,\text{ms}$)
- **Output**: Sine 17.50 mV peak, 1 kHz
- **อัตราขยายขนาดจริง**: $\frac{17.50\,\text{mV}}{10.00\,\text{mV}} = 1.75\,\times$
- **ความสัมพันธ์เชิงเฟส**: เมื่อ Vin เป็นบวกยอดคลื่น Vout จะเป็นลบยอดคลื่น (Inverted 180°) ชัดเจน

---

## บันทึกการรัน Automated Test Suite

รันด้วย `.venv` (Python 3.14.2) ครอบคลุมทั้ง Lab 03 และ Lab 04:

```powershell
PS C:\Users\B6815233\Documents\Default Project\BJT-DC-Bias-Web-App> .\.venv\Scripts\python.exe -m unittest discover -s tests -v
...
Ran 108 tests in 5.456s

OK
```

ทุก 108 tests ผ่าน 100% (ไม่มีข้อผิดพลาด, ครอบคลุมสมการ DC, SPICE Adapter, SVG Plotting และ Flask Routes)
