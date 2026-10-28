from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional


class CheckoutForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(check_deliverability=False), Length(max=254)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    address = StringField("Address", validators=[DataRequired(), Length(max=200)])
    city = StringField("City", validators=[DataRequired(), Length(max=80)])
    notes = TextAreaField("Order notes", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Place order")


class QuantityForm(FlaskForm):
    """Add to cart and cart quantity changes. CSRF is included."""

    quantity = IntegerField("Quantity", default=1, validators=[DataRequired(), NumberRange(min=1, max=99)])
    submit = SubmitField("Add to cart")
