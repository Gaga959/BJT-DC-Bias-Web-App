# Design Note — BJT DC Bias Web App

สรุปการตัดสินใจออกแบบสำหรับ Lab 02 (รายละเอียดเต็มอยู่ที่
`docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md`)

## ทางเลือกการแสดงผล

| ทางเลือก | ลักษณะ | แลกกับ |
|---|---|---|
| A Minimal | ค่าสุดท้าย + badge + warning | เร็ว แต่ตรวจย้อนกลับยาก |
| **B Standard (เลือก)** | ค่าสุดท้าย + `<details>` “วิธีคำนวณ” แสดง VTH, RTH, IB, IE | งานเพิ่มเล็กน้อย ได้ประโยชน์ด้าน A3 |
| C Full teaching | สมการแทนเลขทุกบรรทัด | เวลา/test เพิ่มมาก เสี่ยงไม่จบในคาบ |

**เหตุผลที่เลือก B:** ค่าที่แสดงใน “วิธีคำนวณ” ยังคำนวณจาก Python จริง
จึงไม่ขัดเงื่อนไข “ห้าม hardcode” แต่ช่วยให้ตรวจผลกับค่ามือได้ตามเกณฑ์ A3
และตอบคำถามท้ายใบงานได้

## การแบ่งชั้น

```
Browser → Flask route (app.py) → dc_bias.calculate_dc_bias() → Jinja template
```

- `app.py` แปลงหน่วย (kΩ → Ω) และแปลงข้อความเป็นตัวเลข
- `dc_bias.py` รับ SI เท่านั้น — test ได้โดยไม่ต้องมี Flask
- template ไม่มีสมการและไม่มีเลขคำตอบ

## Region thresholds

| เงื่อนไข | Region | หมายเหตุ |
|---|---|---|
| `VTH ≤ VBE` | cutoff | clamp กระแสเป็น 0, `VB = VTH`, `VC = VCE = VCC` |
| `VCE < 0.2 V` | saturation | รายงานค่าแต่ติด warning |
| `0.2 ≤ VCE < 0.5 V` | near-saturation | warning ว่าอาจคลาดเคลื่อน |
| อื่น ๆ | active | ไม่มี warning |

ค่าคงที่ `VCE_SAT = 0.2`, `VCE_NEAR_SAT = 0.5` อยู่ใน `dc_bias.py`

## ข้อจำกัดที่รู้ตัว

- เป็น Forward-Active approximation ไม่ใช่ SPICE
- β และ VBE คงที่ ไม่ขึ้นกับอุณหภูมิ/กระแส
- ตัวต้านทานทุกตัวใช้หน่วยร่วมกัน (เลือก Ω หรือ kΩ ทั้งกลุ่ม)
