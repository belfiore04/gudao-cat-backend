import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gudao_cat.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

HACHIMI_ROOT = os.getenv("HACHIMI_ROOT", "/root/hachimi")
HACHIMI_GD_CONFIG = os.getenv(
    "HACHIMI_GD_CONFIG",
    f"{HACHIMI_ROOT}/GroundingDINO/groundingdino/config/GroundingDINO_SwinT_OGC.py",
)
HACHIMI_GD_CHECKPOINT = os.getenv(
    "HACHIMI_GD_CHECKPOINT",
    f"{HACHIMI_ROOT}/weights/groundingdino_swint_ogc.pth",
)
HACHIMI_SAM_CHECKPOINT = os.getenv(
    "HACHIMI_SAM_CHECKPOINT",
    f"{HACHIMI_ROOT}/weights/sam_vit_h_4b8939.pth",
)
HACHIMI_SAM_TYPE = os.getenv("HACHIMI_SAM_TYPE", "vit_h")
HACHIMI_DEVICE = os.getenv("HACHIMI_DEVICE") or None
HACHIMI_GALLERY_DIR = os.getenv("HACHIMI_GALLERY_DIR", f"{HACHIMI_ROOT}/dataset/gallery")

RECOGNITION_THRESHOLD = float(os.getenv("RECOGNITION_THRESHOLD", "0.35"))
RECOGNITION_TOP_K = int(os.getenv("RECOGNITION_TOP_K", "5"))
RECOGNITION_MAX_WORKERS = max(1, int(os.getenv("RECOGNITION_MAX_WORKERS", "1")))
RECOGNITION_MAX_QUEUE_SIZE = max(1, int(os.getenv("RECOGNITION_MAX_QUEUE_SIZE", "20")))
RECOGNITION_MAX_UPLOAD_MB = max(1, int(os.getenv("RECOGNITION_MAX_UPLOAD_MB", "12")))
