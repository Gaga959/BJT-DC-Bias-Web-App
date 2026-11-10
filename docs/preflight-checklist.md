# Pre-flight Checklist — Lab 02 (ENG29 2121)

ตรวจความพร้อมก่อนเริ่ม Brainstorm → Plan → Build
วันที่ตรวจ: 10 พ.ย. 2026 · เครื่อง: `B6815233` · OpenCode Desktop 2.2.6

## 1. Toolchain

| # | รายการ | เกณฑ์ผ่าน | สถานะ | หลักฐาน |
|---|---|---|---|---|
| 1 | Git | `git --version` ใช้ได้ | ✅ | `git version 2.56.0.windows.4` |
| 2 | Git identity | มี user.name / user.email | ✅ | `Gaga959` / `imgodgg64@gmail.com` |
| 3 | GitHub account | Login ใน GitHub Desktop | ✅ | Windows Credential: `https://api.github.com/Gaga959` |
| 4 | OpenCode Desktop | เปิด Session และส่งข้อความได้ | ✅ | v2.2.6 (CLI bundled) |
| 5 | Superpowers plugin | โหลด Skills ได้ | ✅ | `superpowers` commit `22f0b46` (v7.0.2) |
| 6 | Skill `brainstorming` | โหลดผ่าน `skill` tool ได้ | ✅ | อยู่ในรายการ Skills ที่ลงทะเบียน |
| 7 | Python | `python --version` ใช้ได้ | ✅ | `Python 3.14.2` |
| 8 | pip | `pip --version` ใช้ได้ | ✅ | `pip 25.3` |

## 2. Repository

| # | รายการ | สถานะ | หมายเหตุ |
|---|---|---|---|
| 9 | โฟลเดอร์โปรเจกต์ | ✅ | `Documents\GitHub\BJT DC Bias Web App` |
| 10 | Git repo initialized | ✅ | branch `main`, commit `b0d6217 Initial commit` |
| 11 | Remote (GitHub) | ⬜ ยังไม่มี | ต้องกด **Publish repository** ใน GitHub Desktop ครั้งแรก |
| 12 | `.gitignore` | ✅ | ignore `.venv/`, `__pycache__/`, `.env` ฯลฯ |
| 13 | เพิ่ม repo เข้า GitHub Desktop | ⬜ ทำเอง | File → Add Local Repository → เลือกโฟลเดอร์นี้ |

## 3. Scope ที่ตกลงไว้ (Week 2)

- [x] Flask Web App (multi-file) ไม่ใช่ HTML ไฟล์เดียว
- [x] Voltage-Divider Bias เท่านั้น
- [x] Input: `VCC, R1, R2, RC, RE, β, VBE`
- [x] Output: `VB, VE, VC, VCE, IC` (+ IB/IE) พร้อมหน่วย
- [x] Validation + Warning นอก Forward-Active
- [x] Automated tests (≥3 engineering + ≥1 Flask HTTP)
- [ ] AC / Transient / SPICE / Bode — **ไม่อยู่ในขอบเขต**

## 4. ขั้นตอน Commit ด้วย GitHub Desktop

1. เปิด **GitHub Desktop** → `File` → `Add Local Repository…`
2. เลือก `C:\Users\B6815233\Documents\GitHub\BJT DC Bias Web App`
3. แท็บ **Changes** → ตรวจรายการไฟล์ (ควรเห็น `.gitignore`, `docs/preflight-checklist.md`)
4. ช่อง **Summary** พิมพ์: `chore: add preflight checklist and gitignore`
5. (ทางเลือก) **Description**: `เตรียมความพร้อมเครื่องมือสำหรับ Lab 02 ก่อนเริ่มพัฒนา Flask DC Bias app`
6. กด **Commit to main**
7. ครั้งแรกกด **Publish repository** → ตั้งชื่อ `BJT DC Bias Web App` → เลือก Private/Public → Publish
8. ตรวจว่าไม่มีไฟล์ต้องห้ามติดไป: `.venv/`, `.env`, API key

> หมายเหตุ: หลัง Publish แล้ว ให้ใช้ GitHub Desktop commit/push ทุกครั้งที่จบ Task
> โดยตรวจ Diff ก่อนกด Commit เสมอ

## 5. เกณฑ์ตรวจรับที่จะยึด (A1–A7)

- A1 `GET /` → HTTP 200 + ฟอร์ม
- A2 `POST` → Python คำนวณจริง ไม่ hardcode
- A3 ผลตรงกับการคำนวณอิสระ (VTH, RTH, IB, IC, IE, VE, VB, VC, VCE)
- A4 Validation: R≤0, β≤0, ค่าไม่ใช่ตัวเลข → error ที่อ่านได้
- A5 Warning เมื่อ VTH ≤ VBE (cutoff) หรือ VCE ใกล้ saturation
- A6 ≥3 unit tests + ≥1 Flask test client test
- A7 clone repo → install → run → test ตาม README ได้
