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
    camera_name: str
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


@app.post("/cameras", status_code=201)
def add_camera(data: CameraIn):
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
                data.camera_name, data.ip, data.port,
                data.admin_id, data.admin_password, data.rtsp_main_url,
                data.lat, data.lng,
            ))
            ava_cam_id = cur.lastrowid
        ava_conn.commit()

        with br_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO camera_bridge (ava_cam_id, node_id, channel, camera_name)
                VALUES (%s, %s, %s, %s)
            """, (ava_cam_id, data.node_id, data.channel, data.camera_name))
        br_conn.commit()

        return {"ok": True, "ava_cam_id": ava_cam_id}
    finally:
        ava_conn.close()
        br_conn.close()


@app.get("/cameras")
def list_cameras():
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


@app.delete("/cameras/{bridge_id}")
def delete_camera(bridge_id: int):
    br_conn  = database.get_bridge_conn()
    ava_conn = database.get_ava_conn()
    try:
        with br_conn.cursor() as cur:
            cur.execute("SELECT ava_cam_id FROM camera_bridge WHERE id = %s", (bridge_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="not found")
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
