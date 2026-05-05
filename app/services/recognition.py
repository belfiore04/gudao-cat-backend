import math
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import joinedload

from app import config
from app.database import SessionLocal
from app.models.cat import Cat
from app.models.cat_feature import CatFeature


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


class RecognitionQueueFull(RuntimeError):
    pass


@dataclass
class RecognitionJob:
    id: str
    kind: str
    status: str
    created_at: datetime
    updated_at: datetime
    filename: str | None = None
    user_id: int | None = None
    progress: dict = field(default_factory=dict)
    result: dict | None = None
    error: str | None = None
    finished_at: datetime | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class RecognitionService:
    def __init__(self):
        self.upload_dir = Path(config.UPLOAD_DIR) / "recognition"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.gallery_dir = Path(config.HACHIMI_GALLERY_DIR)
        self._executor = ThreadPoolExecutor(max_workers=config.RECOGNITION_MAX_WORKERS)
        self._jobs: dict[str, RecognitionJob] = {}
        self._jobs_lock = threading.RLock()
        self._pipeline = None
        self._pipeline_lock = threading.Lock()

    def snapshot(self) -> dict:
        with self._jobs_lock:
            queued = sum(1 for job in self._jobs.values() if job.status == "queued")
            running = sum(1 for job in self._jobs.values() if job.status == "running")
            completed = sum(1 for job in self._jobs.values() if job.status == "completed")
            failed = sum(1 for job in self._jobs.values() if job.status == "failed")
        return {
            "queued": queued,
            "running": running,
            "completed": completed,
            "failed": failed,
            "max_workers": config.RECOGNITION_MAX_WORKERS,
            "max_queue_size": config.RECOGNITION_MAX_QUEUE_SIZE,
            "model_loaded": self._pipeline is not None,
        }

    def active_job_count(self) -> int:
        with self._jobs_lock:
            return sum(1 for job in self._jobs.values() if job.status in {"queued", "running"})

    def save_upload(self, file_obj, filename: str | None) -> Path:
        suffix = Path(filename or "").suffix.lower()
        if suffix not in IMAGE_SUFFIXES:
            suffix = ".jpg"

        path = self.upload_dir / f"{uuid4().hex}{suffix}"
        limit_bytes = config.RECOGNITION_MAX_UPLOAD_MB * 1024 * 1024
        written = 0

        with path.open("wb") as out:
            while True:
                chunk = file_obj.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > limit_bytes:
                    out.close()
                    path.unlink(missing_ok=True)
                    raise ValueError(f"上传图片超过 {config.RECOGNITION_MAX_UPLOAD_MB} MB")
                out.write(chunk)

        return path

    def submit_recognition(
        self,
        image_path: Path,
        filename: str | None,
        user_id: int,
        threshold: float | None = None,
    ) -> dict:
        self._ensure_capacity()
        job = self._create_job(kind="recognition", filename=filename, user_id=user_id)
        self._executor.submit(self._run_recognition, job.id, image_path, threshold)
        return job.to_dict()

    def submit_gallery_build(self, user_id: int, rebuild: bool = False) -> dict:
        self._ensure_capacity()
        job = self._create_job(kind="gallery_build", filename=None, user_id=user_id)
        self._executor.submit(self._run_gallery_build, job.id, user_id, rebuild)
        return job.to_dict()

    def get_job(self, job_id: str, user_id: int) -> dict | None:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if job is None or job.user_id != user_id:
                return None
            return job.to_dict()

    def _ensure_capacity(self) -> None:
        if self.active_job_count() >= config.RECOGNITION_MAX_QUEUE_SIZE:
            raise RecognitionQueueFull("识别队列已满，请稍后再试")

    def _create_job(self, kind: str, filename: str | None, user_id: int) -> RecognitionJob:
        now = datetime.utcnow()
        job = RecognitionJob(
            id=uuid4().hex,
            kind=kind,
            status="queued",
            filename=filename,
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        with self._jobs_lock:
            self._jobs[job.id] = job
        return job

    def _update_job(self, job_id: str, **changes) -> None:
        with self._jobs_lock:
            job = self._jobs[job_id]
            for key, value in changes.items():
                setattr(job, key, value)
            job.updated_at = datetime.utcnow()
            if job.status in {"completed", "failed"} and job.finished_at is None:
                job.finished_at = job.updated_at

    def _get_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline

        with self._pipeline_lock:
            if self._pipeline is not None:
                return self._pipeline

            required_paths = [
                Path(config.HACHIMI_ROOT),
                Path(config.HACHIMI_GD_CONFIG),
                Path(config.HACHIMI_GD_CHECKPOINT),
                Path(config.HACHIMI_SAM_CHECKPOINT),
            ]
            missing = [str(path) for path in required_paths if not path.exists()]
            if missing:
                raise RuntimeError("hachimi 模型或配置文件缺失: " + ", ".join(missing))

            hachimi_root = str(Path(config.HACHIMI_ROOT).resolve())
            if hachimi_root not in sys.path:
                sys.path.insert(0, hachimi_root)

            from core_pipeline import CatIdentificationPipeline

            self._pipeline = CatIdentificationPipeline(
                gd_config_path=config.HACHIMI_GD_CONFIG,
                gd_checkpoint_path=config.HACHIMI_GD_CHECKPOINT,
                sam_checkpoint_path=config.HACHIMI_SAM_CHECKPOINT,
                sam_type=config.HACHIMI_SAM_TYPE,
                device=config.HACHIMI_DEVICE,
            )
            return self._pipeline

    def _run_recognition(self, job_id: str, image_path: Path, threshold: float | None) -> None:
        started = time.time()
        threshold_value = threshold if threshold is not None else config.RECOGNITION_THRESHOLD
        self._update_job(job_id, status="running", progress={"stage": "loading_model"})

        try:
            pipeline = self._get_pipeline()
            self._update_job(job_id, progress={"stage": "detect_segment_extract"})
            inference_started = time.time()
            result = pipeline.process_image(str(image_path))
            inference_seconds = time.time() - inference_started

            if result is None:
                self._update_job(
                    job_id,
                    status="completed",
                    result={
                        "detected": False,
                        "accepted": False,
                        "decision": "no_cat_detected",
                        "top1": None,
                        "matches": [],
                        "threshold": threshold_value,
                        "timing": {
                            "inference_seconds": inference_seconds,
                            "total_seconds": time.time() - started,
                        },
                    },
                )
                return

            query_vector, _ = result
            self._update_job(job_id, progress={"stage": "search"})
            search_started = time.time()
            matches = self._search_matches(query_vector, config.RECOGNITION_TOP_K)
            search_seconds = time.time() - search_started

            top1 = matches[0] if matches else None
            accepted = bool(top1 and top1["distance"] < threshold_value)
            self._update_job(
                job_id,
                status="completed",
                result={
                    "detected": True,
                    "accepted": accepted,
                    "decision": top1["cat_name"] if accepted else "unknown",
                    "top1": top1,
                    "matches": matches,
                    "threshold": threshold_value,
                    "timing": {
                        "inference_seconds": inference_seconds,
                        "search_seconds": search_seconds,
                        "total_seconds": time.time() - started,
                    },
                },
            )
        except Exception as exc:
            self._update_job(job_id, status="failed", error=str(exc))

    def _run_gallery_build(self, job_id: str, user_id: int, rebuild: bool) -> None:
        self._update_job(job_id, status="running", progress={"stage": "loading_model"})
        started = time.time()
        stored = 0
        failed = 0

        try:
            pipeline = self._get_pipeline()
            images = list(self._iter_gallery_images())

            with SessionLocal() as db:
                if rebuild:
                    db.query(CatFeature).delete()
                    db.commit()

                for index, (cat_name, image_path) in enumerate(images, start=1):
                    self._update_job(
                        job_id,
                        progress={
                            "stage": "building_gallery",
                            "current": index,
                            "total": len(images),
                            "cat_name": cat_name,
                            "image": str(image_path),
                        },
                    )

                    result = pipeline.process_image(str(image_path))
                    if result is None:
                        failed += 1
                        continue

                    cat = db.query(Cat).filter(Cat.name == cat_name).first()
                    if cat is None:
                        cat = Cat(
                            name=cat_name,
                            habits=None,
                            location=None,
                            photos=[],
                            creator_id=user_id,
                        )
                        db.add(cat)
                        db.flush()

                    vector, _ = result
                    db.add(
                        CatFeature(
                            cat_id=cat.id,
                            embedding=vector,
                            photo_url=str(image_path),
                        )
                    )
                    if str(image_path) not in (cat.photos or []):
                        cat.photos = [*(cat.photos or []), str(image_path)]
                    stored += 1
                    db.commit()

            self._update_job(
                job_id,
                status="completed",
                result={
                    "stored": stored,
                    "failed": failed,
                    "total_images": len(images),
                    "total_seconds": time.time() - started,
                },
            )
        except Exception as exc:
            self._update_job(job_id, status="failed", error=str(exc))

    def _iter_gallery_images(self):
        for cat_dir in sorted(self.gallery_dir.iterdir()):
            if not cat_dir.is_dir() or cat_dir.name == "videos":
                continue
            for image_path in sorted(cat_dir.iterdir()):
                if image_path.suffix.lower() in IMAGE_SUFFIXES:
                    yield cat_dir.name, image_path

    def _search_matches(self, query_vector: list[float], top_k: int) -> list[dict]:
        best_by_cat: dict[int, dict] = {}
        with SessionLocal() as db:
            features = (
                db.query(CatFeature)
                .options(joinedload(CatFeature.cat))
                .filter(CatFeature.embedding.isnot(None))
                .all()
            )
            for feature in features:
                distance = cosine_distance(query_vector, feature.embedding)
                existing = best_by_cat.get(feature.cat_id)
                if existing is None or distance < existing["distance"]:
                    best_by_cat[feature.cat_id] = {
                        "cat_id": feature.cat_id,
                        "cat_name": feature.cat.name,
                        "distance": distance,
                        "photo_url": feature.photo_url,
                        "cat": {
                            "id": feature.cat.id,
                            "name": feature.cat.name,
                            "habits": feature.cat.habits,
                            "location": feature.cat.location,
                            "photos": feature.cat.photos,
                            "creator_id": feature.cat.creator_id,
                            "created_at": feature.cat.created_at,
                        },
                    }

        return sorted(best_by_cat.values(), key=lambda item: item["distance"])[:top_k]


def cosine_distance(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return math.inf

    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for a, b in zip(left, right):
        dot += a * b
        left_norm += a * a
        right_norm += b * b

    if left_norm <= 0 or right_norm <= 0:
        return math.inf
    return 1.0 - dot / (math.sqrt(left_norm) * math.sqrt(right_norm))


recognition_service = RecognitionService()
