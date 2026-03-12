import streamlit as st
import base64
import os
import requests
from PIL import Image, ImageOps
import io
import datetime
import json
import numpy as np
# 🌟 新增的核心插件：网页画板
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

# ⚠️ 从云端金库安全读取 API Key
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("⚠️ 未检测到云端 Secrets，请确保已在 Advanced settings 中配置 GEMINI_API_KEY。")
    st.stop()

st.title("🏗️ 建筑 AI 渲染引擎 PRO / Architecture AI Render PRO v6.0")
st.markdown("---")

tab_studio, tab_gallery = st.tabs(["🎨 局部重绘与工作室 / Inpainting Studio", "🖼️ 历史资产库 / Gallery"])

# ------------------------------------------
# Tab 1: 局部重绘工作室 (核心升级)
# ------------------------------------------
with tab_studio:
    col_ctrl, col_canvas = st.columns([1, 2], gap="large")

    with col_ctrl:
        st.subheader("1. 基础配置 / Base Setup")
        uploaded_file = st.file_uploader("上传原图或白模 / Upload Original or Sketch", type=['png', 'jpg', 'jpeg'])
        original_base_pil = None 
        
        if uploaded_file is not None:
            image_bytes = uploaded_file.getvalue()
            # 强制转为 RGB，防止部分带透明通道的 PNG 报错
            original_base_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB") 

        st.subheader("2. 重绘模式与指令 / Inpainting Prompt")
        
        # 🌟 V6.0 核心逻辑：判断模式
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
            # 自动模式下，如果是重绘，需要加一些提示词
            if is_inpainting:
                st.warning("💡 当前为预设风格，将对涂抹区域应用此风格进行局部重绘。建议切换为『自定义』来精确描述重绘内容（如：'Add a minimalist tree'）。")

        st.subheader("3. 画幅与参数 / Settings")
        
        # 局部重绘下，锁定比例，不能压缩得太厉害，以保持融合
        if is_inpainting:
            aspect_ratio = st.radio("📐 画幅比例 (已锁定)", ["✨ 自动 (Auto)"], horizontal=True)
            quality = st.radio("✨ 渲染精度", ["1K (标准)", "2K (超清)"], horizontal=True, index=0)
            st.caption("💡 局部重绘需保持高清晰度以确保融合，已自动锁定最佳参数。")
        else:
            aspect_ratio = st.radio("📐 画幅比例", ["✨ 自动 (Auto)", "16:9", "9:16", "1:1", "4:3", "3:4"], horizontal=True)
            quality = st.radio("✨ 渲染精度", ["512 (极速)", "1K (标准)", "2K (超清)", "4K (大片)"], horizontal=True, index=1)

        # 🌟 V6.0 画笔设置：仅在重绘模式下显示
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
        
        # 🌟 V6.0 核心更新：召唤画板
        if original_base_pil:
            with viewport_placeholder.container():
                # 计算适配比例，保持画板不撑爆屏幕
                col1, col2 = st.columns([100, 1]) # 小技巧让画板居中
                with col1:
                    orig_w, orig_h = original_base_pil.size
                    max_web_w = 700
                    if orig_w > max_web_w:
                        scale_fac = max_web_w / orig_w
                        web_w = max_web_w
                        web_h = int(orig_h * scale_fac)
                    else:
                        web_w = orig_w
                        web_h = orig_h
                    
                    if is_inpainting:
                        st.info("🖌️ 请在下方图片上**涂抹你希望修改的区域**。涂抹完成后点击左侧『开始渲染』。\nTips: 涂满目标区域，不需要保留细节；确保画板动作为 'freedraw'。")
                        canvas_result = st_canvas(
                            fill_color="rgba(255, 255, 255, 1.0)",  # 蒙版白色（涂抹区域）
                            stroke_width=stroke_width,
                            stroke_color="rgba(255, 255, 255, 1.0)",
                            background_image=original_base_pil,
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
            # 核心验证：如果是重绘模式，必须检查是否涂抹了
            elif is_inpainting and (canvas_result is None or canvas_result.image_data is None or not np.any(canvas_result.image_data > 0)):
                st.warning("⚠️ 请先在右侧图片上**涂抹你需要重绘的区域**！")
            else:
                with viewport_placeholder.container():
                    with st.spinner("💳 局部重绘融合中，大约需要 15-40 秒... / Generating Inpainting..."):
                        try:
                            q_val = quality.split(" ")[0]
                            # 1. 确定最终比例与压缩 (保持 v5.8 的 1MB 全局压缩逻辑)
                            img_w, img_h = original_base_pil.size
                            
                            if is_inpainting:
                                ar_val = "自动"
                                q_val = "2K" # 局部重绘强制至少 2K 以保持融合度
                            
                            if "自动" in aspect_ratio or is_inpainting:
                                r_val = img_w / img_h
                                ratios = {"16:9": 16/9, "9:16": 9/16, "1:1": 1.0, "4:3": 4/3, "3:4": 3/4}
                                ar_val = min(ratios, key=lambda k: abs(ratios[k] - r_val))
                            else:
                                ar_val = aspect_ratio.split(" ")[0]
                            
                            # ==========================================
                            # 🌟 V6.0 核心逻辑：全局智能压缩引擎 
                            # ==========================================
                            base_pil_processed = original_base_pil.copy()
                            # 我们先把原图压到 API 接受的上限 2048px (JPEG 85 画质，目标 1MB)
                            api_limit_size = 2048 
                            if base_pil_processed.width > api_limit_size or base_pil_processed.height > api_limit_size:
                                base_pil_processed.thumbnail((api_limit_size, api_limit_size), Image.Resampling.LANCZOS)
                            
                            # 将处理后的原图转 Base64
                            buffered = io.BytesIO()
                            base_pil_processed.save(buffered, format="JPEG", quality=85)
                            base_payload_64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

                            # ==========================================
                            # 🌟 V6.0 核心逻辑：生成蒙版 (Mask)
                            # ==========================================
                            payload = None
                            if is_inpainting:
                                # A. 获取前端涂抹的蒙版数据 (带有 alpha 通道)
                                mask_data_rgba = canvas_result.image_data
                                # B. 转为 PIL 图片并进行处理
                                mask_pil = Image.fromarray(mask_data_rgba.astype('uint8'), 'RGBA')
                                # C. 分离出 Alpha 通道（用户涂抹的部分）
                                alpha_channel = mask_pil.split()[-1]
                                # D. 关键步骤：生成纯黑白蒙版。Alpha > 0 的地方设为 255(白)，否则设为 0(黑)
                                # 这是因为 Gemini 的 inline_data 需要一张 JPEG/PNG 作为蒙版，而不是纯数组
                                threshold = 1
                                binary_mask = alpha_channel.point(lambda p: 255 if p >= threshold else 0)
                                # 强制转为 L (灰度图)，然后转 RGB 防止报错，因为 point 操作有时会产生意外通道
                                binary_mask = binary_mask.convert("RGB")
                                # 如果你的图片比例不规则，这里需要做一个和 v5.8 一样的补白边逻辑来适配 mask
                                final_mask_pil = binary_mask.resize(base_pil_processed.size, Image.Resampling.NEAREST)

                                # E. 将蒙版也转为 Base64
                                mask_buffered = io.BytesIO()
                                final_mask_pil.save(mask_buffered, format="JPEG", quality=85)
                                mask_payload_64 = base64.b64encode(mask_buffered.getvalue()).decode('utf-8')
                                
                                st.toast("🛡️ 1MB全局压缩引擎启动！局部重绘通道已开启，蒙版生成成功！")

                                # ==========================================
                                # 🌟 V6.0 核心逻辑：构建局部重绘 API Payload
                                # ==========================================
                                # 顺序极其重要：1.底图，2.蒙版图，3.提示词。
                                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={API_KEY}"
                                payload = {
                                    "contents": [{"parts": [
                                        {"inline_data": {"mime_type": "image/jpeg", "data": base_payload_64}}, # Part 1: 底图
                                        {"inline_data": {"mime_type": "image/jpeg", "data": mask_payload_64}}, # Part 2: 蒙版
                                        {"text": prompt} # Part 3: 咒语
                                    ]}],
                                    # 重绘下比例锁定
                                    "generationConfig": {"imageConfig": {"aspectRatio": ar_val, "imageSize": q_val}}
                                }
                            else:
                                # 全局模式保持 v5.8 逻辑
                                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={API_KEY}"
                                st.toast("🛡️ 1MB全局压缩引擎启动！全局风格化模式。")
                                payload = {
                                    "contents": [{"parts": [
                                        {"text": prompt},
                                        {"inline_data": {"mime_type": "image/jpeg", "data": base_payload_64}}
                                    ]}],
                                    "generationConfig": {"imageConfig": {"aspectRatio": ar_val, "imageSize": q_val}}
                                }

                            # 2. 发送请求
                            headers = {'Content-Type': 'application/json'}
                            response = requests.post(url, headers=headers, json=payload, timeout=180)

                            if response.status_code == 200:
                                result = response.json()
                                # ==========================================
                                # 🌟 V5.8 安全预警拦截系统
                                # ==========================================
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
                                        
                                    st.success(f"🎉 局部重绘完成 / Success! ({img_width} x {img_height} px)")
                                    # 在画板下方显示成品，方便对比
                                    col1, col2 = st.columns([100, 1]) 
                                    with col1:
                                        st.image(raw_ai_image, caption=f"AI 渲染成品 | {img_width} x {img_height}", use_container_width=True)
                                        with open(img_filename, "rb") as file:
                                            st.download_button(
                                                label="⬇️ 保存当前局部重绘图 / Download Inpainting Image",
                                                data=file,
                                                file_name=f"render_{prefix}_{timestamp}.png",
                                                mime="image/png",
                                                use_container_width=True
                                            )
                                    
                                    st.session_state['last_render'] = {'prompt': prompt, 'output_b64': output_b64, 'ar_val': ar_val, 'quality': q_val}
                                    
                                except KeyError:
                                    # 如果找不到图片数据，解析具体的拦截原因
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

        # 图生图 4K 深化模块 (保持)
        if 'last_render' in st.session_state and st.session_state['last_render']['quality'] in ["512", "1K"]:
            st.divider()
            st.info("💡 满意当前光影？点击下方按钮直升 4K / Upscale to 4K instants.")
            if st.button("💎 4K 极限深化 / Upscale to 4K (Ultra-HD)", type="secondary", use_container_width=True):
                with viewport_placeholder.container():
                    # 4K 深化不适用于重绘，我们这里加个判断以防万一
                    st.warning("⚠️ 4K极限深化适用于全局模式。对局部重绘结果进行整体深化，可能会轻微模糊原保留区域，建议在需要整体高像素出图时使用。")
                    with st.spinner("💳 正在生成 4K 极限细节..."):
                        # ...此处省略旧代码，保持 4K 深化逻辑...
                        pass

# ------------------------------------------
# Tab 2: 历史画廊 (保持)
# ------------------------------------------
with tab_gallery:
    st.subheader("📁 历史资产库 / History Assets")
    if os.path.exists(HISTORY_DIR):
        files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".png")]
        files.sort(reverse=True)
        # ...此此处省略旧代码，保持画廊逻辑...
        pass
