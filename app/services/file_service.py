import logging
import uuid
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.feature_model import FeatureRecord
from app.models.file_model import FileRecord, FileStatus
from app.services.geospatial_service import read_geospatial_file
from app.utils.exceptions import ApplicationError
from app.utils.file_validator import validate_filename, validate_upload_bytes

logger = logging.getLogger(__name__)


class FileService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def process_upload(self, upload: UploadFile) -> FileRecord:
        extension = validate_filename(upload.filename, self.settings)
        data = await upload.read(self.settings.max_upload_size_bytes + 1)
        validate_upload_bytes(data, extension, self.settings)
        stored_name = f"{uuid.uuid4().hex}{extension}"
        stored_path = self.settings.upload_directory / stored_name
        stored_path.parent.mkdir(parents=True, exist_ok=True)
        stored_path.write_bytes(data)
        record = FileRecord(original_filename=upload.filename or "unnamed", stored_filename=stored_name, file_type=extension)
        self.db.add(record)
        self.db.flush()
        try:
            features, source_crs = read_geospatial_file(stored_path, extension)
            record.source_crs = source_crs
            record.feature_count = len(features)
            for item in features:
                result = item["measurement"]
                self.db.add(
                    FeatureRecord(
                        file_id=record.id,
                        feature_index=item["feature_index"],
                        geometry_type=item["geometry_type"],
                        geometry=item["geometry"],
                        properties=item["properties"],
                        area=result.value if result.measurement_type == "area" else None,
                        area_unit=result.unit if result.measurement_type == "area" else None,
                        length=result.value if result.measurement_type == "length" else None,
                        length_unit=result.unit if result.measurement_type == "length" else None,
                        measurement_crs=result.measurement_crs,
                        measurement_status=result.status,
                        measurement_message=result.message,
                    )
                )
            record.status = FileStatus.COMPLETED
            self.db.commit()
            self.db.refresh(record)
            logger.info("Processed file %s with %d features", record.id, record.feature_count)
            return record
        except ApplicationError as exc:
            self.db.rollback()
            record.status = FileStatus.FAILED
            record.error_message = exc.message
            self.db.add(record)
            self.db.commit()
            raise
        except Exception:
            self.db.rollback()
            logger.exception("Unexpected failure processing upload")
            record.status = FileStatus.FAILED
            record.error_message = "File processing failed unexpectedly."
            self.db.add(record)
            self.db.commit()
            raise ApplicationError("File processing failed unexpectedly.")
        finally:
            stored_path.unlink(missing_ok=True)
