import json
import os
import shutil
import subprocess
import threading
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

load_dotenv()

TMP_DIR = Path("/tmp")
TTL_SECONDS = 10 * 60
CLEANUP_INTERVAL_SECONDS = 60
HEYGEN_GENERATE_URL = "https://api.heygen.com/v2/video/generate"
HEYGEN_STATUS_URL = "https://api.heygen.com/v1/video_status.get"
HEYGEN_ASSET_UPLOAD_URL = "https://api.heygen.com/v1/asset.upload"
LOGO_PATH = TMP_DIR / "logo.png"


class Mode(str, Enum):
    ad = "ad"
    reel = "reel"
    presentation = "presentation"


class GenerateRequest(BaseModel):
    prompt: str
    mode: Mode
    audience: str = ""
    tone: str = ""


class ScriptParts(BaseModel):
    hook: str
    body: str
    cta: str
    caption: str


app = FastAPI(title="AI Social Media Video Generator API")

origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _make_prompt_template(mode: Mode) -> PromptTemplate:
    common_instructions = (
        "Return valid JSON only, with keys: hook, body, cta, caption. "
        "No markdown, no code fences, no extra text."
    )

    if mode == Mode.ad:
        template = (
            "You are an expert direct-response copywriter. Use PAS framework (Problem, Agitate, Solve) "
            "to create a short business video script focused on conversion.\n"
            "Prompt: {prompt}\nAudience: {audience}\nTone: {tone}\n"
            f"{common_instructions}"
        )
    elif mode == Mode.reel:
        template = (
            "You are a viral social media strategist. Create a short reel script with a hook in the first 2 seconds, "
            "fast-paced and highly engaging content.\n"
            "Prompt: {prompt}\nAudience: {audience}\nTone: {tone}\n"
            f"{common_instructions}"
        )
    else:
        template = (
            "You are a startup pitch coach. Create a structured presentation script with clear explanation and "
            "professional flow.\n"
            "Prompt: {prompt}\nAudience: {audience}\nTone: {tone}\n"
            f"{common_instructions}"
        )

    return PromptTemplate.from_template(template)


def _generate_script(data: GenerateRequest) -> ScriptParts:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model, temperature=0.7)
    prompt_template = _make_prompt_template(data.mode)
    chain = prompt_template | llm

    output = chain.invoke(
        {
            "prompt": data.prompt,
            "audience": data.audience or "General business audience",
            "tone": data.tone or "Confident and concise",
        }
    )

    content = output.content if isinstance(output.content, str) else "".join(output.content)

    try:
        parsed = json.loads(content)
        return ScriptParts(**parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=502, detail=f"Script generation format error: {exc}") from exc


def _build_final_script(parts: ScriptParts) -> str:
    return f"{parts.hook}\n\n{parts.body}\n\n{parts.cta}"


def _poll_heygen_video_id(video_id: str, headers: dict[str, str]) -> str:
    timeout_seconds = 240
    start_time = time.time()

    while True:
        if time.time() - start_time > timeout_seconds:
            raise HTTPException(status_code=504, detail="Timed out waiting for HeyGen video generation")

        response = requests.get(HEYGEN_STATUS_URL, headers=headers, params={"video_id": video_id}, timeout=30)
        if not response.ok:
            raise HTTPException(status_code=502, detail=f"HeyGen status error: {response.text}")

        payload = response.json() or {}
        data = payload.get("data", {})
        status = (data.get("status") or "").lower()

        if status in {"completed", "success"}:
            video_url = data.get("video_url") or data.get("url")
            if not video_url:
                raise HTTPException(status_code=502, detail="HeyGen completed response missing video URL")
            return video_url

        if status in {"failed", "error"}:
            raise HTTPException(status_code=502, detail=f"HeyGen generation failed: {payload}")

        time.sleep(3)


def _upload_image_asset_to_heygen(image_file: UploadFile, api_key: str) -> Optional[str]:
    try:
        content = image_file.file.read()
        if not content:
            return None

        files = {
            "file": (
                image_file.filename or "avatar-image.png",
                content,
                image_file.content_type or "image/png",
            )
        }
        headers = {"X-Api-Key": api_key}

        response = requests.post(HEYGEN_ASSET_UPLOAD_URL, headers=headers, files=files, timeout=60)
        if not response.ok:
            return None

        payload = response.json() or {}
        data = payload.get("data", {})
        return data.get("talking_photo_id") or data.get("asset_id")
    except Exception:
        return None
    finally:
        image_file.file.seek(0)


