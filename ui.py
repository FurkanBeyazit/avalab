import gradio as gr
import requests

API = "http://localhost:8091"

_custom_css = """
footer { display: none !important; }
#cam-table th, #cam-table td { padding: 6px 12px; text-align: left; font-size: 13px; }
#cam-table th { background: #1a4fa3; color: #fff; }
#cam-table tr:nth-child(even) { background: #f4f7fc; }
"""


def _post_camera(name, node_id, channel, ip, port, admin_id, admin_password,
                 rtsp_main_url, lat, lng):
    if not name or not node_id or not channel:
        return "<p style='color:red'>Camera Name, Node ID, Channel 필수입니다.</p>", _load_table()
    try:
        channel = int(channel)
        port    = int(port) if port else 8080
    except ValueError:
        return "<p style='color:red'>Channel / Port 숫자여야 합니다.</p>", _load_table()
    try:
        r = requests.post(f"{API}/cameras", json={
            "name":    name,
            "node_id":        node_id,
            "channel":        channel,
            "ip":             ip,
            "port":           port,
            "admin_id":       admin_id,
            "admin_password": admin_password,
            "rtsp_main_url":  rtsp_main_url,
            "lat":            lat,
            "lng":            lng,
        }, timeout=5)
        r.raise_for_status()
        ava_id = r.json().get("ava_cam_id", "?")
        return f"<p style='color:green'>✓ 저장 완료 (AVA cam_id: {ava_id})</p>", _load_table()
    except Exception as e:
        return f"<p style='color:red'>오류: {e}</p>", _load_table()


def _load_table():
    try:
        rows = requests.get(f"{API}/cameras", timeout=5).json()
    except Exception:
        return "<p style='color:red'>API 연결 실패 — main.py 실행 여부를 확인하세요.</p>"
    if not rows:
        return "<p style='opacity:0.5'>등록된 카메라가 없습니다.</p>"
    headers = ["ID", "AVA ID", "Node ID", "Channel", "Camera Name", "IP", "PORT", "RTSP", "LAT", "LNG"]
    head = "<thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead>"
    body = "".join(
        f"<tr>"
        f"<td>{r.get('id','')}</td>"
        f"<td>{r.get('ava_cam_id','')}</td>"
        f"<td>{r.get('node_id','')}</td>"
        f"<td>{r.get('channel','')}</td>"
        f"<td>{r.get('name','')}</td>"
        f"<td>{r.get('IP','')}</td>"
        f"<td>{r.get('PORT','')}</td>"
        f"<td>{r.get('RTSP_MAIN_URL','')}</td>"
        f"<td>{r.get('LAT','')}</td>"
        f"<td>{r.get('LNG','')}</td>"
        f"</tr>"
        for r in rows
    )
    return f"<table id='cam-table' style='border-collapse:collapse;width:100%'>{head}<tbody>{body}</tbody></table>"


