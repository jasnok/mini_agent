"""번호판 이미지 인식의 HTTP 진입점입니다."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.errors import ImageTooLargeError, RecognitionDependencyError, UnsupportedImageError
from app.schemas.parking import VehicleRecognizeResponse
from app.services.vehicle_recognition_service import recognize_vehicle


vehicle_router = APIRouter(prefix="/api/vehicle", tags=["주차장 · 번호판 인식"])


@vehicle_router.post("/recognize", response_model=VehicleRecognizeResponse)
async def recognize_vehicle_image(image: UploadFile = File(...)) -> VehicleRecognizeResponse:
    content = await image.read()
    try:
        return recognize_vehicle(
            filename=image.filename or "",
            content_type=image.content_type,
            content=content,
        )
    except ImageTooLargeError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except UnsupportedImageError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except TimeoutError as error:
        raise HTTPException(status_code=504, detail="번호판 인식 시간이 초과되었습니다.") from error
    except RecognitionDependencyError as error:
        raise HTTPException(status_code=502, detail="번호판 인식 서비스를 사용할 수 없습니다.") from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="번호판 인식 중 내부 오류가 발생했습니다.") from error
