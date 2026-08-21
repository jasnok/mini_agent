from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from openai import APITimeoutError
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.schemas import TtsRequest, VoiceTranslationResult
from app.services.media_service import (
    AudioTooLargeError,
    UnsupportedAudioTypeError,
    analyze_image,
    create_speech,
    translate_voice,
)


media_router = APIRouter(prefix="/api/media", tags=["Multimodal"])


@media_router.post("/image-analysis")
async def image_analysis(
    image: UploadFile = File(...),
    question: str = Form("여행자가 알아야 할 정보와 주의점을 알려주세요."),
) -> dict:
    try:
        result = analyze_image(image.content_type or "", await image.read(), question)
        return result.model_dump()
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"이미지 분석 실패: {error}") from error


@media_router.post("/tts")
def text_to_speech(payload: TtsRequest) -> Response:
    try:
        audio = create_speech(payload.text, payload.voice, payload.instructions)
        return Response(
            content=audio,
            media_type="audio/mpeg",
            headers={"X-Synthetic-Voice": "true"},
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"TTS 생성 실패: {error}") from error


@media_router.post("/voice-translation", response_model=VoiceTranslationResult)
async def voice_translation(
    audio: UploadFile = File(...),
    source_language: str = Form("ko"),
    target_language: str = Form("en"),
    voice: str | None = Form(None),
) -> VoiceTranslationResult:
    if source_language != "ko" or target_language != "en":
        raise HTTPException(status_code=422, detail="현재는 한국어(ko)에서 영어(en) 번역만 지원합니다.")
    try:
        max_bytes = settings.max_audio_size_mb * 1024 * 1024
        content = await audio.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise AudioTooLargeError(
                f"음성 파일은 {settings.max_audio_size_mb}MB 이하여야 합니다."
            )
        return await run_in_threadpool(
            translate_voice,
            audio.content_type or "",
            content,
            voice,
        )
    except AudioTooLargeError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except UnsupportedAudioTypeError as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    except APITimeoutError as error:
        raise HTTPException(status_code=504, detail="음성 처리 응답 시간이 초과되었습니다.") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"음성 번역 실패: {error}") from error
    finally:
        await audio.close()
