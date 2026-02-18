from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from ..db.models import Note, NoteTag, Tag
from ..db.session import get_db
from ..deps import get_current_user
from ..schemas import NoteCreateRequest, NoteOut, NoteTagOut, NoteUpdateRequest

router = APIRouter(prefix="/notes", tags=["notes"])


def _note_to_out(note: Note) -> NoteOut:
    return NoteOut(
        id=note.id,
        title=note.title,
        content=note.content,
        pinned=note.pinned,
        favorited=note.favorited,
        created_at=note.created_at,
        updated_at=note.updated_at,
        tags=[NoteTagOut(id=t.id, name=t.name) for t in (note.tags or [])],
    )


@router.get(
    "",
    response_model=list[NoteOut],
    summary="List/search notes",
    description="List notes for the current user, with optional search/filtering by tag/pinned/favorited.",
    operation_id="list_notes",
)
async def list_notes(
    q: str | None = Query(None, description="Search query (matches title/content)"),
    tag_id: int | None = Query(None, description="Filter by tag id"),
    pinned: bool | None = Query(None, description="If true, return only pinned notes"),
    favorited: bool | None = Query(None, description="If true, return only favorited notes"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> list[NoteOut]:
    """List notes."""
    stmt = select(Note).where(Note.user_id == user.id)

    if pinned is True:
        stmt = stmt.where(Note.pinned.is_(True))
    if favorited is True:
        stmt = stmt.where(Note.favorited.is_(True))

    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Note.title.ilike(like), Note.content.ilike(like)))

    if tag_id:
        stmt = stmt.join(NoteTag, NoteTag.note_id == Note.id).where(NoteTag.tag_id == tag_id)

    stmt = stmt.order_by(Note.pinned.desc(), Note.updated_at.desc(), Note.id.desc())
    res = await db.execute(stmt)
    notes = res.scalars().unique().all()
    return [_note_to_out(n) for n in notes]


@router.post(
    "",
    response_model=NoteOut,
    summary="Create note",
    description="Create a note with optional tags.",
    operation_id="create_note",
)
async def create_note(
    payload: NoteCreateRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)
) -> NoteOut:
    """Create note."""
    title = (payload.title or "").strip()
    if len(title) > 120:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Title too long")

    note = Note(user_id=user.id, title=title, content=payload.content or "")
    db.add(note)
    await db.commit()
    await db.refresh(note)

    # Attach tags (validate ownership)
    if payload.tag_ids:
        res = await db.execute(
            select(Tag.id).where(and_(Tag.user_id == user.id, Tag.id.in_(payload.tag_ids)))
        )
        ok_ids = {r[0] for r in res.all()}
        for tid in payload.tag_ids:
            if tid in ok_ids:
                db.add(NoteTag(note_id=note.id, tag_id=tid))
        await db.commit()

    # reload with tags
    res2 = await db.execute(select(Note).where(Note.id == note.id))
    note2 = res2.scalar_one()
    return _note_to_out(note2)


@router.put(
    "/{note_id}",
    response_model=NoteOut,
    summary="Update note",
    description="Update title/content and/or tags.",
    operation_id="update_note",
)
async def update_note(
    note_id: int,
    payload: NoteUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> NoteOut:
    """Update note."""
    res = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == user.id))
    note = res.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Note not found")

    if payload.title is not None:
        note.title = payload.title.strip()
    if payload.content is not None:
        note.content = payload.content

    # update updated_at explicitly for SQLite-like behavior; Postgres onupdate also works.
    note.updated_at = func.now()  # type: ignore[assignment]

    await db.commit()

    if payload.tag_ids is not None:
        # remove all then add validated
        await db.execute(delete(NoteTag).where(NoteTag.note_id == note_id))
        if payload.tag_ids:
            res2 = await db.execute(
                select(Tag.id).where(and_(Tag.user_id == user.id, Tag.id.in_(payload.tag_ids)))
            )
            ok_ids = {r[0] for r in res2.all()}
            for tid in payload.tag_ids:
                if tid in ok_ids:
                    db.add(NoteTag(note_id=note_id, tag_id=tid))
        await db.commit()

    res3 = await db.execute(select(Note).where(Note.id == note_id))
    updated = res3.scalar_one()
    return _note_to_out(updated)


@router.delete(
    "/{note_id}",
    summary="Delete note",
    description="Delete a note.",
    operation_id="delete_note",
)
async def delete_note(
    note_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)
):
    """Delete note."""
    res = await db.execute(select(Note.id).where(Note.id == note_id, Note.user_id == user.id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Note not found")

    await db.execute(delete(Note).where(Note.id == note_id, Note.user_id == user.id))
    await db.commit()
    return {"ok": True}


@router.post(
    "/{note_id}/pin",
    response_model=NoteOut,
    summary="Toggle pin",
    description="Toggle pinned status for a note.",
    operation_id="toggle_pin",
)
async def toggle_pin(
    note_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)
) -> NoteOut:
    """Toggle pinned."""
    res = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == user.id))
    note = res.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Note not found")

    note.pinned = not note.pinned
    note.updated_at = func.now()  # type: ignore[assignment]
    await db.commit()

    res2 = await db.execute(select(Note).where(Note.id == note_id))
    note2 = res2.scalar_one()
    return _note_to_out(note2)


@router.post(
    "/{note_id}/favorite",
    response_model=NoteOut,
    summary="Toggle favorite",
    description="Toggle favorited status for a note.",
    operation_id="toggle_favorite",
)
async def toggle_favorite(
    note_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)
) -> NoteOut:
    """Toggle favorite."""
    res = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == user.id))
    note = res.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Note not found")

    note.favorited = not note.favorited
    note.updated_at = func.now()  # type: ignore[assignment]
    await db.commit()

    res2 = await db.execute(select(Note).where(Note.id == note_id))
    note2 = res2.scalar_one()
    return _note_to_out(note2)
