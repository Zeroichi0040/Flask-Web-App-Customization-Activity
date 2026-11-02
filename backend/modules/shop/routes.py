"""Storefront: public product pages, cart, and persisted checkout orders."""

from io import BytesIO

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from backend.common.forms import ActionForm
from backend.modules.shop.forms import CheckoutForm, QuantityForm
from database import db
from database.models import CartItem, Order, OrderItem, ProductImage, ProductsRecord

bp = Blueprint("shop", __name__)


@bp.app_context_processor
def cart_values():
    """Number of items in the signed-in user's cart, shown next to the Cart links."""
    if not current_user.is_authenticated:
        return {"cart_count": 0}
    count = db.session.scalar(
        db.select(db.func.coalesce(db.func.sum(CartItem.quantity), 0)).where(CartItem.user_id == current_user.id)
    )
    return {"cart_count": int(count)}


def cart_lines():
    items = db.session.scalars(
        db.select(CartItem).where(CartItem.user_id == current_user.id).order_by(CartItem.id)
    ).all()
    lines = []
    for item in items:
        unit_price = item.variation.price if item.variation else item.product.price
        lines.append({
            "item": item, "product": item.product, "variation": item.variation,
            "unit_price": unit_price, "subtotal": unit_price * item.quantity,
        })
    return lines, sum((line["subtotal"] for line in lines), 0)


@bp.get("/products")
def products():
    records = db.session.scalars(db.select(ProductsRecord).order_by(ProductsRecord.name, ProductsRecord.id)).all()
    return render_template("shop/products.html", products=records)


@bp.get("/products/<int:product_id>")
def product(product_id):
    record = db.get_or_404(ProductsRecord, product_id)
    gallery = []
    if record.has_image:
        gallery.append(url_for("shop.product_image", product_id=record.id, v=record.version))
    gallery += [url_for("shop.product_photo", product_id=record.id, image_id=image.id) for image in record.images]
    return render_template("shop/product.html", product=record, form=QuantityForm(), gallery=gallery)


@bp.get("/products/<int:product_id>/image")
def product_image(product_id):
    record = db.get_or_404(ProductsRecord, product_id)
    if not record.has_image:
        abort(404)
    response = send_file(BytesIO(record.image_data), mimetype=record.image_type)
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@bp.get("/products/<int:product_id>/photos/<int:image_id>")
def product_photo(product_id, image_id):
    image = db.first_or_404(
        db.select(ProductImage).where(ProductImage.id == image_id, ProductImage.product_id == product_id)
    )
    response = send_file(BytesIO(image.image_data), mimetype=image.image_type)
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@bp.post("/cart/add/<int:product_id>")
@login_required
def cart_add(product_id):
    record = db.get_or_404(ProductsRecord, product_id)
    form = QuantityForm()
    if not form.validate_on_submit():
        flash("Choose a quantity from 1 to 99.", "error")
        return redirect(url_for("shop.product", product_id=record.id), code=303)
    variation = None
    if record.variations:
        variation = next((v for v in record.variations if v.id == form.variation_id.data), None)
        if variation is None:
            flash("Choose an option first.", "error")
            return redirect(url_for("shop.product", product_id=record.id), code=303)
    same_option = CartItem.variation_id.is_(None) if variation is None else CartItem.variation_id == variation.id
    item = db.session.scalar(db.select(CartItem).where(
        CartItem.user_id == current_user.id, CartItem.product_id == record.id, same_option
    ))
    if item:
        item.quantity = min(item.quantity + form.quantity.data, 99)
    else:
        db.session.add(CartItem(
            user_id=current_user.id, product_id=record.id,
            variation_id=variation.id if variation else None, quantity=form.quantity.data,
        ))
    db.session.commit()
    name = f"{record.name} ({variation.label})" if variation else record.name
    flash(f"Added {name} to your cart.", "success")
    return redirect(url_for("shop.product", product_id=record.id), code=303)


@bp.get("/cart")
@login_required
def cart():
    lines, total = cart_lines()
    return render_template("shop/cart.html", lines=lines, total=total, action_form=ActionForm())


def own_item(item_id):
    return db.first_or_404(db.select(CartItem).where(
        CartItem.id == item_id, CartItem.user_id == current_user.id
    ))


@bp.post("/cart/items/<int:item_id>/update")
@login_required
def cart_update(item_id):
    item = own_item(item_id)
    form = QuantityForm()
    if form.validate_on_submit():
        item.quantity = form.quantity.data
        db.session.commit()
    else:
        flash("Choose a quantity from 1 to 99.", "error")
    return redirect(url_for("shop.cart"), code=303)


@bp.post("/cart/items/<int:item_id>/remove")
@login_required
def cart_remove(item_id):
    item = own_item(item_id)
    if ActionForm().validate_on_submit():
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("shop.cart"), code=303)


@bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    lines, total = cart_lines()
    if not lines:
        flash("Your cart is empty. Add a product first.", "error")
        return redirect(url_for("shop.products"), code=303)
    form = CheckoutForm()
    if request.method == "GET":
        form.full_name.data = current_user.display_name
        form.email.data = current_user.email
    if form.validate_on_submit():
        order = Order(
            user_id=current_user.id,
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip(),
            phone=(form.phone.data or "").strip(),
            address=form.address.data.strip(),
            city=form.city.data.strip(),
            notes=(form.notes.data or "").strip(),
            total=total,
        )
        for line in lines:
            item = line["item"]
            order.items.append(OrderItem(
                product_id=item.product_id,
                variation_id=item.variation_id,
                product_name=line["product"].name,
                variation_label=line["variation"].label if line["variation"] else "",
                unit_price=line["unit_price"],
                quantity=item.quantity,
                subtotal=line["subtotal"],
            ))
        db.session.add(order)
        for line in lines:
            db.session.delete(line["item"])
        db.session.commit()
        flash(f"Order #{order.id} placed successfully. Payment is not collected by this demo.", "success")
        return redirect(url_for("shop.products"), code=303)
    return render_template("shop/checkout.html", form=form, lines=lines, total=total), (
        422 if request.method == "POST" else 200
    )
