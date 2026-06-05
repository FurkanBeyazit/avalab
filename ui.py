import gradio as gr
import requests

API = "http://localhost:8091"

_custom_css = """
footer { display: none !important; }
#cam-table {
    border-collapse: collapse;
    width: 100%;
}
#cam-table th, #cam-table td {
    padding: 6px 12px;
    text-align: left;
    font-size: 13px;
    color: inherit;
}
#cam-table th {
    background: #1a4fa3;
    color: #fff !important;
}
#cam-table tr:nth-child(odd)  { background: rgba(0,0,0,0.03); }
#cam-table tr:nth-child(even) { background: rgba(0,0,0,0.08); }
#cam-table tr:hover           { background: rgba(26,79,163,0.15); }
"""


def _post_camera(name, node_id, channel, stor_ip, ip, port, admin_id, admin_password,
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
            "name":           name,
            "node_id":        node_id,
            "channel":        channel,
            "stor_ip":        stor_ip,
            "ip":             ip,
            "port":           port,
            "admin_id":       admin_id,
            "admin_password": admin_password,
            "rtsp_main_url":  rtsp_main_url,
            "lat":            lat,
            "lng":            lng,
        }, timeout=15)
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
    headers = ["ID", "AVA ID", "Node ID", "Channel", "STOR_IP", "Camera Name", "IP", "PORT", "RTSP", "LAT", "LNG", ""]
    head = "<thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead>"

    def _del_onclick(bid):
        return (
            f"fetch('http://'+location.hostname+':8091/cameras/{bid}',{{method:'DELETE'}})"
            f".then(function(r){{return r.json();}})"
            f".then(function(){{"
            f"var b=document.querySelector('#cam-refresh-btn button');"
            f"if(!b){{var a=document.querySelectorAll('button');"
            f"for(var i=0;i<a.length;i++){{if(a[i].textContent.indexOf('새로고침')>=0){{b=a[i];break;}}}}}}"
            f"if(!b){{try{{b=window.parent.document.querySelector('#cam-refresh-btn button');}}catch(e){{}}}}"
            f"if(b){{b.click();}}else{{location.reload();}}"
            f"}})"
        )

    body = "".join(
        "<tr>"
        f"<td>{r.get('id','')}</td>"
        f"<td>{r.get('ava_cam_id','')}</td>"
        f"<td>{r.get('node_id','')}</td>"
        f"<td>{r.get('channel','')}</td>"
        f"<td>{r.get('STOR_IP','')}</td>"
        f"<td>{r.get('name','')}</td>"
        f"<td>{r.get('IP','')}</td>"
        f"<td>{r.get('PORT','')}</td>"
        f"<td>{r.get('RTSP_MAIN_URL','')}</td>"
        f"<td>{r.get('LAT','')}</td>"
        f"<td>{r.get('LNG','')}</td>"
        f"<td><button onclick=\"{_del_onclick(r.get('id',''))}\" "
        f"style='background:#c0392b;color:#fff;border:none;padding:3px 10px;"
        f"border-radius:4px;cursor:pointer;font-size:12px'>🗑️ 삭제</button></td>"
        "</tr>"
        for r in rows
    )
    return f"<table id='cam-table' style='border-collapse:collapse;width:100%'>{head}<tbody>{body}</tbody></table>"


_EVENT_TYPE_OPTIONS = [
    "1 - 침입(INTRUSION1)",   "2 - 배회1(LOITER1)",       "4 - 군집(CROWD)",
    "5 - 주정차(PARKING)",    "8 - 침입2(INTRUSION2)",    "9 - 침입3(INTRUSION3)",
    "10 - 배회2(LOITER2)",    "11 - 배회3(LOITER3)",      "12 - 흡연(SMOKING)",
    "15 - 화재(FIRE)",        "16 - 쓰레기투기(GARBAGE)", "17 - 쓰러짐(FALL)",
    "18 - 싸움(FIGHT)",       "19 - 연기(FIRE_SMOKE)",
]

_EVENT_NAMES = {
    1:"침입(INTRUSION1)", 2:"배회1(LOITER1)",  4:"군집(CROWD)",
    5:"주정차(PARKING)",  8:"침입2(INTRUSION2)", 9:"침입3(INTRUSION3)",
    10:"배회2(LOITER2)", 11:"배회3(LOITER3)",  12:"흡연(SMOKING)",
    15:"화재(FIRE)",     16:"쓰레기투기(GARBAGE)", 17:"쓰러짐(FALL)",
    18:"싸움(FIGHT)",    19:"연기(FIRE_SMOKE)",
}


def _get_camera_choices():
    try:
        rows = requests.get(f"{API}/cameras", timeout=5).json()
        return [f"{r['ava_cam_id']} - {r['name']}" for r in rows]
    except Exception:
        return []


def _post_event_area(camera_choice, event_type_choice, geometry, activation_time):
    if not camera_choice or not event_type_choice:
        return "<p style='color:red'>Camera와 Event Type을 선택하세요.</p>", _load_event_table()
    try:
        camera_id  = int(camera_choice.split(" - ")[0])
        event_type = int(event_type_choice.split(" - ")[0])
    except (ValueError, IndexError):
        return "<p style='color:red'>선택값 파싱 오류</p>", _load_event_table()
    try:
        r = requests.post(f"{API}/event-area", json={
            "camera_id":       camera_id,
            "event_type":      event_type,
            "geometry":        geometry or "",
            "activation_time": activation_time or "00:00-24:00",
        }, timeout=15)
        r.raise_for_status()
        return "<p style='color:green'>✓ 저장 완료</p>", _load_event_table()
    except Exception as e:
        return f"<p style='color:red'>오류: {e}</p>", _load_event_table()


