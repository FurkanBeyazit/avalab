from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
import websockets
import database

app = FastAPI(title="Avalab Camera API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ── WebSocket helper ─────────────────────────────────────────────────────────
async def _ws_call(stor_ip: str, payload: dict, expect_type: str, timeout: float = 8.0):
    """
    AVA STOR WebSocket에 payload를 Binary 프레임으로 전송하고
    expect_type과 일치하는 응답을 timeout 초 안에 기다립니다.
    응답이 없으면 None을 반환합니다.
    """
    host = stor_ip or database.AVA_STOR_HOST
    if not host:
        raise HTTPException(status_code=400, detail="STOR IP가 설정되지 않았습니다.")
    uri = f"ws://{host}:{database.AVA_STOR_PORT}/linkproto"
    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps(payload).encode("utf-8"))
            loop = asyncio.get_running_loop()
            deadline = loop.time() + timeout
            while True:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    return None
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                    msg = json.loads(raw)
                    if msg.get("type") == expect_type:
                        return msg
                except asyncio.TimeoutError:
                    return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AVA STOR 연결 오류: {e}")


# ── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    database.init_bridge_db()


# ── 카메라 등록 ──────────────────────────────────────────────────────────────
class CameraIn(BaseModel):
    name: str
    node_id: str
    channel: int
    stor_ip: str = ""
    ip: str = ""
    port: int = 8080
    admin_id: str = ""
    admin_password: str = ""
    rtsp_main_url: str = ""
    lat: str = ""
    lng: str = ""


@app.post("/cameras", status_code=201)
async def add_camera(data: CameraIn):
    """
    1. AVA STOR WebSocket으로 LINK_CMD_ADD_CAM_REQ 전송
    2. LINK_CMD_CAM_ADD_NOTIFY 응답에서 strId(ava_cam_id) 획득
    3. camera_bridge에 ava_cam_id + node_id + channel + 카메라 정보 저장
    """
    payload = {
        "type": "LINK_CMD_ADD_CAM_REQ",
        "addCamReq": {
            "cCam": {
                "strName":    data.name,
                "nType":      "NORMAL_TYPE",
                "strIP":      data.ip,
                "strPort":    str(data.port),
                "strUser":    data.admin_id,
                "strPasswd":  data.admin_password,
                "strRTSPUrl": data.rtsp_main_url,
                "strLat":     data.lat,
                "strLng":     data.lng,
            }
        },
    }

    resp = await _ws_call(data.stor_ip, payload, "LINK_CMD_CAM_ADD_NOTIFY")
    if resp is None:
        raise HTTPException(
            status_code=504,
            detail="AVA 타임아웃: 8초 내에 LINK_CMD_CAM_ADD_NOTIFY 응답 없음 (등록 실패)"
        )

    ava_cam_id = resp["camAddNotify"]["cCam"]["strId"]

    br_conn = database.get_bridge_conn()
    try:
        with br_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO camera_bridge
                    (ava_cam_id, node_id, channel, name, stor_ip, ip, port, rtsp_main_url, lat, lng)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                ava_cam_id, data.node_id, data.channel, data.name,
                data.stor_ip, data.ip, str(data.port), data.rtsp_main_url,
                data.lat, data.lng,
            ))
        br_conn.commit()
    finally:
        br_conn.close()

    return {"ok": True, "ava_cam_id": ava_cam_id}


# ── VMS lookup: AVA camera ID → node_id + channel ───────────────────────────
@app.get("/node/{ava_cam_id}")
def get_node(ava_cam_id: int):
    """VMS가 AVA 카메라 ID로 node_id와 channel을 조회합니다."""
    br_conn = database.get_bridge_conn()
    try:
        with br_conn.cursor() as cur:
            cur.execute(
                "SELECT node_id, channel, name FROM camera_bridge WHERE ava_cam_id = %s",
                (str(ava_cam_id),)
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"ava_cam_id={ava_cam_id} 미등록")
        return {"node_id": row["node_id"], "channel": row["channel"], "name": row["name"]}
    finally:
        br_conn.close()


# ── 카메라 목록 (UI용) ────────────────────────────────────────────────────────
@app.get("/cameras")
def list_cameras():
    """UI 표시용 — bridge 테이블에서 직접 조회합니다."""
    br_conn = database.get_bridge_conn()
    try:
        with br_conn.cursor() as cur:
            cur.execute("SELECT * FROM camera_bridge ORDER BY id")
            rows = cur.fetchall()
        return [
            {
                "id":           r["id"],
                "ava_cam_id":   r["ava_cam_id"],
                "node_id":      r["node_id"],
                "channel":      r["channel"],
                "name":         r["name"],
                "STOR_IP":      r.get("stor_ip", ""),
                "IP":           r.get("ip", ""),
                "PORT":         r.get("port", ""),
                "RTSP_MAIN_URL": r.get("rtsp_main_url", ""),
                "LAT":          r.get("lat", ""),
                "LNG":          r.get("lng", ""),
            }
            for r in rows
        ]
    finally:
        br_conn.close()