def _generate_heygen_video(script: str, image_file: Optional[UploadFile]) -> str:
    api_key = os.getenv("HEYGEN_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="HEYGEN_API_KEY is not configured")

    default_avatar_id = "Josh_lite20230714"
    avatar_id = os.getenv("HEYGEN_AVATAR_ID", default_avatar_id)
    voice_id = os.getenv("HEYGEN_VOICE_ID", "1bd001e7e50f421d891986aad5158bc8")

    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json",
    }

    video_input = {
        "character": {
            "type": "avatar",
            "avatar_id": avatar_id,
        },
        "voice": {
            "type": "text",
            "voice_id": voice_id,
            "input_text": script,
        },
    }

    talking_photo_id = None
    if image_file is not None:
        talking_photo_id = _upload_image_asset_to_heygen(image_file, api_key)

    if talking_photo_id:
        video_input["character"]["type"] = "talking_photo"
        video_input["character"]["talking_photo_id"] = talking_photo_id

    payload = {
        "video_inputs": [video_input],
        "test": False,
    }

    response = requests.post(HEYGEN_GENERATE_URL, headers=headers, json=payload, timeout=60)
    if not response.ok and talking_photo_id is None and avatar_id != default_avatar_id:
        response_text = response.text.lower()
        if (
            "avatar lock not found" in response_text
            or "avatar look not found" in response_text
            or "avatar not found" in response_text
        ):
            video_input["character"]["avatar_id"] = default_avatar_id
            response = requests.post(HEYGEN_GENERATE_URL, headers=headers, json=payload, timeout=60)

    if not response.ok:
        response_text = response.text.lower()
        if talking_photo_id is None and (
            "avatar lock not found" in response_text
            or "avatar look not found" in response_text
            or "avatar not found" in response_text
        ):
            raise HTTPException(
                status_code=502,
                detail=(
                    f"HeyGen avatar configuration invalid for HEYGEN_AVATAR_ID='{avatar_id}'. "
                    "Set a valid avatar ID from your HeyGen account, or remove HEYGEN_AVATAR_ID to use default fallback."
                ),
            )
        raise HTTPException(status_code=502, detail=f"HeyGen generate error: {response.text}")

    generate_data = response.json() or {}
    video_id = (generate_data.get("data") or {}).get("video_id")
    if not video_id:
        raise HTTPException(status_code=502, detail="HeyGen response missing video_id")

    return _poll_heygen_video_id(video_id, headers)


def _save_video_to_tmp(source_url: str) -> str:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    video_id = str(uuid.uuid4())
    output_path = TMP_DIR / f"{video_id}.mp4"

    with requests.get(source_url, stream=True, timeout=120) as response:
        if not response.ok:
            raise HTTPException(status_code=502, detail=f"Failed to download rendered video: {response.text}")
        with output_path.open("wb") as file_obj:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file_obj.write(chunk)

    return video_id


def _save_logo_to_tmp(logo_file: UploadFile) -> Optional[Path]:
    try:
        content = logo_file.file.read()
        if not content:
            return None

        TMP_DIR.mkdir(parents=True, exist_ok=True)
        with LOGO_PATH.open("wb") as file_obj:
            file_obj.write(content)
        return LOGO_PATH
    except Exception:
        return None
    finally:
        logo_file.file.seek(0)


def _overlay_logo_on_video(video_id: str, logo_path: Optional[Path]) -> None:
    if logo_path is None or not logo_path.exists():
        return

    ffmpeg_binary = os.getenv("FFMPEG_BINARY", "ffmpeg")
    if shutil.which(ffmpeg_binary) is None:
        raise HTTPException(status_code=500, detail="FFmpeg is not installed or not available in PATH")

    input_video = TMP_DIR / f"{video_id}.mp4"
    output_video = TMP_DIR / f"{video_id}_logo.mp4"

    command = [
        ffmpeg_binary,
        "-y",
        "-i",
        str(input_video),
        "-i",
        str(logo_path),
        "-filter_complex",
        "[1:v]scale='min(100,iw)':-1[logo];[0:v][logo]overlay=10:10",
        "-c:a",
        "copy",
        str(output_video),
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=502, detail=f"FFmpeg logo overlay failed: {result.stderr}")

    output_video.replace(input_video)


def _cleanup_tmp_files_loop() -> None:
    while True:
        now = time.time()
        try:
            for file_path in TMP_DIR.glob("*.mp4"):
                if now - file_path.stat().st_mtime > TTL_SECONDS:
                    file_path.unlink(missing_ok=True)
        except Exception:
            pass
        time.sleep(CLEANUP_INTERVAL_SECONDS)


@app.on_event("startup")
def _startup() -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    thread = threading.Thread(target=_cleanup_tmp_files_loop, daemon=True)
    thread.start()


async def _parse_generate_input(request: Request) -> GenerateRequest:
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        data = await request.json()
        return GenerateRequest(**data)

    form = await request.form()
    payload = {
        "prompt": form.get("prompt", ""),
        "mode": form.get("mode", "ad"),
        "audience": form.get("audience", ""),
        "tone": form.get("tone", ""),
    }
    return GenerateRequest(**payload)


@app.post("/generate")
async def generate_video(
    request: Request,
    image: Optional[UploadFile] = File(default=None),
    logo: Optional[UploadFile] = File(default=None),
) -> dict:
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    try:
        payload = await _parse_generate_input(request)
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid request body: {exc}") from exc

    script_parts = _generate_script(payload)
    final_script = _build_final_script(script_parts)
    heygen_video_url = _generate_heygen_video(final_script, image)
    local_video_id = _save_video_to_tmp(heygen_video_url)

    logo_file = logo or image
    if logo_file is not None:
        logo_path = _save_logo_to_tmp(logo_file)
        _overlay_logo_on_video(local_video_id, logo_path)

    return {
        "video_url": f"/video/{local_video_id}",
        "script": final_script,
        "caption": script_parts.caption,
    }


@app.get("/video/{video_id}")
def get_video(video_id: str) -> FileResponse:
    file_path = TMP_DIR / f"{video_id}.mp4"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video not found or expired")

    return FileResponse(path=str(file_path), media_type="video/mp4", filename=f"{video_id}.mp4")


@app.get("/health")
def health() -> dict:
    return {"status": "OK"}
