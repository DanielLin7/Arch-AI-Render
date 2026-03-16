import streamlit as st
import base64
import os
import requests
from PIL import Image, ImageDraw
import io
import datetime
import numpy as np

# ==========================================
# 0. 页面基础配置
# ==========================================
st.set_page_config(page_title="Architecture AI Render PRO", layout="wide", initial_sidebar_state="collapsed")

# 🌟 初始化激光画笔的记忆系统
if "mask_stamps" not in st.session_state:
    st.session_state.mask_stamps = []

# ==========================================
# 🛠️ 核心辅助函数
# ==========================================
def pil_to_base64(pil_img, format="JPEG", quality=85):
    buffered = io.BytesIO()
    pil_img.save(buffered, format=format, quality=quality)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def call_gemini_api(api_key, prompt, base_b64, mask_b64=None, aspect_ratio="1:1", image_size="1K"):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    parts = []
    if mask_b64:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base_b64}})
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": mask_b64}})
        parts.append({"text": prompt})
    else:
        parts.append({"text": prompt})
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base_b64}})
        
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"imageConfig": {"aspectRatio": aspect_ratio, "imageSize": image_size}}
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=180)
    response.raise_for_status() 
    return response.json()

def save_render_result(image, prompt, ar_val, q_val, mode_str, history_dir):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = "inpainting_" if "局部" in mode_str else ("4K_up_" if q_val == "4K" else "global_")
    img_filename = os.path.join(history_dir, f"render_{prefix}{timestamp}.png")
    txt_filename = os.path.join(history_dir, f"render_{prefix}{timestamp}.txt")
    
    image.save(img_filename)
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(f"【Mode】{mode_str}\n【Settings】AR: {ar_val} | Res: {q_val} | Size: {image.width}x{image.height}\n【Prompt】{prompt}\n")
    return img_filename

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