# ── 카메라 삭제 ───────────────────────────────────────────────────────────────
@app.delete("/cameras/{bridge_id}")
async def delete_camera(bridge_id: int):
    """
    1. AVA STOR WebSocket으로 LINK_CMD_DEL_CAM_REQ 전송
    2. LINK_CMD_CAM_DEL_NOTIFY 응답 확인
    3. camera_bridge에서 해당 레코드 삭제
    """
    br_conn = database.get_bridge_conn()
    try:
        with br_conn.cursor() as cur:
            cur.execute(
                "SELECT ava_cam_id, stor_ip FROM camera_bridge WHERE id = %s", (bridge_id,)
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="미등록 카메라")
        ava_cam_id = row["ava_cam_id"]
        stor_ip    = row["stor_ip"]
    finally:
        br_conn.close()

    payload = {
        "type": "LINK_CMD_DEL_CAM_REQ",
        "delCamReq": {"strId": ava_cam_id},
    }
    resp = await _ws_call(stor_ip, payload, "LINK_CMD_CAM_DEL_NOTIFY")
    if resp is None:
        raise HTTPException(
            status_code=504,
            detail="AVA 타임아웃: 8초 내에 LINK_CMD_CAM_DEL_NOTIFY 응답 없음 (삭제 실패)"
        )

    br_conn = database.get_bridge_conn()
    try:
        with br_conn.cursor() as cur:
            cur.execute("DELETE FROM camera_bridge WHERE id = %s", (bridge_id,))
        br_conn.commit()
    finally:
        br_conn.close()

    return {"ok": True}


# ── Event area ───────────────────────────────────────────────────────────────
_EVENT_NAMES = {
    1: "침입(INTRUSION1)", 2: "배회1(LOITER1)",     4: "군집(CROWD)",
    5: "주정차(PARKING)",  8: "침입2(INTRUSION2)",  9: "침입3(INTRUSION3)",
    10: "배회2(LOITER2)", 11: "배회3(LOITER3)",    12: "흡연(SMOKING)",
    15: "화재(FIRE)",     16: "쓰레기투기(GARBAGE)", 17: "쓰러짐(FALL)",
    18: "싸움(FIGHT)",    19: "연기(FIRE_SMOKE)",
}


class EventAreaIn(BaseModel):
    camera_id: str
    event_type: int
    geometry: str = ""
    activation_time: str = "00:00-24:00"


@app.post("/event-area", status_code=201)
async def set_event_area(data: EventAreaIn):
    """
    이벤트 영역을 bridge DB에 저장하고
    AVA STOR WebSocket으로 LINK_CMD_SET_EVENT_AREA_NOTIFY를 전송합니다.
    geometry가 빈 문자열이면 AVA에서 해당 영역이 삭제됩니다.
    """
    # 해당 카메라의 stor_ip 조회
    br_conn = database.get_bridge_conn()
    try:
        with br_conn.cursor() as cur:
            cur.execute(
                "SELECT stor_ip FROM camera_bridge WHERE ava_cam_id = %s", (data.camera_id,)
            )
            row = cur.fetchone()
        stor_ip = row["stor_ip"] if row else ""
    finally:
        br_conn.close()

    payload = {
        "type": "LINK_CMD_SET_EVENT_AREA_NOTIFY",
        "setEventAreaNotify": {
            "cEventArea": {
                "nCameraId":         int(data.camera_id),
                "nEventType":        data.event_type,
                "strGeometry":       data.geometry,
                "strActivationTime": data.activation_time,
            }
        },
    }
    resp = await _ws_call(stor_ip, payload, "LINK_CMD_SET_EVENT_AREA_NOTIFY")
    if resp is None:
        raise HTTPException(
            status_code=504,
            detail="AVA 타임아웃: 8초 내에 이벤트 영역 설정 응답 없음"
        )

    br_conn = database.get_bridge_conn()
    try:
        with br_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO event_area (camera_id, event_type, geometry, activation_time)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE geometry=%s, activation_time=%s
            """, (data.camera_id, data.event_type, data.geometry, data.activation_time,
                  data.geometry, data.activation_time))
        br_conn.commit()
    finally:
        br_conn.close()

    return {"ok": True}


@app.get("/event-area/{camera_id}")
def get_event_area(camera_id: str):
    """AVA LINK_CMD 포맷으로 저장된 이벤트 영역 목록을 반환합니다."""
    br_conn = database.get_bridge_conn()
    try:
        with br_conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM event_area WHERE camera_id = %s ORDER BY event_type",
                (camera_id,)
            )
            rows = cur.fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail=f"camera_id={camera_id} 이벤트 영역 없음")
        return [
            {
                "type": "LINK_CMD_SET_EVENT_AREA_NOTIFY",
                "setEventAreaNotify": {
                    "cEventArea": {
                        "nCameraId":         int(r["camera_id"]),
                        "nEventType":        r["event_type"],
                        "strGeometry":       r["geometry"],
                        "strActivationTime": r["activation_time"],
                    }
                },
            }
            for r in rows
        ]
    finally:
        br_conn.close()


@app.get("/event-areas")
def list_event_areas():
    """UI용 전체 이벤트 영역 목록"""
    br_conn = database.get_bridge_conn()
    try:
        with br_conn.cursor() as cur:
            cur.execute("SELECT * FROM event_area ORDER BY camera_id, event_type")
            return cur.fetchall()
    finally:
        br_conn.close()


@app.delete("/event-area/{area_id}")
def delete_event_area(area_id: int):
    br_conn = database.get_bridge_conn()
    try:
        with br_conn.cursor() as cur:
            cur.execute("SELECT id FROM event_area WHERE id = %s", (area_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="not found")
            cur.execute("DELETE FROM event_area WHERE id = %s", (area_id,))
        br_conn.commit()
        return {"ok": True}
    finally:
        br_conn.close()


if __name__ == "__main__":
    import uvicorn
    print("\n  API  →  http://localhost:8091")
    print("  Docs →  http://localhost:8091/docs\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8091, reload=True)
