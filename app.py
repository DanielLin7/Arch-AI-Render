import streamlit as st
import streamlit.components.v1 as components
import base64
import os
import requests
from PIL import Image
import io
import datetime
import numpy as np
import tempfile

# ==========================================
# 0. 页面基础配置
# ==========================================
st.set_page_config(page_title="Architecture AI Render PRO", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🌟 独家黑科技：自研纯血原生 HTML5 画板引擎
# 彻底抛弃各种开源画板插件，从底层根绝一切 Iframe 跨域白板 Bug
# ==========================================
CANVAS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/streamlit-component-lib/1.3.0/streamlit.js"></script>
    <style>
        body { margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; overflow: hidden; background-color: transparent;}
        #container { position: relative; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid #e0e0e0; background: #fff; touch-action: none; }
        #bg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain; pointer-events: none; user-select: none; }
        canvas { position: absolute; top: 0; left: 0; cursor: crosshair; touch-action: none; }
        .toolbar { display: flex; justify-content: space-between; align-items: center; padding-bottom: 8px; }
        .title { font-size: 14px; font-weight: 600; color: #31333F; }
        button { padding: 6px 12px; background: #ff4b4b; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; transition: background 0.2s; }
        button:hover { background: #ff3333; }
        button:active { transform: scale(0.98); }
    </style>
</head>
<body>
    <div class="toolbar">
        <span class="title">🖌️ 直接在下方自由涂抹 (支持不规则形状)</span>
        <button id="clearBtn">🗑️ 清除重画 (Clear)</button>
    </div>
    <div id="container">
        <img id="bg" src="" draggable="false" />
        <canvas id="drawingCanvas"></canvas>
    </div>

    <script>
        const canvas = document.getElementById('drawingCanvas');
        const ctx = canvas.getContext('2d');
        const bg = document.getElementById('bg');
        const container = document.getElementById('container');
        const clearBtn = document.getElementById('clearBtn');
        
        let isDrawing = false;
        let isReady = false;

        function sendMask() {
            const maskCanvas = document.createElement('canvas');
            maskCanvas.width = canvas.width;
            maskCanvas.height = canvas.height;
            const mCtx = maskCanvas.getContext('2d');
            
            const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const maskData = mCtx.createImageData(canvas.width, canvas.height);
            
            let hasDrawing = false;
            for (let i = 0; i < imgData.data.length; i += 4) {
                if (imgData.data[i+3] > 0) { 
                    maskData.data[i] = 255; maskData.data[i+1] = 255; maskData.data[i+2] = 255; maskData.data[i+3] = 255;
                    hasDrawing = true;
                } else {
                    maskData.data[i] = 0; maskData.data[i+1] = 0; maskData.data[i+2] = 0; maskData.data[i+3] = 255;
                }
            }
            
            if (hasDrawing) {
                mCtx.putImageData(maskData, 0, 0);
                Streamlit.setComponentValue(maskCanvas.toDataURL('image/jpeg'));
            } else {
                Streamlit.setComponentValue("");
            }
        }

        function startDrawing(e) {
            isDrawing = true;
            draw(e);
        }

        function stopDrawing() {
            if (!isDrawing) return;
            isDrawing = false;
            ctx.beginPath();
            sendMask();
        }

        function draw(e) {
            if (!isDrawing) return;
            e.preventDefault();
            
            const rect = canvas.getBoundingClientRect();
            let clientX, clientY;
            
            if (e.touches && e.touches.length > 0) {
                clientX = e.touches[0].clientX; clientY = e.touches[0].clientY;
            } else {
                clientX = e.clientX; clientY = e.clientY;
            }
            
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const x = (clientX - rect.left) * scaleX;
            const y = (clientY - rect.top) * scaleY;

            ctx.lineTo(x, y);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(x, y);
        }

        canvas.addEventListener('mousedown', startDrawing);
        window.addEventListener('mouseup', stopDrawing);
        canvas.addEventListener('mousemove', draw);
        
        canvas.addEventListener('touchstart', startDrawing, {passive: false});
        window.addEventListener('touchend', stopDrawing);
        canvas.addEventListener('touchmove', draw, {passive: false});
        
        clearBtn.addEventListener('click', () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            sendMask();
        });

        function onRender(event) {
            const data = event.detail.args;
            container.style.width = data.width + 'px';
            container.style.height = data.height + 'px';
            
            if (!isReady || bg.src !== "data:image/jpeg;base64," + data.bg_base64) {
                canvas.width = data.width;
                canvas.height = data.height;
                bg.src = "data:image/jpeg;base64," + data.bg_base64;
                isReady = true;
                Streamlit.setComponentValue("");
            }
            
            ctx.strokeStyle = 'rgba(255, 50, 50, 0.7)';
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.lineWidth = data.brush_size;
            
            Streamlit.setFrameHeight(data.height + 45);
        }

        Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
        Streamlit.setComponentReady();
    </script>
</body>
</html>
"""

@st.cache_resource
def get_native_canvas():
    """将自研的 HTML 画板编译为 Streamlit 组件"""
    component_dir = os.path.join(tempfile.gettempdir(), "native_canvas_comp")
    os.makedirs(component_dir, exist_ok=True)
    with open(os.path.join(component_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(CANVAS_HTML)
    return components.declare_component("native_canvas", path=component_dir)

native_canvas = get_native_canvas()

# ==========================================
# 🛠️ 核心辅助函数
# ==========================================
def pil_to_base64(pil_img, format="JPEG", quality=85):
    buffered = io.BytesIO()
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
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

st.title("🏗️ 建筑 AI 渲染引擎 PRO / Architecture AI Render PRO v10.0")
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
                ["🎨 局部重绘 (自由涂抹)", "🚀 全局渲染 (整体出图)"],
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
                prompt = st.text_area("输入重绘指令 (建议英文) / Inpainting Prompt:", value="", help="描述涂抹区域生成什么，如：'A modern glass balcony'")
            else:
                prompt = st.text_area("输入指令 (建议英文) / Global Prompt:", value="")
        elif is_inpainting:
            st.warning("💡 预设风格将全局影响涂抹区域。如需精确控制，建议切换至『自定义』并详细描述（如：'Add a minimalist tree'）。")

        st.subheader("3. 画幅与参数 / Settings")
        
        if is_inpainting:
            aspect_ratio = st.radio("📐 画幅比例 (已锁定)", ["✨ 自动 (Auto)"], horizontal=True)
            quality = st.radio("✨ 渲染精度", ["1K (标准)", "2K (超清)"], horizontal=True, index=0)
            st.caption("💡 局部重绘强制锁定高清晰度，以确保图像完美融合。")
        else:
            aspect_ratio = st.radio("📐 画幅比例", ["✨ 自动 (Auto)", "16:9", "9:16", "1:1", "4:3", "3:4"], horizontal=True)
            quality = st.radio("✨ 渲染精度", ["512 (极速)", "1K (标准)", "2K (超清)", "4K (大片)"], horizontal=True, index=1)

        if is_inpainting and original_base_pil:
            st.divider()
            st.subheader("🖌️ 画笔工具 / Brush Tool")
            stroke_width = st.slider("画笔粗细 / Brush Size:", 5, 100, value=30)

        st.markdown("<br>", unsafe_allow_html=True) 
        render_btn = st.button("🚀 开始渲染抽卡 / Generate", type="primary", use_container_width=True)

    with col_canvas:
        st.subheader("📺 渲染视口 / Viewport")
        viewport_placeholder = st.empty()
        
        canvas_result = None
        if original_base_pil:
            with viewport_placeholder.container():
                col1, col2 = st.columns([100, 1])
                with col1:
                    orig_w, orig_h = original_base_pil.size
                    max_web_w = 700
                    scale_fac = max_web_w / orig_w if orig_w > max_web_w else 1.0
                    web_w, web_h = int(orig_w * scale_fac), int(orig_h * scale_fac)
                    
                    if is_inpainting:
                        # 🌟 绝杀：唤醒我们自己手写的原生自由画板
                        preview_pil = original_base_pil.resize((web_w, web_h), Image.Resampling.LANCZOS)
                        bg_b64 = pil_to_base64(preview_pil)
                        
                        canvas_result = native_canvas(
                            bg_base64=bg_b64,
                            width=web_w,
                            height=web_h,
                            brush_size=stroke_width,
                            key="inpainting_native_canvas"
                        )
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
            elif is_inpainting and (not canvas_result or not canvas_result.startswith("data:image")):
                st.warning("⚠️ 请先在右侧图片上**随意涂抹**你需要重绘的区域！")
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
                                # 提取原生画板传回的完美黑白蒙版
                                b64_data = canvas_result.split(",")[1]
                                mask_image_data = base64.b64decode(b64_data)
                                raw_mask_pil = Image.open(io.BytesIO(mask_image_data)).convert("RGB")
                                final_mask_pil = raw_mask_pil.resize(base_pil_processed.size, Image.Resampling.NEAREST)
                                mask_payload_64 = pil_to_base64(final_mask_pil)
                                st.toast("🛡️ 自研引擎：原生黑白蒙版提取成功！")

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
