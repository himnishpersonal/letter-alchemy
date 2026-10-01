"""Thin FastAPI application over the reviewed puzzle bank."""

import os
import statistics
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import DateTime, Integer, String, UniqueConstraint, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .lexicon import ROOT, load_lexicon
from .puzzles import BANK, Puzzle, load_bank, validate_intermediates


class Base(DeclarativeBase):
    pass


class Completion(Base):
    __tablename__ = "completions"
    __table_args__ = (UniqueConstraint("puzzle_number", "device_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    puzzle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    device_id: Mapped[str] = mapped_column(String(36), nullable=False)
    seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    hints_used: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ValidationRequest(BaseModel):
    intermediates: list[str | None] = Field(min_length=3, max_length=3)

    @field_validator("intermediates")
    @classmethod
    def clean_words(cls, values: list[str | None]) -> list[str | None]:
        result = []
        for word in values:
            if word is None:
                result.append(None)
            elif len(word) == 5 and word.isascii() and word.isalpha():
                result.append(word.upper())
            else:
                raise ValueError("Each filled slot must be five ASCII letters")
        return result


class CompletionRequest(ValidationRequest):
    device_id: UUID
    seconds: int = Field(ge=1, le=86400)
    hints_used: int = Field(ge=0, le=3)


def create_app(bank_path: Path = BANK / "puzzles.json", database_url: str | None = None,
               today_fn=None) -> FastAPI:
    launch, puzzles = load_bank(bank_path)
    if os.getenv("ALCHEMY_LAUNCH_DATE"):
        launch = date.fromisoformat(os.environ["ALCHEMY_LAUNCH_DATE"])
    valid, _ = load_lexicon()
    if database_url is None:
        database_url = os.getenv("DATABASE_URL")
    if not database_url:
        if os.getenv("K_SERVICE") or os.getenv("RENDER"):
            raise RuntimeError("DATABASE_URL is required on hosted services; container storage is ephemeral")
        database_url = f"sqlite:///{ROOT / 'alchemy.sqlite3'}"
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    today_fn = today_fn or (lambda: datetime.now(timezone.utc).date())
    app = FastAPI(title="Letter Alchemy API", version="0.1.0")
    origins = [origin.strip() for origin in os.getenv("ALCHEMY_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if origin.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type"])

    def released(number: int) -> Puzzle:
        today_number = (today_fn() - launch).days + 1
        if number < 1 or number > today_number or number not in puzzles:
            raise HTTPException(status_code=404, detail="Puzzle not available")
        return puzzles[number]

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "bank_size": len(puzzles)}

    @app.get("/puzzle/today")
    def today():
        number = (today_fn() - launch).days + 1
        return released(number).public()

    @app.get("/puzzle/{number}")
    def puzzle(number: int):
        return released(number).public()

    @app.post("/puzzle/{number}/validate")
    def validate(number: int, request: ValidationRequest):
        return validate_intermediates(released(number), request.intermediates, valid)

    @app.post("/puzzle/{number}/complete")
    def complete(number: int, request: CompletionRequest):
        puzzle_record = released(number)
        result = validate_intermediates(puzzle_record, request.intermediates, valid)
        if not result["solved"]:
            raise HTTPException(status_code=422, detail=result)
        with Session(engine) as session:
            existing = session.scalar(select(Completion).where(Completion.puzzle_number == number,
                                                                Completion.device_id == str(request.device_id)))
            if existing is not None:
                return {"recorded": False, "already_completed": True}
            session.add(Completion(puzzle_number=number, device_id=str(request.device_id),
                                   seconds=request.seconds, hints_used=request.hints_used,
                                   created_at=datetime.now(timezone.utc)))
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                duplicate = session.scalar(select(Completion.id).where(
                    Completion.puzzle_number == number, Completion.device_id == str(request.device_id)))
                if duplicate is None:
                    raise
                return {"recorded": False, "already_completed": True}
        return {"recorded": True, "already_completed": False}

    @app.get("/puzzle/{number}/stats")
    def stats(number: int):
        released(number)
        with Session(engine) as session:
            durations = session.scalars(select(Completion.seconds).where(Completion.puzzle_number == number)).all()
        return {"completions": len(durations),
                "median_seconds": statistics.median(durations) if durations else None}

    return app
