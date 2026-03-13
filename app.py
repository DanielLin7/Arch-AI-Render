import streamlit as st
import base64
import os
import requests
from PIL import Image, ImageOps
import io
import datetime
import json
import numpy as np
from streamlit_drawable_canvas import st_canvas 

# ==========================================
# 0. 页面基础配置
# ==========================================
st.set_page_config(page_title="Architecture AI Render PRO", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🔐 SaaS 门禁与密码验证系统
# ==========================================
def check_password():
    def password_entered():
        valid_passwords = ["ARCH2026", "VIP888", "DESIGN2026"] 
        if st.session_state["password"] in valid_passwords:
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 欢迎 / Welcome")
        st.info("💡 请输入授权邀请码以解锁引擎 / Please enter your invite code.")
        st.text_input("🔑 邀请码 / Invite Code:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 欢迎 / Welcome")
        st.text_input("🔑 邀请码 / Invite Code:", type="password", on_change=password_entered, key="password")
        st.error("🚫 密码错误或已过期 / Invalid or expired code.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# ==========================================
# 🚀 核心渲染工作区
# ==========================================
HISTORY_DIR = "render_history"
os.makedirs(HISTORY_DIR, exist_ok=True)

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("⚠️ 未检测到云端 Secrets，请确保已在 Advanced settings 中配置 GEMINI_API_KEY。")
    st.stop()

st.title("🏗️ 建筑 AI 渲染引擎 PRO / Architecture AI Render PRO v6.1")
st.markdown("---")

tab_studio, tab_gallery = st.tabs(["🎨 局部重绘与工作室 / Inpainting Studio", "🖼️ 历史资产库 / Gallery"])

# ------------------------------------------
# Tab 1: 局部重绘工作室
# ------------------------------------------
with tab_studio:
    col_ctrl, col_canvas = st.columns([1, 2], gap="large")

    with col_ctrl:
        st.subheader("1. 基础配置 / Base Setup")
        uploaded_file = st.file_uploader("上传原图或白模 / Upload Original or Sketch", type=['png', 'jpg', 'jpeg'])
        original_base_pil = None 
        
        if uploaded_file is not None:
            image_bytes = uploaded_file.getvalue()
            original_base_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB") 
            # 🌟 修复 1：把左侧的底图预览加回来，提供安全感
            st.image(original_base_pil, caption="原始底图 / Original Base", use_container_width=True)

        st.subheader("2. 重绘模式与指令 / Inpainting Prompt")
        
        if original_base_pil:
            inpainting_mode = st.radio(
                "模式 / Mode",
                ["🎨 局部重绘 (涂抹修改)", "🚀 全局渲染 (整体出图)"],
                horizontal=True,
                help="局部重绘：修改涂抹区域；全局渲染：整体风格化。"
            )
        else:
            st.info("👈 上传图片后即可选择重绘模式")
            inpainting_mode = "🚀 全局渲染 (整体出图)"

        is_inpainting = "局部重绘" in inpainting_mode

        style_presets = {
            "🏛️ 法式新古典别墅 / Neoclassical": "High-end residential villa architectural rendering, Neoclassical style. Pure white smooth stucco facade, elegant dark-framed French windows and doors, intricate wrought iron balcony railings.",
            "🏙️ 现代与 Art Deco 高层 / Modern Art Deco": "High-rise residential building rendering, seamlessly combining Modern and Art Deco styles. Strong vertical emphasis, elegant geometric ornamentation, stepping silhouettes, sleek glass and metallic brass facade.",
            "🌿 极简清水混凝土 / Minimalist Zen": "Minimalist architectural rendering, Japanese Zen style. Fair-faced exposed concrete walls with visible formwork holes, pure geometric volumes.",
            "✍️ 自定义 / Custom Prompt": ""
        }
        selected_style = st.selectbox("选择风格 / Select Style", list(style_presets.keys()))
        prompt = style_presets[selected_style]
        if selected_style == "✍️ 自定义 / Custom Prompt":
            if is_inpainting:
                prompt = st.text_area("输入重绘指令 (建议英文) / Inpainting Prompt:", value="", help="描述你希望在涂抹区域生成什么，比如：'A modern glass balcony railings'")
            else:
                prompt = st.text_area("输入指令 (建议英文) / Global Prompt:", value="")
        else:
            if is_inpainting:
                st.warning("💡 当前为预设风格，将对涂抹区域应用此风格进行局部重绘。建议切换为『自定义』来精确描述重绘内容（如：'Add a minimalist tree'）。")

        st.subheader("3. 画幅与参数 / Settings")
        
        if is_inpainting:
            aspect_ratio = st.radio("📐 画幅比例 (已锁定)", ["✨ 自动 (Auto)"], horizontal=True)
            quality = st.radio("✨ 渲染精度", ["1K (标准)", "2K (超清)"], horizontal=True, index=0)
            st.caption("💡 局部重绘需保持高清晰度以确保融合，已自动锁定最佳参数。")
        else:
            aspect_ratio = st.radio("📐 画幅比例", ["✨ 自动 (Auto)", "16:9", "9:16", "1:1", "4:3", "3:4"], horizontal=True)
            quality = st.radio("✨ 渲染精度", ["512 (极速)", "1K (标准)", "2K (超清)", "4K (大片)"], horizontal=True, index=1)

        if is_inpainting and original_base_pil:
            st.divider()
            st.subheader("🖌️ 画笔工具 / Brush Tool")
            stroke_width = st.slider("画笔大小 / Brush Size:", 5, 100, value=25)
            drawing_mode = st.selectbox("画板动作 / Canvas Action:", ["freedraw", "transform"], index=0, help="freedraw：涂抹；transform：移动/缩放原图(用画笔涂抹前请确保切回freedraw)")

        st.markdown("<br>", unsafe_allow_html=True) 
        render_btn = st.button("🚀 开始渲染抽卡 / Generate", type="primary", use_container_width=True)

    with col_canvas:
        st.subheader("📺 渲染视口 / Viewport")
        viewport_placeholder = st.empty()
        
        if original_base_pil:
            with viewport_placeholder.container():
                col1, col2 = st.columns([100, 1])
                with col1:
                    orig_w, orig_h = original_base_pil.size
                    max_web_w = 700
                    if orig_w > max_web_w:
                        scale_fac = max_web_w / orig_w
                        web_w = int(max_web_w)
                        web_h = int(orig_h * scale_fac)
                    else:
                        web_w = int(orig_w)
                        web_h = int(orig_h)
                    
                    if is_inpainting:
                        st.info("🖌️ 请在下方图片上**涂抹你希望修改的区域**。涂抹完成后点击左侧『开始渲染』。\nTips: 涂满目标区域，不需要保留细节；确保画板动作为 'freedraw'。")
                        
                        # 🌟 修复 2：将原图缩小到画板尺寸，防止高分辨率巨无霸把画板撑爆变成白板
                        canvas_bg = original_base_pil.resize((web_w, web_h), Image.Resampling.LANCZOS)
                        
                        canvas_result = st_canvas(
                            fill_color="rgba(255, 255, 255, 1.0)",
                            stroke_width=stroke_width,
                            stroke_color="rgba(255, 255, 255, 1.0)",
                            background_image=canvas_bg,
                            update_streamlit=True,
                            height=web_h,
                            width=web_w,
                            drawing_mode=drawing_mode,
                            key="inpainting_canvas",
                        )
                    else:
                        st.image(original_base_pil, caption="输入底图 / Input Base", use_container_width=True)
                        st.info("当前为全局渲染模式，如需局部重绘，请在左侧开启『模式』。")
                        canvas_result = None

        elif not uploaded_file:
            viewport_placeholder.info("👈 请在左侧上传一张底图，并选择模式 / Upload an image and select mode to start.")
        
        if render_btn:
            if not uploaded_file: st.warning("⚠️ 请上传底图！")
            elif not prompt: st.warning("⚠️ 请输入重绘指令！")
            elif is_inpainting and (canvas_result is None or canvas_result.image_data is None or not np.any(canvas_result.image_data > 0)):
                st.warning("⚠️ 请先在右侧图片上**涂抹你需要重绘的区域**！")
            else:
                with viewport_placeholder.container():
                    with st.spinner("💳 局部重绘融合中，大约需要 15-40 秒... / Generating Inpainting..."):
                        try:
                            q_val = quality.split(" ")[0]
                            img_w, img_h = original_base_pil.size
                            
                            if is_inpainting:
                                ar_val = "自动"
                                q_val = "2K"
                            
                            if "自动" in aspect_ratio or is_inpainting:
                                r_val = img_w / img_h
                                ratios = {"16:9": 16/9, "9:16": 9/16, "1:1": 1.0, "4:3": 4/3, "3:4": 3/4}
                                ar_val = min(ratios, key=lambda k: abs(ratios[k] - r_val))
                            else:
                                ar_val = aspect_ratio.split(" ")[0]
                            
                            base_pil_processed = original_base_pil.copy()
                            api_limit_size = 2048 
                            if base_pil_processed.width > api_limit_size or base_pil_processed.height > api_limit_size:
                                base_pil_processed.thumbnail((api_limit_size, api_limit_size), Image.Resampling.LANCZOS)
                            
                            buffered = io.BytesIO()
                            base_pil_processed.save(buffered, format="JPEG", quality=85)
                            base_payload_64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

                            payload = None
                            if is_inpainting:
                                mask_data_rgba = canvas_result.image_data
                                mask_pil = Image.fromarray(mask_data_rgba.astype('uint8'), 'RGBA')
                                alpha_channel = mask_pil.split()[-1]
                                threshold = 1
                                binary_mask = alpha_channel.point(lambda p: 255 if p >= threshold else 0)
                                binary_mask = binary_mask.convert("RGB")
                                final_mask_pil = binary_mask.resize(base_pil_processed.size, Image.Resampling.NEAREST)

                                mask_buffered = io.BytesIO()
                                final_mask_pil.save(mask_buffered, format="JPEG", quality=85)
                                mask_payload_64 = base64.b64encode(mask_buffered.getvalue()).decode('utf-8')
                                
                                st.toast("🛡️ 1MB全局压缩引擎启动！局部重绘通道已开启，蒙版生成成功！")

                                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={API_KEY}"
                                payload = {
                                    "contents": [{"parts": [
                                        {"inline_data": {"mime_type": "image/jpeg", "data": base_payload_64}},
                                        {"inline_data": {"mime_type": "image/jpeg", "data": mask_payload_64}},
                                        {"text": prompt}
                                    ]}],
                                    "generationConfig": {"imageConfig": {"aspectRatio": ar_val, "imageSize": q_val}}
                                }
                            else:
                                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={API_KEY}"
                                st.toast("🛡️ 1MB全局压缩引擎启动！全局风格化模式。")
                                payload = {
                                    "contents": [{"parts": [
                                        {"text": prompt},
                                        {"inline_data": {"mime_type": "image/jpeg", "data": base_payload_64}}
                                    ]}],
                                    "generationConfig": {"imageConfig": {"aspectRatio": ar_val, "imageSize": q_val}}
                                }

                            headers = {'Content-Type': 'application/json'}
                            response = requests.post(url, headers=headers, json=payload, timeout=180)

                            if response.status_code == 200:
                                result = response.json()
                                try:
                                    output_b64 = result['candidates'][0]['content']['parts'][0]['inlineData']['data']
                                    image_data = base64.b64decode(output_b64)
                                    
                                    raw_ai_image = Image.open(io.BytesIO(image_data))
                                    img_width, img_height = raw_ai_image.size
                                    
                                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                                    prefix = "inpainting_" if is_inpainting else ""
                                    img_filename = os.path.join(HISTORY_DIR, f"{prefix}render_{timestamp}.png")
                                    txt_filename = os.path.join(HISTORY_DIR, f"{prefix}render_{timestamp}.txt")
                                    
                                    raw_ai_image.save(img_filename)
                                    with open(txt_filename, "w", encoding="utf-8") as f:
                                        mode_str = "【Mode】局部重绘 / Inpainting" if is_inpainting else "【Mode】全局渲染 / Global"
                                        f.write(f"{mode_str}\n【Settings】AR: {ar_val} | Res: {q_val} | Size: {img_width}x{img_height}\n【Prompt】{prompt}\n")
                                        
                                    st.success(f"🎉 渲染完成 / Success! ({img_width} x {img_height} px)")
                                    
                                    col1, col2 = st.columns([100, 1]) 
                                    with col1:
                                        st.image(raw_ai_image, caption=f"AI 渲染成品 | {img_width} x {img_height}", use_container_width=True)
                                        with open(img_filename, "rb") as file:
                                            st.download_button(
                                                label="⬇️ 保存当前图 / Download Image",
                                                data=file,
                                                file_name=f"render_{prefix}_{timestamp}.png",
                                                mime="image/png",
                                                use_container_width=True
                                            )
                                    
                                    st.session_state['last_render'] = {'prompt': prompt, 'output_b64': output_b64, 'ar_val': ar_val, 'quality': q_val}
                                    
                                except KeyError:
                                    st.error("🚫 渲染被 Google 安全引擎拦截！(Safety Filter Triggered)")
                                    st.warning("💡 拦截原因：指令或图片可能触发了敏感内容限制。\n**建议：局部重绘时，切忌要求生成人物/人群/人脸，以防被封杀。**")
                                    with st.expander("🔍 查看云端原始拦截报告"):
                                        st.json(result)
                            else:
                                st.error(f"❌ 失败 / Failed! Status: {response.status_code}")
                                with st.expander("查看详情"):
                                    st.text(response.text)
                        except Exception as e:
                            st.error(f"🌐 错误 / Error: {e}")

        if 'last_render' in st.session_state and st.session_state['last_render']['quality'] in ["512", "1K"]:
            st.divider()
            st.info("💡 满意当前光影？点击下方按钮直升 4K / Upscale to 4K instants.")
            if st.button("💎 4K 极限深化 / Upscale to 4K (Ultra-HD)", type="secondary", use_container_width=True):
                with viewport_placeholder.container():
                    st.warning("⚠️ 4K极限深化适用于全局模式。对局部重绘结果进行整体深化，可能会轻微模糊原保留区域，建议在需要整体高像素出图时使用。")
                    with st.spinner("💳 正在生成 4K 极限细节..."):
                        try:
                            last = st.session_state['last_render']
                            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={API_KEY}"
                            headers = {'Content-Type': 'application/json'}
                            payload = {
                                "contents": [{"parts": [{"text": last['prompt']}, {"inline_data": {"mime_type": "image/jpeg", "data": last['output_b64']}}]}],
                                "generationConfig": {"imageConfig": {"aspectRatio": last['ar_val'], "imageSize": "4K"}}
                            }
                            response = requests.post(url, headers=headers, json=payload, timeout=180)

                            if response.status_code == 200:
                                result = response.json()
                                try:
                                    output_b64 = result['candidates'][0]['content']['parts'][0]['inlineData']['data']
                                    image_data = base64.b64decode(output_b64)
                                    
                                    raw_ai_4k_image = Image.open(io.BytesIO(image_data))
                                    img_width, img_height = raw_ai_4k_image.size
                                    
                                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                                    img_filename = os.path.join(HISTORY_DIR, f"render_4K_upscaled_{timestamp}.png")
                                    txt_filename = os.path.join(HISTORY_DIR, f"render_4K_upscaled_{timestamp}.txt")
                                    
                                    raw_ai_4k_image.save(img_filename)
                                    with open(txt_filename, "w", encoding="utf-8") as f:
                                        f.write(f"【Settings】AR: {last['ar_val']} | Res: 4K | Size: {img_width}x{img_height}\n【Prompt】{last['prompt']}\n")
                                        
                                    st.success(f"🎆 4K 深化成功！ / Upscale Complete! ({img_width}x{img_height})")
                                    st.image(raw_ai_4k_image, caption=f"4K 终极渲染 | {img_width} x {img_height}", use_container_width=True)
                                    
                                    with open(img_filename, "rb") as file:
                                        st.download_button(
                                            label="⬇️ 保存 4K 极限大图 / Download 4K Ultra-HD",
                                            data=file,
                                            file_name=f"render_4K_upscaled_{timestamp}.png",
                                            mime="image/png",
                                            type="primary",
                                            use_container_width=True
                                        )
                                except KeyError:
                                    st.error("🚫 4K 深化被 Google 安全引擎拦截！(提示：请勿在指令中涉及人物生成)")
                            else:
                                st.error("❌ 失败 / Failed!")
                        except Exception as e:
                            st.error(f"🌐 错误 / Error: {e}")

# ------------------------------------------
# Tab 2: 历史画廊
# ------------------------------------------
with tab_gallery:
    st.subheader("📁 历史资产库 / History Assets")
    if os.path.exists(HISTORY_DIR):
        files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".png")]
        files.sort(reverse=True)
        
        if not files:
            st.info("📭 画廊为空 / Gallery is empty.")
        else:
            cols = st.columns(3) 
            for i, file_name in enumerate(files):
                img_path = os.path.join(HISTORY_DIR, file_name)
                txt_path = img_path.replace(".png", ".txt")
                
                display_stats = "数据丢失 / Unknown"
                saved_prompt = "A high quality architectural rendering."
                saved_ar = "16:9"
                
                if os.path.exists(txt_path):
                    with open(txt_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "【Settings】" in content: 
                            raw_settings = content.split("【Settings】")[1].split("\n")[0].strip()
                            display_stats = raw_settings.replace("AR:", "📐").replace("| Res:", "| ✨").replace("| Size:", "| 📏").replace("Real Size:", "📏")
                        elif "【参数】" in content:
                            raw_settings = content.split("【参数】")[1].split("\n")[0].strip()
                            display_stats = raw_settings.replace("比例:", "📐").replace("| 画质:", "| ✨").replace("| 真实尺寸:", "| 📏")
                        elif "【Real 4K Size】" in content:
                            raw_settings = content.split("【Real 4K Size】")[1].split("\n")[0].strip()
                            display_stats = f"📐 自适应 | ✨ 4K | 📏 {raw_settings}"
                        else:
                            try:
                                with Image.open(img_path) as tmp_img:
                                    display_stats = f"📏 {tmp_img.width}x{tmp_img.height} (早期版本)"
                            except:
                                pass
                                
                        if "16:9" in display_stats: saved_ar = "16:9"
                        elif "9:16" in display_stats: saved_ar = "9:16"
                        elif "1:1" in display_stats: saved_ar = "1:1"
                        elif "4:3" in display_stats: saved_ar = "4:3"
                        elif "3:4" in display_stats: saved_ar = "3:4"
                            
                        if "【Prompt】" in content: 
                            saved_prompt = content.split("【Prompt】")[1].strip()
                        elif "【指令】" in content:
                            saved_prompt = content.split("【指令】")[1].strip()
                
                with cols[i % 3]:
                    st.image(Image.open(img_path), use_container_width=True)
                    st.caption(f"**{display_stats}**")
                    
                    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
                    with btn_col1:
                        with open(img_path, "rb") as file:
                            st.download_button("⬇️ DL", data=file, file_name=file_name, mime="image/png", key=f"dl_{file_name}", use_container_width=True)
                    with btn_col2:
                        if "4K" in display_stats:
                            st.button("✔️ Max", key=f"up_{file_name}", use_container_width=True, disabled=True)
                        else:
                            if st.button("💎 4K", key=f"up_{file_name}", use_container_width=True):
                                with st.spinner("💳..."):
                                    try:
                                        with open(img_path, "rb") as old_img_file:
                                            history_b64 = base64.b64encode(old_img_file.read()).decode('utf-8')
                                        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={API_KEY}"
                                        payload = {"contents": [{"parts": [{"text": saved_prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": history_b64}}]}], "generationConfig": {"imageConfig": {"aspectRatio": saved_ar, "imageSize": "4K"}}}
                                        response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload, timeout=180)
                                        if response.status_code == 200:
                                            result = response.json()
                                            try:
                                                new_img_data = base64.b64decode(result['candidates'][0]['content']['parts'][0]['inlineData']['data'])
                                                new_image = Image.open(io.BytesIO(new_img_data))
                                                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                                                new_image.save(os.path.join(HISTORY_DIR, f"render_4K_up_{ts}.png"))
                                                with open(os.path.join(HISTORY_DIR, f"render_4K_up_{ts}.txt"), "w", encoding="utf-8") as f:
                                                    f.write(f"【Settings】AR: {saved_ar} | Res: 4K | Size: {new_image.size[0]}x{new_image.size[1]}\n【Prompt】{saved_prompt}\n")
                                                st.success("✅ 完成 / Done! 刷新查看 / Refresh to see.")
                                            except KeyError:
                                                st.error("🚫 4K 深化被拦截 (敏感指令)")
                                        else:
                                            st.error("❌ Failed")
                                    except Exception as e:
                                        st.error(f"❌ 错误: {e}")

                    with btn_col3:
                        if st.button("🗑️ Del", key=f"del_{file_name}", use_container_width=True):
                            os.remove(img_path)
                            if os.path.exists(txt_path):
                                os.remove(txt_path)
                            st.rerun() 

                    with st.expander(f"📝 查看咒语指令 (Prompt)"):
                        st.code(f"{saved_prompt}")
