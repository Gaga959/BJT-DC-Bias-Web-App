# Reflection — Lab 04 & Engineering Notes

รายวิชา ENG29 2121 Computer Programming for Electrical Engineers (2/2569)  
ระบบจำลองวงจรขยายทรานซิสเตอร์ BJT Common-Emitter Amplifier ร่วมกับ ngspice

---

## 1. คำถามสั้นสำหรับตรวจและประเมินผล Lab 04 (Oral / Defense)

### 1.1 โปรแกรม Python ส่งอะไรให้ ngspice และรับผลกลับมาอย่างไร?
- **การส่งข้อมูล**: Python (`spice_engine.py`) นำพารามิเตอร์จากฟอร์ม เช่น ค่าความต้านทาน, ตัวเก็บประจุ, เบต้า, แอมพลิจูด และความถี่ มาสร้างเป็นข้อความ **SPICE Netlist** (รูปแบบ `.cir`) โดยระบุคำสั่งวิเคราะห์ตามโหมด เช่น `.op`, `.ac dec 20 10 100meg`, หรือ `.tran`
- **การประมวลผล**: เรียกคำสั่งผ่านโมดูล `subprocess.run` ในโหมด Batch (`ngspice_con -b netlist.cir`) โดยระบุ timeout และไม่ใช้ `shell=True` เพื่อความปลอดภัย
- **การรับผล**: ngspice จะบันทึกผลลัพธ์ลงใน stdout หรือ raw data file; Python จะอ่านไฟล์ดังกล่าวแล้วใช้ Regular Expressions หรือ Parsing logic แยกข้อมูลตัวเลข (แรงดันจุดต่อ, กระแส, คู่ความถี่-อัตราขยาย, และเวลา-แรงดัน) แล้วแปลงกลับมาเป็น Data Class ที่มีหน่วยทางวิศวกรรมกำกับชัดเจน

### 1.2 เหตุใดกราฟ .ac และ .tran จึงไม่ใช่สิ่งเดียวกัน?
- **`.ac` (AC Small-Signal Analysis)**: เป็นการวิเคราะห์ใน **Frequency Domain** โดยนำวงจรมาลิเนียไรซ์ (Linearization) รอบจุด DC Operating Point แล้วกวาดความถี่ตั้งแต่ต่ำไปสูง เพื่อดูอัตราขยายเชิงขนาด ($|V_{out}/V_{in}|$) และเฟสเทียบกับความถี่ (Bode Plot)
- **`.tran` (Transient Analysis)**: เป็นการวิเคราะห์ใน **Time Domain** โดยคำนวณปฏิกิริยาของวงจรที่ไม่เป็นเชิงเส้น (Non-linear Differential Equations) ตามเวลาจริง แสดงรูปคลื่น $V_{in}(t)$ และ $V_{out}(t)$ ตามแกนเวลา (ms) ทำให้เห็นทั้งการแกว่ง การกลับเฟส และการขลิบยอดคลื่น (Clipping) เมื่อเกิด Saturation หรือ Cutoff

### 1.3 ถ้าเปลี่ยน Amplitude แต่กราฟไม่เปลี่ยน คุณจะตรวจข้อมูลตรงไหนก่อน?
1. ตรวจสอบ Netlist ที่ส่งให้ ngspice (เปิดดูได้จาก `Netlist ที่ส่งให้ ngspice` ใต้กราฟ) ว่าบรรทัดแหล่งสัญญาณ `VIN` มีการอัปเดตค่า Amplitude ตามที่กรอกหรือไม่
2. ตรวจสอบว่า Browser กำลังแสดงผลจากการจำลองรอบใหม่ หรือเป็น Cache/กราฟเก่า
3. ตรวจสอบ log ของ ngspice ว่าการรันมี error เกิดขึ้นหรือไม่จนทำให้ระบบไม่สามารถอัปเดตกราฟใหม่ได้

### 1.4 Impeccable เปลี่ยนอะไรได้ และไม่ควรเปลี่ยนอะไร?
- **สิ่งที่เปลี่ยนได้**: การจัดวาง Layout (Responsive Grid/Flexbox), การปรับขนาดตัวอักษร, สไตล์ของตารางและปุ่ม, การแสดงผลหน่วยให้อ่านง่ายทั้งบน Desktop และ Mobile, และการปรับ Contrast สีของกราฟ
- **สิ่งที่ไม่ควรเปลี่ยนเด็ดขาด**: สูตรและสมการทางวิศวกรรม, ฟังก์ชันคำนวณใน Python, และการแทนที่ข้อมูลกราฟจริงด้วยภาพ Mockup/Placeholder ที่ไม่ได้มาจากการรัน ngspice

### 1.5 คุณรู้ได้อย่างไรว่า Bode Plot เป็นผลจำลองจริง ไม่ใช่ Mock Data?
1. **การตอบสนองต่ออินพุต**: เมื่อเปลี่ยนค่า $R_E$ จาก 1 kΩ เป็น 2.2 kΩ ค่า Midband Gain บนกราฟจะลดลงตามหลักการ Emitter Degeneration จริง ไม่ใช่ค่าคงที่
2. **การตรวจ Netlist และ Output**: ข้อมูลจุดบนกราฟ SVG แต่ละจุด ($x, y$) ถูกคำนวณขึ้นจากคู่ลำดับความถี่และเกนใน raw output ของ ngspice ที่รันจริงในโฟลเดอร์ชั่วคราว
3. **การทดสอบ Unit Tests**: ชุดทดสอบ `test_ac_gain_falls_when_re_grows` และ `test_tran_run_draws_waveforms` ยืนยันว่าผลลัพธ์ผันแปรตามสภาวะทางฟิสิกส์ของวงจรจริง

---

## 2. บันทึกการทำงานร่วมกับ AI (AI Contribution & Student Verification)

- **ส่วนที่ AI ช่วยสร้าง/ปรับปรุง**:
  1. ช่วยจัดโครงสร้างโมดูล `spice_engine.py` ในการสร้าง Netlist สำหรับโหมด `.op`, `.ac`, และ `.tran` พร้อมทั้งระบบตรวจจับ ngspice executable บนเครื่อง
  2. ออกแบบโมดูล `plotting.py` ที่วาดกราฟ Bode Plot และ Waveform ด้วย Pure Python SVG ไม่ต้องพึ่งพา Third-party chart library ภายนอก
  3. ปรับปรุง UI ใน `templates/index.html` และ `static/style.css` ให้เป็น Responsive Single-Screen Layout และมีแท็บสลับโหมดการวิเคราะห์ชัดเจน
- **ส่วนที่นักศึกษาตรวจสอบและยืนยันด้วยตนเอง**:
  1. ตรวจสอบความถูกต้องของ Netlist และทิศทางการต่อวงจร CE Voltage Divider ร่วมกับ $C_{IN}, C_{OUT}, R_L$
  2. ตรวจสอบความสมเหตุสมผลของผลลัพธ์ DC Operating Point ระหว่างสมการคำนวณมือ (Analytical) และผลจาก ngspice
  3. ตรวจสอบอัตราขยาย Midband Gain (~1.75 ×) และการกลับเฟส 180° ของรูปคลื่น Transient
  4. รันและยืนยันชุดทดสอบทั้งหมด 108 tests และตรวจจับภาพหน้าจอหลักฐานผ่านเบราว์เซอร์จริง
