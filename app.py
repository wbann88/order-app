import streamlit as st
import fitz  # PyMuPDF
import os
import re
import smtplib
from email.message import EmailMessage
from io import BytesIO

# ==========================================
# 1. ตั้งค่าส่วนตัว (Configuration)
# ==========================================
SMTP_SENDER = "wbann88@gmail.com"
SMTP_PASSWORD = "uthb ryxg zcvl czfw"
SMTP_RECEIVER = "wbann88@gmail.com"

def send_summary_email(summary_text, preview_images):
    """ส่ง Email พร้อมแนบรูปพรีวิว (รับเป็น list ของ bytes)"""
    msg = EmailMessage()
    msg['Subject'] = "🚀 รายงานสรุปออเดอร์ (Smart Label Processor)"
    msg['From'] = SMTP_SENDER
    msg['To'] = SMTP_RECEIVER
    msg.set_content(f"ระบบประมวลผลเสร็จสิ้น:\n\n{summary_text}")

    for filename, img_data in preview_images.items():
        msg.add_attachment(img_data, maintype='image', subtype='jpeg', filename=filename)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SMTP_SENDER, SMTP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"❌ ส่งอีเมลล้มเหลว: {e}")
        return False

def get_extracted_items(page):
    text = page.get_text()
    skus = re.findall(r"(WB[\w\-_]+)", text)
    names = re.findall(r"Weekend begins - ([^\n\r]+)", text)
    
    extracted_items = []
    size_map = {"00": "XS", "01": "S", "02": "M", "03": "L", "04": "", "05": ""}
    
    for i in range(len(skus)):
        full_sku = skus[i]
        p_name = names[i].split()[0] if i < len(names) else "Unknown"
        last_two = full_sku[-2:]
        p_size = size_map.get(last_two, "")
        img_sku = full_sku[:-2]
        extracted_items.append({"full_sku": full_sku, "img_sku": img_sku, "p_name": p_name, "p_size": p_size})
    return extracted_items

# --- ส่วนของหน้าจอ Web App (UI) ---
st.set_page_config(page_title="Smart Label App", layout="centered")
st.title("📦 Smart Label Processor")
st.write("อัปโหลดไฟล์ Label.pdf เพื่อใส่รูปสินค้าและไซส์อัตโนมัติ")

uploaded_file = st.file_uploader("เลือกไฟล์ PDF ของคุณ", type="pdf")

if uploaded_file is not None:
    if st.button("🚀 เริ่มประมวลผล"):
        # อ่าน PDF จากหน่วยความจำ
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        preview_images_dict = {}
        summary_log = ""
        
        progress_bar = st.progress(0)
        total_pages = len(doc)

        for i, page in enumerate(doc):
            items = get_extracted_items(page)
            if not items: continue

            summary_log += f"📄 หน้า {i+1}:\n"
            
            # ลอจิกการวางรูป (Single / Grid) ใช้โค้ดเดิมของคุณ
            if len(items) == 1:
                item = items[0]
                img_path = f"Photo/{item['img_sku']}.jpg"
                page.insert_text((220, 195), item['p_name'], fontsize=8, fontname="helv")
                if os.path.exists(img_path):
                    page.insert_image(fitz.Rect(220, 200, 280, 290), filename=img_path)
                    if item['p_size']:
                        box_rect = fitz.Rect(220, 260, 250, 280)
                        shape = page.new_shape()
                        shape.draw_rect(box_rect)
                        shape.finish(fill=(0,0,0)); shape.commit()
                        page.insert_text((box_rect.x0+3, box_rect.y1-5), item['p_size'], fontsize=14, fontname="cour", color=(1,1,1))
                    summary_log += f"  ✅ {item['full_sku']}\n"
            else:
                # Grid Mode ลอจิกเดิม
                base_x, base_y = 220, 195
                for idx, item in enumerate(items):
                    col, row = idx % 2, idx // 2
                    curr_x, curr_y = base_x + (col*40), base_y + (row*60)
                    page.insert_text((curr_x, curr_y), item['p_name'], fontsize=7, fontname="helv")
                    img_path = f"Photo/{item['img_sku']}.jpg"
                    if os.path.exists(img_path):
                        page.insert_image(fitz.Rect(curr_x, curr_y+5, curr_x+35, curr_y+50), filename=img_path)
                        if item['p_size']:
                            box_rect = fitz.Rect(curr_x, curr_y+35, curr_x+10, curr_y+50)
                            shape = page.new_shape(); shape.draw_rect(box_rect)
                            shape.finish(fill=(0,0,0)); shape.commit()
                            page.insert_text((box_rect.x0+1, box_rect.y1-2), item['p_size'], fontsize=12, fontname="cour", color=(1,1,1))
                    summary_log += f"  ✅ Grid: {item['full_sku']}\n"

            # เก็บรูปพรีวิว
            pix = page.get_pixmap(clip=fitz.Rect(0, 0, 350, 450), matrix=fitz.Matrix(2, 2))
            preview_images_dict[f"page_{i+1}.jpeg"] = pix.tobytes("jpeg")
            progress_bar.progress((i + 1) / total_pages)

        # บันทึกไฟล์ลงหน่วยความจำเพื่อดาวน์โหลด
        out_buffer = BytesIO()
        doc.save(out_buffer)
        doc.close()

        # แสดงผลบนหน้าเว็บ
        st.success("✅ ประมวลผลเสร็จสิ้น!")
        st.download_button(label="📥 ดาวน์โหลดไฟล์ที่ทำเสร็จแล้ว", data=out_buffer.getvalue(), file_name="Final_Work.pdf", mime="application/pdf")
        
        # ส่งอีเมล
        if send_summary_email(summary_log, preview_images_dict):
            st.info("📨 ส่งรายงานสรุปเข้าอีเมลเรียบร้อยแล้ว")
        
        # แสดงรูปตัวอย่างบนมือถือ
        st.subheader("🖼 พรีวิวผลงาน")
        for img_name, img_bytes in preview_images_dict.items():
            st.image(img_bytes, caption=img_name)