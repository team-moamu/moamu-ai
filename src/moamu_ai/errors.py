class PhotoVerificationError(Exception):
    """사진 인증 과정에서 API 오류 응답으로 변환할 수 있는 예외의 기반 클래스."""


class ImageRootUnavailableError(PhotoVerificationError):
    """설정된 로컬 이미지 루트를 사용할 수 없을 때 발생한다."""


class ImageNotFoundError(PhotoVerificationError):
    """요청한 이미지 파일을 찾을 수 없을 때 발생한다."""


class ImagePathNotAllowedError(PhotoVerificationError):
    """이미지 경로가 허용된 루트 바깥을 가리킬 때 발생한다."""


class ImageUnreadableError(PhotoVerificationError):
    """이미지 파일을 읽거나 경로를 확인할 수 없을 때 발생한다."""


class ImageFetchFailedError(PhotoVerificationError):
    """저장소에서 인증 이미지를 가져오지 못했을 때 발생한다."""


class UnsupportedImageError(PhotoVerificationError):
    """인증에 사용할 수 없는 이미지 형식일 때 발생한다."""


class ImageStoreConfigurationError(PhotoVerificationError):
    """이미지 저장소 설정이나 클라이언트 구성이 잘못되었을 때 발생한다."""


class ProviderConfigurationError(PhotoVerificationError):
    """AI 모델 공급자 설정이 없거나 올바르지 않을 때 발생한다."""


class ModelProviderError(PhotoVerificationError):
    """AI 모델 호출 또는 이미지 전달에 실패했을 때 발생한다."""


class InvalidModelOutputError(PhotoVerificationError):
    """모델 응답이 기대한 구조나 조건 목록과 맞지 않을 때 발생한다."""
