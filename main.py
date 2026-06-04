from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import database

app = FastAPI(title="Avalab Camera API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


class CameraIn(BaseModel):
    name: str
    node_id: str
    channel: int
    ip: str = ""
    port: int = 8080
    admin_id: str = ""
    admin_password: str = ""
    rtsp_main_url: str = ""
    lat: str = ""
    lng: str = ""


@app.on_event("startup")
def startup():
    database.init_bridge_db()


# ── 카메라 등록 ──────────────────────────────────────────────────────────────
@app.post("/cameras", status_code=201)
def add_camera(data: CameraIn):
    """
    1. aibis.camera 에 INSERT → AVA가 ID 자동 부여
    2. avalab.camera_bridge 에 ava_cam_id + node_id + channel 저장
    """
    ava_conn = database.get_ava_conn()
    br_conn  = database.get_bridge_conn()
    try:
        with ava_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO camera
                    (NAME, IP, PORT, ADMIN_ID, ADMIN_PASSWORD, RTSP_MAIN_URL, LAT, LNG)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data.name, data.ip, data.port,
                data.admin_id, data.admin_password, data.rtsp_main_url,
                data.lat, data.lng,
            ))
            ava_cam_id = cur.lastrowid
        ava_conn.commit()

        with br_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO camera_bridge (ava_cam_id, node_id, channel, name)
                VALUES (%s, %s, %s, %s)
            """, (ava_cam_id, data.node_id, data.channel, data.name))
        br_conn.commit()

        return {"ok": True, "ava_cam_id": ava_cam_id}
    finally:
        ava_conn.close()
        br_conn.close()


# ── VMS lookup: AVA camera ID → node_id + channel ───────────────────────────
@app.get("/node/{ava_cam_id}")
def get_node(ava_cam_id: int):
    """
    VMS gets node_id and channel using AVA camera ID from this endpoint.
    """
    br_conn = database.get_bridge_conn()
    try:
        with br_conn.cursor() as cur:
            cur.execute(
                "SELECT node_id, channel, name FROM camera_bridge WHERE ava_cam_id = %s",
                (ava_cam_id,)
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"ava_cam_id={ava_cam_id} is not registered")
        return {
            "node_id":       row["node_id"],
            "channel":       row["channel"],
            "name":   row["name"],
        }
    finally:
        br_conn.close()


# ── Kayıtlı kamera listesi (UI için) ────────────────────────────────────────
@app.get("/cameras")
def list_cameras():
    """
    Listing cameras for UI by joining bridge and AVA tables.
    VMS does not use this endpoint.
    """
    br_conn  = database.get_bridge_conn()
    ava_conn = database.get_ava_conn()
    try:
        with br_conn.cursor() as cur:
            cur.execute("SELECT * FROM camera_bridge ORDER BY id")
            rows = cur.fetchall()

        result = []
        for r in rows:
            with ava_conn.cursor() as cur:
                cur.execute(
                    "SELECT IP, PORT, RTSP_MAIN_URL, LAT, LNG FROM camera WHERE ID = %s",
                    (r["ava_cam_id"],)
                )
                ava = cur.fetchone() or {}
            result.append({**r, **ava})
        return result
    finally:
        br_conn.close()
        ava_conn.close()


# ── Kamera sil ───────────────────────────────────────────────────────────────
@app.delete("/cameras/{bridge_id}")
def delete_camera(bridge_id: int):
    """
        Removes both bridge record and AVA camera record using bridge_id. UI calls this endpoint when deleting a camera.
    """
    br_conn  = database.get_bridge_conn()
    ava_conn = database.get_ava_conn()
    try:
        with br_conn.cursor() as cur:
            cur.execute("SELECT ava_cam_id FROM camera_bridge WHERE id = %s", (bridge_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="is not registered")
            ava_cam_id = row["ava_cam_id"]
            cur.execute("DELETE FROM camera_bridge WHERE id = %s", (bridge_id,))
        br_conn.commit()

        with ava_conn.cursor() as cur:
            cur.execute("DELETE FROM camera WHERE ID = %s", (ava_cam_id,))
        ava_conn.commit()

        return {"ok": True}
    finally:
        br_conn.close()
        ava_conn.close()


if __name__ == "__main__":
    import uvicorn
    print("\n  API  →  http://localhost:8091")
    print("  Docs →  http://localhost:8091/docs\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8091, reload=True)
