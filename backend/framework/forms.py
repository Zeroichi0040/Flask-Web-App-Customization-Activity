"""Build accessible server forms from the same fields that define the JSON API."""

from decimal import Decimal

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.fields import SelectChoice
from wtforms.validators import InputRequired, Length, Optional


def form_class(resource):
    fields = {"version": HiddenField(), "submit": SubmitField(f"Save {resource.singular.lower()}")}
    for definition in resource.fields:
        validators = [InputRequired()] if definition.required and definition.kind != "boolean" else [Optional()]
        options = {"validators": validators, "default": definition.default, "description": definition.help}
        kind = definition.kind
        if kind in {"text", "textarea", "email", "url", "choice"}:
            validators.append(Length(max=definition.max_length))
        if kind == "choice":
            options["choices"] = [SelectChoice(*choice) for choice in definition.choices]
        if kind == "image":
            # The file itself is checked and stored by the resource's on_save hook.
            validators.append(FileAllowed(["png", "jpg", "jpeg", "webp"], "Choose a PNG, JPEG, or WebP image."))
        if kind == "decimal":
            options["places"] = 2
            # JSON uses decimal strings; WTForms must receive a numeric default.
            default = definition.default
            options["default"] = None if default is None or default == "" else Decimal(str(default))
        cls = {
            "text": StringField,
            "textarea": TextAreaField,
            "email": StringField,
            "url": StringField,
            "integer": IntegerField,
            "decimal": DecimalField,
            "boolean": BooleanField,
            "date": DateField,
            "choice": SelectField,
            "image": FileField,
        }[kind]
        fields[definition.name] = cls(definition.label, **options)
    return type(resource.key.title() + "Form", (FlaskForm,), fields)
