import streamlit as st
import base64
import os
import requests
from PIL import Image
import io
import datetime

# ==========================================
# 0. 页面基础配置
# ==========================================
st.set_page_config(page_title="Architecture AI Render", layout="wide", initial_sidebar_state="collapsed")

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

# os.environ['http_proxy'] = 'http://127.0.0.1:7890'
# os.environ['https_proxy'] = 'http://127.0.0.1:7890'

HISTORY_DIR = "render_history"
os.makedirs(HISTORY_DIR, exist_ok=True)

# ⚠️ 从云端金库中安全读取密钥
API_KEY = st.secrets["GEMINI_API_KEY"]

st.title("🏗️ 建筑效果图 AI 渲染引擎 / Architecture AI Render v5.7")
st.markdown("---")

tab_studio, tab_gallery = st.tabs(["🎨 工作台 / Studio", "🖼️ 历史资产库 / Gallery"])

# ------------------------------------------
# Tab 1: 工作台
# ------------------------------------------
with tab_studio:
    col_ctrl, col_canvas = st.columns([1, 2], gap="large")

    with col_ctrl:
        st.subheader("1. 底图 / Base Image")
        uploaded_file = st.file_uploader("上传白模或线稿 / Upload Sketch", type=['png', 'jpg', 'jpeg'])
        base64_image = ""
        original_base_pil = None 
        
        if uploaded_file is not None:
            st.image(uploaded_file, caption="原始底图 / Original Base", use_container_width=True)
            image_bytes = uploaded_file.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            # 转换为 RGB，防止透明背景的 PNG 引发错误
            original_base_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB") 

        st.subheader("2. 风格与指令 / Style & Prompt")
        style_presets = {
            "🏛️ 法式新古典别墅 / Neoclassical": "High-end residential villa architectural rendering, Neoclassical style. Pure white smooth stucco facade, elegant dark-framed French windows and doors, intricate wrought iron balcony railings. Photorealistic, professional architectural photography, ultra-detailed textures. Strictly preserve the original architectural geometry.",
            "🏙️ 现代与 Art Deco 高层 / Modern Art Deco": "High-rise residential building rendering, seamlessly combining Modern and Art Deco styles. Strong vertical emphasis, elegant geometric ornamentation, stepping silhouettes, sleek glass and metallic brass facade. Photorealistic, 8k resolution, professional architectural photography.",
            "🌿 极简清水混凝土 / Minimalist Zen": "Minimalist architectural rendering, Japanese Zen style. Fair-faced exposed concrete walls with visible formwork holes, pure geometric volumes. Dramatic interplay of light and shadow, integrated with sparse Zen landscaping. Photorealistic, architectural photography.",
            "✍️ 自定义 / Custom Prompt": ""
        }
        selected_style = st.selectbox("选择风格 / Select Style", list(style_presets.keys()), label_visibility="collapsed")
        prompt = style_presets[selected_style]
        if selected_style == "✍️ 自定义 / Custom Prompt":
            prompt = st.text_area("输入英文指令 / Enter Prompt:", value="")

        st.subheader("3. 画幅与精度 / Settings")
        aspect_ratio = st.radio(
            "📐 画幅比例 (Aspect Ratio)", 
            ["✨ 自动 (Auto)", "16:9", "9:16", "1:1", "4:3", "3:4"],
            horizontal=True 
        )
        quality = st.radio(
            "✨ 渲染画质 (Resolution)", 
            ["512 (极速)", "1K (标准)", "2K (超清)", "4K (大片)"],
            horizontal=True
        )

        st.markdown("<br>", unsafe_allow_html=True) 
        render_btn = st.button("🚀 开始渲染抽卡 / Generate", type="primary", use_container_width=True)

    with col_canvas:
        st.subheader("📺 渲染视口 / Viewport")
        viewport_placeholder = st.empty()
        
        if not uploaded_file:
            viewport_placeholder.info("👈 请在左侧配置参数并点击渲染 / Configure settings on the left and click generate.")
        
        if render_btn:
            if not uploaded_file:
                st.warning("⚠️ 请上传底图！/ Upload an image first!")
            elif not prompt:
                st.warning("⚠️ 请输入渲染指令！/ Enter a prompt!")
            else:
                with viewport_placeholder.container():
                    with st.spinner("💳 云端算力渲染中，预计需要 10-30 秒... / Generating..."):
                        try:
                            # 1. 确定最终比例
                            if "自动" in aspect_ratio:
                                img_w, img_h = original_base_pil.size
                                r_val = img_w / img_h
                                ratios = {"16:9": 16/9, "9:16": 9/16, "1:1": 1.0, "4:3": 4/3, "3:4": 3/4}
                                ar_val = min(ratios, key=lambda k: abs(ratios[k] - r_val))
                                st.toast(f"📐 已智能匹配最佳画幅: {ar_val}")
                            else:
                                ar_val = aspect_ratio.split(" ")[0]
                                
                            q_val = quality.split(" ")[0]
                            
                            # ==========================================
                            # 🌟 核心修复引擎：防裁切智能白边填充 (Letterboxing)
                            # ==========================================
                            target_w_ratio, target_h_ratio = map(int, ar_val.split(':'))
                            target_ratio_float = target_w_ratio / target_h_ratio
                            orig_w, orig_h = original_base_pil.size
                            orig_ratio_float = orig_w / orig_h

                            # 容差范围内的微小差异直接忽略，否则开始智能补边
                            if abs(target_ratio_float - orig_ratio_float) > 0.01:
                                if target_ratio_float > orig_ratio_float: 
                                    # 目标更宽，需要左右加白边
                                    new_w = int(orig_h * target_ratio_float)
                                    new_h = orig_h
                                else: 
                                    # 目标更窄，需要上下加白边
                                    new_w = orig_w
                                    new_h = int(orig_w / target_ratio_float)
                                
                                # 创建纯白色的“画布底板”
                                padded_base_pil = Image.new("RGB", (new_w, new_h), (255, 255, 255))
                                # 把原图贴在正中间
                                paste_x = (new_w - orig_w) // 2
                                paste_y = (new_h - orig_h) // 2
                                padded_base_pil.paste(original_base_pil, (paste_x, paste_y))
                                
                            # ==========================================
                            # 🌟 核心修复引擎：防裁切 + 全局智能压缩
                            # ==========================================
                            target_w_ratio, target_h_ratio = map(int, ar_val.split(':'))
                            target_ratio_float = target_w_ratio / target_h_ratio
                            orig_w, orig_h = original_base_pil.size
                            orig_ratio_float = orig_w / orig_h

                            # 先把原图赋给一个终极变量
                            final_pil = original_base_pil

                            # 1. 智能白边填充 (Letterboxing)
                            if abs(target_ratio_float - orig_ratio_float) > 0.01:
                                if target_ratio_float > orig_ratio_float: 
                                    new_w = int(orig_h * target_ratio_float)
                                    new_h = orig_h
                                else: 
                                    new_w = orig_w
                                    new_h = int(orig_w / target_ratio_float)
                                
                                final_pil = Image.new("RGB", (new_w, new_h), (255, 255, 255))
                                paste_x = (new_w - orig_w) // 2
                                paste_y = (new_h - orig_h) // 2
                                final_pil.paste(original_base_pil, (paste_x, paste_y))
                                st.toast("🛡️ 已自动填充画幅白边！")
                            
                            # 2. 全局 1MB 级智能压缩 (无论是否补白边，统统压缩！)
                            max_size = 1920
                            if final_pil.width > max_size or final_pil.height > max_size:
                                final_pil.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                            
                            buffered = io.BytesIO()
                            final_pil.save(buffered, format="JPEG", quality=85)
                            payload_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                            
                            # 2. 发送精准调校过的数据包
                            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={API_KEY}"
                            headers = {'Content-Type': 'application/json'}
                            payload = {
                                "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": payload_base64}}]}],
                                "generationConfig": {"imageConfig": {"aspectRatio": ar_val, "imageSize": q_val}}
                            }

                            response = requests.post(url, headers=headers, json=payload, timeout=180)

                            if response.status_code == 200:
                                result = response.json()
                                output_b64 = result['candidates'][0]['content']['parts'][0]['inlineData']['data']
                                image_data = base64.b64decode(output_b64)
                                
                                raw_ai_image = Image.open(io.BytesIO(image_data))
                                img_width, img_height = raw_ai_image.size
                                
                                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                                img_filename = os.path.join(HISTORY_DIR, f"render_{timestamp}.png")
                                txt_filename = os.path.join(HISTORY_DIR, f"render_{timestamp}.txt")
                                
                                raw_ai_image.save(img_filename)
                                with open(txt_filename, "w", encoding="utf-8") as f:
                                    f.write(f"【Settings】AR: {ar_val} | Res: {q_val} | Size: {img_width}x{img_height}\n【Prompt】{prompt}\n")
                                    
                                st.success(f"🎉 渲染完成 / Success! ({img_width} x {img_height} px)")
                                st.image(raw_ai_image, caption=f"AI 渲染成品 | {img_width} x {img_height}", use_container_width=True)
                                
                                with open(img_filename, "rb") as file:
                                    st.download_button(
                                        label="⬇️ 保存当前渲染图 / Download Image",
                                        data=file,
                                        file_name=f"render_{timestamp}.png",
                                        mime="image/png",
                                        use_container_width=True
                                    )
                                
                                st.session_state['last_render'] = {'prompt': prompt, 'output_b64': output_b64, 'ar_val': ar_val, 'quality': q_val}
                                
                            else:
                                st.error(f"❌ 失败 / Failed! Status: {response.status_code}")
                        except Exception as e:
                            st.error(f"🌐 错误 / Error: {e}")

        if 'last_render' in st.session_state and st.session_state['last_render']['quality'] in ["512", "1K"]:
            st.divider()
            st.info("💡 满意当前光影？点击下方按钮直升 4K / Satisfied with lighting? Upscale to 4K instants.")
            if st.button("💎 4K 极限深化 / Upscale to 4K (Ultra-HD)", type="secondary", use_container_width=True):
                with viewport_placeholder.container():
                    with st.spinner("💳 正在生成 4K 极限细节，预计需要 1-2 分钟... / Generating 4K details..."):
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
                            else:
                                st.error("❌ 失败 / Failed!")
                        except Exception as e:
                            st.error(f"🌐 错误 / Error: {e}")

# ------------------------------------------
# Tab 2: 历史画廊 (向下兼容代码不变)
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
                                            new_img_data = base64.b64decode(response.json()['candidates'][0]['content']['parts'][0]['inlineData']['data'])
                                            new_image = Image.open(io.BytesIO(new_img_data))
                                            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                                            new_image.save(os.path.join(HISTORY_DIR, f"render_4K_up_{ts}.png"))
                                            with open(os.path.join(HISTORY_DIR, f"render_4K_up_{ts}.txt"), "w", encoding="utf-8") as f:
                                                f.write(f"【Settings】AR: {saved_ar} | Res: 4K | Size: {new_image.size[0]}x{new_image.size[1]}\n【Prompt】{saved_prompt}\n")
                                            st.success("✅ 完成 / Done! 刷新查看 / Refresh to see.")
                                    except Exception as e:
                                        st.error("❌ Failed")

                    with btn_col3:
                        if st.button("🗑️ Del", key=f"del_{file_name}", use_container_width=True):
                            os.remove(img_path)
                            if os.path.exists(txt_path):
                                os.remove(txt_path)
                            st.rerun() 

                    with st.expander(f"📝 查看咒语指令 (Prompt)"):

                        st.code(f"{saved_prompt}")