with gr.Blocks(title="Ainos AvaLab Connection Bridge", theme=gr.themes.Soft(), css=_custom_css) as app:

    with gr.Tabs() as tabs:

        # ── Home ─────────────────────────────────────────────────────────────
        with gr.Tab("🏠 Home", id=0):
            gr.HTML(
                "<div style='text-align:center;padding:48px 0 24px'>"
                "<div style='display:inline-block;"
                "background:#1a4fa3;color:#ffffff;"
                "font-size:1.6rem;font-weight:700;letter-spacing:0.18em;"
                "padding:6px 22px;border-radius:6px;margin-bottom:14px'>"
                "DANUSYS</div>"
                "<h1 style='font-size:2rem;margin-bottom:6px'>Ainos AvaLab Connection Bridge</h1>"
                "</div>"
            )
            gr.HTML("""
                <style>
                  .home-card {
                    width:180px;height:180px;border-radius:14px;
                    display:flex;flex-direction:column;
                    align-items:center;justify-content:center;
                    gap:8px;cursor:pointer;user-select:none;transition:filter 0.2s;
                  }
                  .home-card:hover { filter: brightness(1.12); }
                </style>
                <div style="display:flex;justify-content:center;gap:24px;padding:24px 0 40px">

                  <div class="home-card"
                       style="border:2px solid rgba(99,190,123,0.6);background:rgba(99,190,123,0.08)"
                       onclick="(function(){ var d=document; try{if(window.parent&&window.parent!==window)d=window.parent.document;}catch(e){} var tabs=d.querySelectorAll('button[role=tab]'); for(var i=0;i<tabs.length;i++){if(tabs[i].textContent.includes('카메라')){tabs[i].click();return;}} })()">
                    <span style="font-size:2.4rem">📷</span>
                    <span style="font-size:1rem;font-weight:600">카메라 등록</span>
                    <span style="font-size:0.75rem;opacity:0.6">Camera Registration</span>
                  </div>

                  <div class="home-card"
                       style="border:2px solid rgba(100,149,237,0.6);background:rgba(100,149,237,0.08)"
                       onclick="(function(){ var d=document; try{if(window.parent&&window.parent!==window)d=window.parent.document;}catch(e){} var tabs=d.querySelectorAll('button[role=tab]'); for(var i=0;i<tabs.length;i++){if(tabs[i].textContent.includes('가디언')){tabs[i].click();return;}} })()">
                    <span style="font-size:2.4rem">👁</span>
                    <span style="font-size:1rem;font-weight:600">가디언아이 설정</span>
                    <span style="font-size:0.75rem;opacity:0.6">Guardian Eye</span>
                  </div>

                  <div class="home-card"
                       style="border:2px solid rgba(147,112,219,0.6);background:rgba(147,112,219,0.08)"
                       onclick="(function(){ var d=document; try{if(window.parent&&window.parent!==window)d=window.parent.document;}catch(e){} var tabs=d.querySelectorAll('button[role=tab]'); for(var i=0;i<tabs.length;i++){if(tabs[i].textContent.includes('Ainos')){tabs[i].click();return;}} })()">
                    <span style="font-size:2.4rem">⚙️</span>
                    <span style="font-size:1rem;font-weight:600">Ainos 설정</span>
                    <span style="font-size:0.75rem;opacity:0.6">Ainos Settings</span>
                  </div>

                </div>
            """)

        # ── 카메라 등록 ───────────────────────────────────────────────────────
        with gr.Tab("📷 카메라 등록", id=1):
            gr.Markdown("## 카메라 등록 / Camera Registration")

            with gr.Column():
                inp_name     = gr.Textbox(label="Camera Name",        placeholder="예: 정문 카메라")
                inp_node     = gr.Textbox(label="Node ID",            placeholder="예: 30632")
                inp_channel  = gr.Textbox(label="Channel",            placeholder="예: 1")
                inp_ip       = gr.Textbox(label="IP",                 placeholder="예: 192.168.0.100")
                inp_port     = gr.Textbox(label="PORT",               placeholder="예: 8080", value="8080")
                inp_admin_id = gr.Textbox(label="Admin ID",           placeholder="예: admin")
                inp_admin_pw = gr.Textbox(label="Admin Password",     placeholder="예: admin1234")
                inp_rtsp     = gr.Textbox(label="RTSP Main URL",      placeholder="rtsp://...")
                inp_lat      = gr.Textbox(label="Latitude (위도)",    placeholder="예: 37.123456")
                inp_lng      = gr.Textbox(label="Longitude (경도)",   placeholder="예: 127.123456")

            with gr.Row():
                btn_save    = gr.Button("💾 저장", variant="primary", scale=1)
                btn_refresh = gr.Button("🔄 목록 새로고침", scale=1)

            save_status = gr.HTML("")

            gr.Markdown("---")
            gr.Markdown("### 등록된 카메라 목록")
            cam_table = gr.HTML("<p style='opacity:0.5'>불러오는 중...</p>")

            btn_save.click(
                _post_camera,
                inputs=[inp_name, inp_node, inp_channel, inp_ip, inp_port,
                        inp_admin_id, inp_admin_pw, inp_rtsp, inp_lat, inp_lng],
                outputs=[save_status, cam_table],
            )
            btn_refresh.click(_load_table, outputs=[cam_table])

        # ── 가디언아이 설정 ────────────────────────────────────────────────────
        with gr.Tab("👁 가디언아이 설정", id=2):
            gr.Markdown("## 가디언아이 설정 / Guardian Eye Settings")
            gr.HTML("<p style='opacity:0.5;padding:40px 0'>준비 중입니다.</p>")

        # ── Ainos 설정 ─────────────────────────────────────────────────────────
        with gr.Tab("⚙️ Ainos 설정", id=3):
            gr.Markdown("## Ainos 설정 / Ainos Settings")
            gr.HTML("<p style='opacity:0.5;padding:40px 0'>준비 중입니다.</p>")

    gr.HTML(
        "<div style='text-align:center;padding:16px 0 8px;"
        "color:#1a4fa3;font-size:0.78rem;margin-top:24px'>"
        "© 2026 DANUSYS. All rights reserved."
        "</div>"
    )

    app.load(_load_table, outputs=[cam_table])


if __name__ == "__main__":
    print("\n  UI  →  http://localhost:7861\n")
    app.launch(server_name="0.0.0.0", server_port=7861)
