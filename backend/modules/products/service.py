"""Your domain rules run inside the framework's database transaction."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from io import BytesIO

from flask import current_app, has_request_context, request
from PIL import Image, ImageOps, UnidentifiedImageError

from backend.common.errors import ValidationError
from database import db
from database.models import CartItem, ProductImage, ProductVariation
from database.models.user import utcnow

MIME_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
MAX_PIXELS = 16_000_000
VARIATION_SLOTS = 4  # up to 4 priced options per product
LABEL_MAX = 60
PRICE_MAX = Decimal("9999999999.99")
EXTRA_PHOTOS = 5  # extra gallery photos besides the cover image


def clean_image(uploaded):
    """Verify an uploaded picture and return (bytes, mime type) ready to store.

    The image is decoded and saved again, which drops hidden metadata such as the GPS
    location a phone camera writes into photos, before the picture is shown publicly.
    """
    message = "Use a valid, non-animated PNG, JPEG, or WebP image up to 16 megapixels."
    limit = current_app.config["MAX_IMAGE_BYTES"]
    raw = uploaded.read(limit + 1)
    if not raw or len(raw) > limit:
        raise ValidationError({"image": [f"Images must be smaller than {limit // (1024 * 1024)} MiB."]})
    try:
        with Image.open(BytesIO(raw)) as image:
            fmt = image.format
            if (
                fmt not in MIME_TYPES
                or image.width * image.height > MAX_PIXELS
                or getattr(image, "n_frames", 1) != 1
            ):
                raise ValueError
            image.load()
            upright = ImageOps.exif_transpose(image)  # keep the photo's orientation without the metadata
            output = BytesIO()
            upright.save(output, format=fmt, **({"quality": 88} if fmt != "PNG" else {"optimize": True}))
    except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
        raise ValidationError({"image": [message]}) from None
    return output.getvalue(), MIME_TYPES[fmt]


def read_variations(form):
    """Read the four variation rows of the admin form: a list of (label, price) or None for an empty row."""
    rows, problems, seen = [], [], set()
    for slot in range(1, VARIATION_SLOTS + 1):
        label = " ".join(form.get(f"variation_label_{slot}", "").split())
        raw_price = form.get(f"variation_price_{slot}", "").strip()
        if not label and not raw_price:
            rows.append(None)
            continue
        if not label:
            problems.append(f"Variation {slot} needs a label.")
        elif len(label) > LABEL_MAX:
            problems.append(f"Variation {slot}: keep the label to {LABEL_MAX} characters or fewer.")
        elif label.casefold() in seen:
            problems.append(f"Variation {slot}: each variation needs a different label.")
        seen.add(label.casefold())
        try:
            price = Decimal(raw_price)
            if not price.is_finite() or price < 0 or price > PRICE_MAX:
                raise InvalidOperation
            if price != price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP):
                problems.append(f"Variation {slot}: use at most 2 decimal places for the price.")
            price = price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except InvalidOperation:
            problems.append(f"Variation {slot} needs a price of 0 or more, such as 270 or 270.00.")
            price = None
        rows.append((label, price))
    return rows, problems


def save_variations(record, rows):
    """Update the four slots in place, so cart items pointing at a variation keep pointing at it."""
    current = {v.position: v for v in record.variations}
    for slot, row in enumerate(rows, start=1):
        existing = current.get(slot)
        if row is None:
            if existing is not None:
                # Shoppers' carts cannot hold an option that no longer exists.
                db.session.execute(db.delete(CartItem).where(CartItem.variation_id == existing.id))
                record.variations.remove(existing)
        elif existing is not None:
            existing.label, existing.price = row
        else:
            record.variations.append(ProductVariation(position=slot, label=row[0], price=row[1]))


def read_photos(record, creating):
    """Check the "More photos" upload and the ticked "Remove" boxes. Returns (new photos, removed ids, problems)."""
    uploads = [u for u in request.files.getlist("more_photos") if u and u.filename]
    removed = {int(v) for v in request.form.getlist("remove_photo") if v.isdigit()}
    kept = 0 if creating else len([img for img in record.images if img.id not in removed])
    if kept + len(uploads) > EXTRA_PHOTOS:
        room = max(EXTRA_PHOTOS - kept, 0)
        return [], removed, [f"A product can have {EXTRA_PHOTOS} extra photos; you can add {room} more."]
    photos, problems = [], []
    for upload in uploads:
        try:
            photos.append(clean_image(upload))
        except ValidationError as error:
            problems.extend(f"{upload.filename}: {message}" for message in error.errors["image"])
    return photos, removed, problems


def save_photos(record, photos, removed):
    for image in [img for img in record.images if img.id in removed]:
        record.images.remove(image)
    for data, kind in photos:
        record.images.append(ProductImage(position=len(record.images) + 1, image_data=data, image_type=kind))
    for position, image in enumerate(record.images, start=1):
        image.position = position


def before_save(record, actor, creating):
    """Add business rules here. Raise ValidationError to reject and roll back a save.

    Keep external side effects out of this hook; it runs before commit.
    The shared framework already validates fields and enforces ownership.

    This hook also stores the product image: the admin form posts it as a file named "image",
    and ticking "remove_image" clears the current one. The same form posts the four variation rows
    (variation_label_N / variation_price_N) and extra photos ("more_photos", "remove_photo").
    The JSON API cannot upload files and never changes variations.
    """
    if not has_request_context():
        return None
    uploaded = request.files.get("image")
    if uploaded and uploaded.filename:
        record.image_data, record.image_type = clean_image(uploaded)
    elif request.form.get("remove_image") and not creating:
        record.image_data, record.image_type = None, None

    # Variations and extra photos only come from the admin form; the JSON API sends neither,
    # so its edits leave them untouched.
    has_options = "variation_label_1" in request.form
    rows, problems = read_variations(request.form) if has_options else (None, [])
    photos, removed, photo_problems = read_photos(record, creating)
    if problems or photo_problems:
        errors = {}
        if problems:
            errors["variations"] = problems
        if photo_problems:
            errors["more_photos"] = photo_problems
        raise ValidationError(errors)
    if has_options:
        save_variations(record, rows)
    if photos or removed:
        save_photos(record, photos, removed)
    if has_options or photos or removed:
        record.updated_at = utcnow()  # saving only variations or photos still counts as an edit
    return None
    rows, problems = read_variations(request.form)
    photos, removed, photo_problems = read_photos(record, creating)
    if problems or photo_problems:
        errors = {}
        if problems:
            errors["variations"] = problems
        if photo_problems:
            errors["more_photos"] = photo_problems
        raise ValidationError(errors)
    save_variations(record, rows)
    save_photos(record, photos, removed)
    record.updated_at = utcnow()  # saving only variations or photos still counts as an edit
    return None
