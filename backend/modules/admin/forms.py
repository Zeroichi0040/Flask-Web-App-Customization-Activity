from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired

from database.models.orders import ORDER_STATUSES


class OrderStatusForm(FlaskForm):
    status = SelectField("Order status", choices=ORDER_STATUSES, validators=[DataRequired()])
    submit = SubmitField("Update status")
