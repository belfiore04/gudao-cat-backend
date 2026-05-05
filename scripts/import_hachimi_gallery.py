#!/usr/bin/env python
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import config
from app.database import Base, SessionLocal, engine
from app.models import *  # noqa: F401,F403 ensure models are registered
from app.models.cat import Cat
from app.models.cat_feature import CatFeature
from app.models.user import User

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import a hachimi gallery into gudao-cat cats and cat_features tables.",
    )
    parser.add_argument(
        "--gallery",
        default=config.HACHIMI_GALLERY_DIR,
        help="Gallery root. Each direct child directory is treated as one cat name.",
    )
    parser.add_argument(
        "--creator-username",
        required=True,
        help="Existing app username used as creator_id for imported cats.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete existing cat_features before importing.",
    )
    parser.add_argument(
        "--clear-imported-photos",
        action="store_true",
        help="Clear photos for cats found in the gallery before appending imported photo paths.",
    )
    return parser


def load_pipeline():
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

    return CatIdentificationPipeline(
        gd_config_path=config.HACHIMI_GD_CONFIG,
        gd_checkpoint_path=config.HACHIMI_GD_CHECKPOINT,
        sam_checkpoint_path=config.HACHIMI_SAM_CHECKPOINT,
        sam_type=config.HACHIMI_SAM_TYPE,
        device=config.HACHIMI_DEVICE,
    )


def iter_gallery_images(gallery: Path):
    if not gallery.exists():
        raise FileNotFoundError(f"图库目录不存在: {gallery}")
    for cat_dir in sorted(gallery.iterdir()):
        if not cat_dir.is_dir() or cat_dir.name == "videos":
            continue
        for image_path in sorted(cat_dir.iterdir()):
            if image_path.suffix.lower() in IMAGE_SUFFIXES:
                yield cat_dir.name, image_path


def main() -> int:
    args = build_parser().parse_args()
    gallery = Path(args.gallery).expanduser().resolve()
    Base.metadata.create_all(bind=engine)

    images = list(iter_gallery_images(gallery))
    if not images:
        print(f"No images found under {gallery}")
        return 2

    with SessionLocal() as db:
        creator = db.query(User).filter(User.username == args.creator_username).first()
        if creator is None:
            print(f"Creator user not found: {args.creator_username}")
            return 2

        if args.rebuild:
            deleted = db.query(CatFeature).delete()
            db.commit()
            print(f"Deleted {deleted} existing cat feature rows.")

        if args.clear_imported_photos:
            cat_names = sorted({cat_name for cat_name, _ in images})
            db.query(Cat).filter(Cat.name.in_(cat_names)).update(
                {Cat.photos: []},
                synchronize_session=False,
            )
            db.commit()

    print(f"Loading hachimi pipeline...")
    pipeline = load_pipeline()
    print(f"Importing {len(images)} images from {gallery}")

    stored = 0
    failed = 0
    with SessionLocal() as db:
        creator = db.query(User).filter(User.username == args.creator_username).first()
        assert creator is not None

        for index, (cat_name, image_path) in enumerate(images, start=1):
            print(f"[{index}/{len(images)}] {cat_name}: {image_path}")
            result = pipeline.process_image(str(image_path))
            if result is None:
                failed += 1
                print("  skipped: no cat detected")
                continue

            cat = db.query(Cat).filter(Cat.name == cat_name).first()
            if cat is None:
                cat = Cat(
                    name=cat_name,
                    habits=None,
                    location=None,
                    photos=[],
                    creator_id=creator.id,
                )
                db.add(cat)
                db.flush()

            vector, _ = result
            photo_url = str(image_path)
            db.add(CatFeature(cat_id=cat.id, embedding=vector, photo_url=photo_url))
            if photo_url not in (cat.photos or []):
                cat.photos = [*(cat.photos or []), photo_url]
            db.commit()
            stored += 1
            print(f"  stored: cat_id={cat.id}")

    print(f"Done. stored={stored}, failed={failed}, total={len(images)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