def _load_event_table():
    try:
        rows = requests.get(f"{API}/event-areas", timeout=5).json()
    except Exception:
        return "<p style='color:red'>API 연결 실패</p>"
    if not rows:
        return "<p style='opacity:0.5'>등록된 이벤트 영역이 없습니다.</p>"
    headers = ["ID", "Camera ID", "Event Type", "Geometry", "Activation Time"]
    head = "<thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead>"
    body = "".join(
        f"<tr>"
        f"<td>{r.get('id','')}</td>"
        f"<td>{r.get('camera_id','')}</td>"
        f"<td>{r.get('event_type','')} - {_EVENT_NAMES.get(r.get('event_type',0),'')}</td>"
        f"<td style='max-width:280px;word-break:break-all'>{r.get('geometry','')}</td>"
        f"<td>{r.get('activation_time','')}</td>"
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

                  <!-- 이벤트 설정 카드 (준비 중, 숨김) -->

                </div>
            """)

        # ── 카메라 등록 ───────────────────────────────────────────────────────
        with gr.Tab("📷 카메라 등록", id=1):
            gr.Markdown("## 카메라 등록 / Camera Registration")

            with gr.Column():
                inp_name     = gr.Textbox(label="Camera Name",        placeholder="예: 정문 카메라")
                inp_node     = gr.Textbox(label="Node ID",            placeholder="예: 30632")
                inp_channel  = gr.Textbox(label="Channel",            placeholder="예: 1")
                inp_stor_ip  = gr.Textbox(label="STOR IP",            placeholder="예: 172.20.14.161")
                inp_ip       = gr.Textbox(label="IP",                 placeholder="예: 192.168.0.100")
                inp_port     = gr.Textbox(label="PORT",               placeholder="예: 8080", value="8080")
                inp_admin_id = gr.Textbox(label="Admin ID",           placeholder="예: admin")
                inp_admin_pw = gr.Textbox(label="Admin Password",     placeholder="예: admin1234")
                inp_rtsp     = gr.Textbox(label="RTSP Main URL",      placeholder="rtsp://...")
                inp_lat      = gr.Textbox(label="Latitude (위도)",    placeholder="예: 37.123456")
                inp_lng      = gr.Textbox(label="Longitude (경도)",   placeholder="예: 127.123456")

            with gr.Row():
                btn_save    = gr.Button("💾 저장", variant="primary", scale=1)
                btn_refresh = gr.Button("🔄 목록 새로고침", scale=1, elem_id="cam-refresh-btn")

            save_status = gr.HTML("")

            gr.Markdown("---")
            gr.Markdown("### 등록된 카메라 목록")
            cam_table = gr.HTML("<p style='opacity:0.5'>불러오는 중...</p>")

            btn_save.click(
                _post_camera,
                inputs=[inp_name, inp_node, inp_channel, inp_stor_ip, inp_ip, inp_port,
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

        # ── 이벤트 설정 ────────────────────────────────────────────────────────
        with gr.Tab("📡 이벤트 설정", id=4, visible=False):
            gr.Markdown("## 이벤트 영역 설정 / Event Area Settings")

            with gr.Row():
                evt_camera = gr.Dropdown(label="Camera (AVA ID - Name)", choices=[], interactive=True, scale=4)
                btn_cam_reload = gr.Button("🔄", scale=0, min_width=60)

            evt_type = gr.Dropdown(label="Event Type", choices=_EVENT_TYPE_OPTIONS, interactive=True)
            evt_geometry = gr.Textbox(
                label="Geometry (strGeometry)",
                placeholder="(x1 y1,x2 y2,x3 y3,x4 y4)  ·  빈 값이면 해당 영역 삭제",
                lines=3,
            )
            evt_time = gr.Textbox(label="Activation Time", value="00:00-24:00", placeholder="00:00-24:00")

            with gr.Row():
                btn_evt_save    = gr.Button("💾 저장", variant="primary", scale=1)
                btn_evt_refresh = gr.Button("🔄 목록 새로고침", scale=1)

            evt_status = gr.HTML("")

            gr.Markdown("---")
            gr.Markdown("### 등록된 이벤트 영역 목록")
            evt_table = gr.HTML("<p style='opacity:0.5'>불러오는 중...</p>")

            btn_cam_reload.click(
                lambda: gr.update(choices=_get_camera_choices()),
                outputs=[evt_camera],
            )
            btn_evt_save.click(
                _post_event_area,
                inputs=[evt_camera, evt_type, evt_geometry, evt_time],
                outputs=[evt_status, evt_table],
            )
            btn_evt_refresh.click(_load_event_table, outputs=[evt_table])

    gr.HTML(
        "<div style='text-align:center;padding:16px 0 8px;"
        "color:#1a4fa3;font-size:0.78rem;margin-top:24px'>"
        "© 2026 DANUSYS. All rights reserved."
        "</div>"
    )

    def _on_load():
        return _load_table(), gr.update(choices=_get_camera_choices()), _load_event_table()

    app.load(_on_load, outputs=[cam_table, evt_camera, evt_table])


if __name__ == "__main__":
    import asyncio, sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("\n  UI  →  http://localhost:7861\n")
    app.launch(server_name="0.0.0.0", server_port=7861)