st.title("🏗️ 建筑 AI 渲染引擎 PRO / Architecture AI Render PRO v9.0")
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
            st.image(original_base_pil, caption="原始底图 / Original Base", use_column_width=True)

        st.subheader("2. 重绘模式与指令 / Inpainting Prompt")
        
        if original_base_pil:
            inpainting_mode = st.radio(
                "模式 / Mode",
                ["🎨 局部重绘 (激光涂抹)", "🚀 全局渲染 (整体出图)"],
                horizontal=True,
                help="局部重绘：修改画笔涂抹区域；全局渲染：整体风格化。"
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
                prompt = st.text_area("输入重绘指令 (建议英文) / Inpainting Prompt:", value="", help="描述你想要修改的内容，如：'A modern glass balcony'")
            else:
                prompt = st.text_area("输入指令 (建议英文) / Global Prompt:", value="")
        elif is_inpainting:
            st.warning("💡 预设风格将全局影响涂抹区域。如需精确控制，建议切换至『自定义』并详细描述。")

        st.subheader("3. 画幅与参数 / Settings")
        
        if is_inpainting:
            aspect_ratio = st.radio("📐 画幅比例 (已锁定)", ["✨ 自动 (Auto)"], horizontal=True)
            quality = st.radio("✨ 渲染精度", ["1K (标准)", "2K (超清)"], horizontal=True, index=0)
            st.caption("💡 局部重绘强制锁定高清晰度，以确保图像完美融合。")
        else:
            aspect_ratio = st.radio("📐 画幅比例", ["✨ 自动 (Auto)", "16:9", "9:16", "1:1", "4:3", "3:4"], horizontal=True)
            quality = st.radio("✨ 渲染精度", ["512 (极速)", "1K (标准)", "2K (超清)", "4K (大片)"], horizontal=True, index=1)

        st.markdown("<br>", unsafe_allow_html=True) 
        render_btn = st.button("🚀 开始渲染抽卡 / Generate", type="primary", use_container_width=True)

    with col_canvas:
        st.subheader("📺 渲染视口 / Viewport")
        viewport_placeholder = st.empty()
        
        # 准备获取虚拟画笔参数
        brush_x, brush_y, brush_r, brush_shape = 50.0, 50.0, 10.0, "圆形"
        
        if original_base_pil:
            with viewport_placeholder.container():
                if is_inpainting:
                    st.success("🎯 **【原生激光画笔控制台】** \n通过滑块移动绿色准星，点击『涂抹』盖章。多次涂抹可组合成复杂形状！")
                    
                    # 🌟 核心：原生虚拟画笔控制台
                    col_shape, col_size = st.columns(2)
                    with col_shape:
                        brush_shape = st.radio("🖌️ 画笔形状", ["圆形", "方形"], horizontal=True)
                    with col_size:
                        brush_r = st.slider("📏 画笔大小 (半径 %)", 1.0, 50.0, 10.0)
                        
                    col_x, col_y = st.columns(2)
                    with col_x:
                        brush_x = st.slider("↔️ 准星水平位置 (X %)", 0.0, 100.0, 50.0)
                    with col_y:
                        brush_y = st.slider("↕️ 准星垂直位置 (Y %)", 0.0, 100.0, 50.0)

                    # 画笔操作按钮
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    if btn_col1.button("🔴 涂抹当前准星区", use_container_width=True):
                        st.session_state.mask_stamps.append((brush_shape, brush_x, brush_y, brush_r))
                    if btn_col2.button("↩️ 撤销上一笔", use_container_width=True):
                        if st.session_state.mask_stamps:
                            st.session_state.mask_stamps.pop()
                    if btn_col3.button("🗑️ 清空所有涂抹", use_container_width=True):
                        st.session_state.mask_stamps = []

                    # 动态绘制预览图：原始底图 + 红色历史涂抹 + 绿色当前准星
                    preview_img = original_base_pil.copy()
                    if preview_img.mode != 'RGBA':
                        preview_img = preview_img.convert('RGBA')
                        
                    overlay = Image.new('RGBA', preview_img.size, (0, 0, 0, 0))
                    draw = ImageDraw.Draw(overlay)
                    w, h = preview_img.size
                    
                    # 1. 绘制历史盖章（红色填充）
                    for shape, sx, sy, sr in st.session_state.mask_stamps:
                        cx, cy = w * sx / 100, h * sy / 100
                        cr_x, cr_y = w * sr / 100, w * sr / 100 # 保持比例统一用宽度的百分比
                        box = [cx - cr_x, cy - cr_y, cx + cr_x, cy + cr_y]
                        if shape == "圆形":
                            draw.ellipse(box, fill=(255, 50, 50, 180))
                        else:
                            draw.rectangle(box, fill=(255, 50, 50, 180))
                            
                    # 2. 绘制当前绿色准星（空心）
                    hx, hy = w * brush_x / 100, h * brush_y / 100
                    hr_x, hr_y = w * brush_r / 100, w * brush_r / 100
                    hover_box = [hx - hr_x, hy - hr_y, hx + hr_x, hy + hr_y]
                    
                    if brush_shape == "圆形":
                        draw.ellipse(hover_box, outline=(0, 255, 0, 255), width=4)
                    else:
                        draw.rectangle(hover_box, outline=(0, 255, 0, 255), width=4)
                        
                    # 画个十字中心点
                    draw.line([hx-15, hy, hx+15, hy], fill=(0, 255, 0, 255), width=3)
                    draw.line([hx, hy-15, hx, hy+15], fill=(0, 255, 0, 255), width=3)
                    
                    # 合并并显示
                    final_preview = Image.alpha_composite(preview_img, overlay)
                    st.image(final_preview, caption="🎯 绿色为准星，红色为已涂抹的重绘区域", use_column_width=True)
                    
                else:
                    st.success("✨ 当前为【全局渲染】模式，原图已在左侧就绪。请点击左下角开始渲染。")
                    st.image(original_base_pil, caption="输入底图 / Input Base", use_column_width=True)
        else:
            viewport_placeholder.info("👈 请在左侧上传一张底图开始 / Upload an image to start.")

        # ==========================================
        # 🟢 触发主渲染逻辑
        # ==========================================
        if render_btn:
            if not uploaded_file: 
                st.warning("⚠️ 请上传底图！")
            elif not prompt: 
                st.warning("⚠️ 请输入渲染指令！")
            else:
                with viewport_placeholder.container():
                    with st.spinner("💳 算力引擎运转中，大约需要 15-40 秒... / Generating..."):
                        try:
                            q_val = quality.split(" ")[0]
                            if is_inpainting:
                                ar_val, q_val = "自动", "2K"
                            
                            img_w, img_h = original_base_pil.size
                            if "自动" in aspect_ratio or is_inpainting:
                                ratios = {"16:9": 16/9, "9:16": 9/16, "1:1": 1.0, "4:3": 4/3, "3:4": 3/4}
                                ar_val = min(ratios, key=lambda k: abs(ratios[k] - (img_w / img_h)))
                            else:
                                ar_val = aspect_ratio.split(" ")[0]
                            
                            base_pil_processed = original_base_pil.copy()
                            if base_pil_processed.width > 2048 or base_pil_processed.height > 2048:
                                base_pil_processed.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                            
                            base_payload_64 = pil_to_base64(base_pil_processed)
                            mask_payload_64 = None

                            if is_inpainting:
                                # 💡 智能补全：如果用户忘记点涂抹，就直接点生成，我们自动把当前准星当作涂抹区域
                                stamps_to_use = st.session_state.mask_stamps.copy()
                                if not stamps_to_use:
                                    stamps_to_use.append((brush_shape, brush_x, brush_y, brush_r))
                                    
                                # 生成纯黑白蒙版给 AI
                                w, h = base_pil_processed.size
                                mask_pil = Image.new("L", (w, h), 0)
                                mask_draw = ImageDraw.Draw(mask_pil)
                                
                                for shape, sx, sy, sr in stamps_to_use:
                                    cx, cy = w * sx / 100, h * sy / 100
                                    cr_x, cr_y = w * sr / 100, w * sr / 100
                                    box = [cx - cr_x, cy - cr_y, cx + cr_x, cy + cr_y]
                                    if shape == "圆形":
                                        mask_draw.ellipse(box, fill=255)
                                    else:
                                        mask_draw.rectangle(box, fill=255)
                                
                                final_mask_pil = mask_pil.convert("RGB")
                                mask_payload_64 = pil_to_base64(final_mask_pil)
                                st.toast("🛡️ 原生多层叠加蒙版生成成功！")

                            result = call_gemini_api(API_KEY, prompt, base_payload_64, mask_payload_64, ar_val, q_val)

                            try:
                                output_b64 = result['candidates'][0]['content']['parts'][0]['inlineData']['data']
                                image_data = base64.b64decode(output_b64)
                                raw_ai_image = Image.open(io.BytesIO(image_data))
                                
                                img_filename = save_render_result(raw_ai_image, prompt, ar_val, q_val, inpainting_mode, HISTORY_DIR)
                                
                                st.success(f"🎉 渲染成功 / Success! ({raw_ai_image.width} x {raw_ai_image.height} px)")
                                
                                col1, col2 = st.columns([100, 1]) 
                                with col1:
                                    st.image(raw_ai_image, caption=f"AI 渲染成品 | {raw_ai_image.width}x{raw_ai_image.height}", use_column_width=True)
                                    with open(img_filename, "rb") as file:
                                        st.download_button("⬇️ 保存当前高清大图", data=file, file_name=os.path.basename(img_filename), mime="image/png", use_container_width=True)
                                
                                st.session_state['last_render'] = {'prompt': prompt, 'output_b64': output_b64, 'ar_val': ar_val, 'quality': q_val}
                                
                            except KeyError:
                                st.error("🚫 渲染被 Google 安全引擎拦截！(Safety Filter Triggered)")
                                st.warning("💡 拦截原因：敏感内容限制。**切忌要求生成人物/人群/人脸。**")
                                with st.expander("🔍 查看云端原始拦截报告"):
                                    st.json(result)

                        except Exception as e:
                            st.error(f"🌐 渲染异常 / Error: {e}")

        # ==========================================
        # 💎 4K 极限深化直通车
        # ==========================================
        if 'last_render' in st.session_state and st.session_state['last_render']['quality'] in ["512", "1K"]:
            st.divider()
            st.info("💡 满意当前光影？点击下方按钮直升 4K / Upscale to 4K instants.")
            if st.button("💎 4K 极限深化 / Upscale to 4K (Ultra-HD)", type="secondary", use_container_width=True):
                with viewport_placeholder.container():
                    st.warning("⚠️ 4K 深化适用于全局模式，会将上一张成品作为底图进行极致细节丰富。")
                    with st.spinner("💳 4K 深化算力运转中，请耐心等待 1-2 分钟..."):
                        try:
                            last = st.session_state['last_render']
                            result = call_gemini_api(API_KEY, last['prompt'], last['output_b64'], mask_b64=None, aspect_ratio=last['ar_val'], image_size="4K")

                            try:
                                output_b64 = result['candidates'][0]['content']['parts'][0]['inlineData']['data']
                                image_data = base64.b64decode(output_b64)
                                raw_ai_4k_image = Image.open(io.BytesIO(image_data))
                                
                                img_filename = save_render_result(raw_ai_4k_image, last['prompt'], last['ar_val'], "4K", "全局渲染", HISTORY_DIR)
                                
                                st.success(f"🎆 4K 深化圆满成功！ ({raw_ai_4k_image.width}x{raw_ai_4k_image.height})")
                                st.image(raw_ai_4k_image, caption="4K 终极渲染", use_column_width=True)
                                
                                with open(img_filename, "rb") as file:
                                    st.download_button("⬇️ 保存 4K 极限大图", data=file, file_name=os.path.basename(img_filename), mime="image/png", type="primary", use_container_width=True)
                            
                            except KeyError:
                                st.error("🚫 4K 深化被拦截 (提示：指令中勿含人物)")
                        
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
                
                display_stats, saved_prompt, saved_ar = "数据丢失", "A high quality rendering.", "16:9"
                
                if os.path.exists(txt_path):
                    with open(txt_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "【Settings】" in content: 
                            raw_settings = content.split("【Settings】")[1].split("\n")[0].strip()
                            display_stats = raw_settings.replace("AR:", "📐").replace("| Res:", "| ✨").replace("| Size:", "| 📏")
                        elif "【Real 4K Size】" in content:
                            raw_settings = content.split("【Real 4K Size】")[1].split("\n")[0].strip()
                            display_stats = f"📐 自适应 | ✨ 4K | 📏 {raw_settings}"
                        
                        if "16:9" in display_stats: saved_ar = "16:9"
                        elif "9:16" in display_stats: saved_ar = "9:16"
                        elif "1:1" in display_stats: saved_ar = "1:1"
                        elif "4:3" in display_stats: saved_ar = "4:3"
                        elif "3:4" in display_stats: saved_ar = "3:4"
                            
                        if "【Prompt】" in content: 
                            saved_prompt = content.split("【Prompt】")[1].strip()
                else:
                    try:
                        with Image.open(img_path) as tmp_img:
                            display_stats = f"📏 {tmp_img.width}x{tmp_img.height} (早期版本)"
                    except: pass
                
                with cols[i % 3]:
                    st.image(img_path, use_column_width=True)
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
                                        result = call_gemini_api(API_KEY, saved_prompt, history_b64, mask_b64=None, aspect_ratio=saved_ar, image_size="4K")
                                        if 'candidates' in result:
                                            try:
                                                new_img_data = base64.b64decode(result['candidates'][0]['content']['parts'][0]['inlineData']['data'])
                                                new_image = Image.open(io.BytesIO(new_img_data))
                                                save_render_result(new_image, saved_prompt, saved_ar, "4K", "画廊4K深化", HISTORY_DIR)
                                                st.success("✅ 刷新查看 / Refresh")
                                            except KeyError:
                                                st.error("🚫 拦截(敏感)")
                                        else: st.error("❌ 失败")
                                    except Exception as e:
                                        st.error("❌ 错误")

                    with btn_col3:
                        if st.button("🗑️ Del", key=f"del_{file_name}", use_container_width=True):
                            os.remove(img_path)
                            if os.path.exists(txt_path): os.remove(txt_path)
                            st.rerun() 

                    with st.expander(f"📝 查看咒语"):
                        st.code(f"{saved_prompt}")
