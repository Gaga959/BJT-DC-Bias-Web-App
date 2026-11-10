# Design (สั้น) — Single-screen layout + dynamic circuit diagram

วันที่: 2026-11-10 · ต่อยอดจาก `2026-11-10-bjt-dc-bias-design.md`

## ทำไม

อาจารย์/ผู้ใช้เห็นภาพตัวอย่างหน้าเว็บที่จัดเป็น 3 คอลัมน์ (Input | Circuit | Results)
และอยากให้แอปเป็นแบบนั้น คือ **เห็นฟอร์ม รูปวงจร และผลลัพธ์พร้อมกันในจอเดียว
ไม่ต้องเลื่อนขึ้นลง** พร้อมรูปวงจรที่กำกับค่าจริงที่กรอก

## เป้าหมาย

- หน้า `/` และ `/calculate` แสดง 3 panel เรียงข้างกันบนจอ ≥ 1100 px
- รูปวงจร Common-Emitter (VCC, R1, R2, RC, RE, Q1) แสดง **ค่าที่ผู้ใช้กรอกจริง**
- ผลลัพธ์เป็นตาราง VB/VE/VC/VCE/IB/IC/IE + กล่องสถานะ (Active / Near-sat / Saturation / Cutoff)
- ทำงานออฟไลน์ ไม่เพิ่ม dependency ไม่ใช้ JavaScript

## ไม่ทำ

- ไม่ทำ AC analysis, กราฟ, print stylesheet, dark mode
- ไม่ทำ live update ตอนพิมพ์ (เลือกแนวทาง A แล้ว)
- ไม่เปลี่ยนสูตร/validation/region logic ใน `dc_bias.py`

## Anti-goal (ถือว่าล้มเหลวถ้าเกิด)

- ต้องเลื่อนหน้าจอที่ 1366×768 เพื่อเห็นทั้ง 3 panel
- ตัวเลขในวงจรไม่ตรงกับช่องที่กรอก (เช่น สลับ R1/R2)
- ค่าในวงจร hardcode ใน template หรือคำนวณด้วย JS
- หน้าจอกระโดด/เปลี่ยนความสูงตอนกด Calculate

## แนวทางที่พิจารณา

| แนวทาง | ผล | แลกกับ |
|---|---|---|
| **A. Server-rendered SVG (เลือก)** | Python เตรียมข้อความพร้อมหน่วย → Jinja วางใน `<text>` | รูปอัปเดตตอนกดปุ่ม ไม่ใช่ตอนพิมพ์ |
| B. JavaScript อัปเดต `<text>` ตอนพิมพ์ | เห็นทันที | เพิ่ม JS, test ยาก, เสี่ยงหน่วย Ω/kΩ ไม่ตรง backend |
| C. วงจรมีแต่ชื่อตัว | ง่ายสุด | ไม่ตอบโจทย์ "ค่าจริง" |

## ดีไซน์

### โครงหน้า

```
header (บรรทัดเดียว: ENG29 2121 · Lab 02 + ชื่อแอป)
[error banner ถ้ามี]
.workspace  (CSS grid 3 คอลัมน์)
├─ .panel.panel-input    ฟอร์มเดิม (ไม่เปลี่ยน field name)
├─ .panel.panel-circuit  <svg class="schematic">
└─ .panel.panel-results  ตารางผลลัพธ์ + กล่องสถานะ + <details>วิธีคำนวณ</details>
```

- grid: `minmax(280px,0.95fr) minmax(320px,1.1fr) minmax(300px,1fr)`, `gap:16px`, `max-width:1400px`
- `< 1100px` → 1 คอลัมน์เรียงลง (ยอมให้ scroll บนมือถือ)
- panel ทุกอันมีหัวข้อ + ไอคอน inline SVG เล็ก (ไม่ใช้ฟอนต์ไอคอน)

### รูปวงจร

- inline `<svg viewBox>` วาดด้วย `<path>/<line>/<circle>/<text>` ล้วน
- ตำแหน่ง label: VCC บนรางบน, R1/R2 ซ้าย, RC/RE ขวา, Q1 พร้อม `β = …` ขวาของทรานซิสเตอร์
- ค่ามาจาก `app._diagram_labels(form)` → dict ของสตริง:
  - `vcc`: `"12 V"`
  - `r1…re`: `"{raw} {kΩ|Ω}"` ตาม select หน่วย
  - `beta`: `"β = 100"`
  - ช่องว่าง/ใช้ไม่ได้ → `"—"`
- GET ใช้ค่า default เดียวกับฟอร์ม (12 V, 100 kΩ, 22 kΩ, 2.2 kΩ, 1 kΩ, β = 100)
- POST error ก็ยังแสดงค่าที่พิมพ์ไว้ (สอดคล้องกับฟอร์มที่ preserve ค่า)

### ผลลัพธ์

- ตาราง 7 แถว (VB, VE, VC, VCE, IB, IC, IE) แถวสลับสี, ค่าชิดขวา
- กล่องสถานะจาก `app._status_note(result)` → `{tone, text}` (tone: ok/warn/danger)
  ข้อความภาษาไทยต่อท้ายด้วยเงื่อนไข เช่น `VCE = 8.05 V > 0.2 V`
- ก่อนกดคำนวณ: ตารางแสดง `—` ทุกช่อง + กล่องสถานะสีเทา "กด Calculate DC Bias เพื่อคำนวณ"
  (ทำให้ layout ไม่กระโดด)
- `<details>วิธีคำนวณ</details>` อยู่ใน panel ผลลัพธ์ (ยุบไว้เป็นค่าเริ่มต้น)

### สิ่งที่ผู้ใช้ยังไม่ได้กำหนด — ผมตัดสินเอง

- ไอคอน panel ใช้ inline SVG วาดเอง 3 อัน (เกียร์/วงจร/กราฟแท่ง)
- ตัวเลขในวงจรแสดงตามข้อความที่พิมพ์ (ไม่ normalize ทศนิยม) เพื่อให้ตรงกับช่องกรอก
- เกณฑ์ "จอเดียว" ทดสอบที่ 1366×768 ด้วย screenshot; ต่ำกว่านั้นยอมให้ scroll

## เทสต์ที่จะเพิ่ม (TDD)

1. GET มี `<svg` และ label default (`12 V`, `100 kΩ`, `β = 100`)
2. POST `r1=47` → วงจรแสดง `47 kΩ`
3. POST `unit=ohm` → `100 Ω` และไม่มี `100 kΩ` ของ R1
4. มี `.panel-input/.panel-circuit/.panel-results` ครบในหน้าเดียว
5. ก่อน POST: ผลลัพธ์เป็น `—` + กล่องสถานะกลาง ๆ, ไม่มีเลขคำตอบ
6. หลัง POST valid: กล่องสถานะ tone ok + ข้อความ Active
7. Cutoff → tone danger + ข้อความ Cutoff
8. ช่องว่าง (`r2=""`) → label วงจรเป็น `—` ไม่ error
9. กัน hardcode: HTML ของ GET ต้องไม่มี `1.942` / `8.052`
