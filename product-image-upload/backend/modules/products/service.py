"""Your domain rules run inside the framework's database transaction."""

from io import BytesIO

from flask import current_app, has_request_context, request
from PIL import Image, ImageOps, UnidentifiedImageError

from backend.common.errors import ValidationError

MIME_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
MAX_PIXELS = 16_000_000


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


def before_save(record, actor, creating):
    """Add business rules here. Raise ValidationError to reject and roll back a save.

    Keep external side effects out of this hook; it runs before commit.
    The shared framework already validates fields and enforces ownership.

    This hook also stores the product image: the admin form posts it as a file named "image",
    and ticking "remove_image" clears the current one. The JSON API cannot upload files.
    """
    if not has_request_context():
        return None
    uploaded = request.files.get("image")
    if uploaded and uploaded.filename:
        record.image_data, record.image_type = clean_image(uploaded)
    elif request.form.get("remove_image") and not creating:
        record.image_data, record.image_type = None, None
    return None
