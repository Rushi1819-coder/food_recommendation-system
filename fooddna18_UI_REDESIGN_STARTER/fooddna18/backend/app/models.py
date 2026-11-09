"""
FoodDNA — Updated models with:
  - timezone-safe utcnow() (fix 1.1)
  - users.password_changed_at column (fix 1.8)
  - orders.idempotency_key column (fix 1.3)
  - feedback.order_id + unique constraint (fix 1.13)
  - UserAddress model (Stage 5)
"""

from datetime import datetime, timezone

from .extensions import db
from .utils.timeutil import utcnow


class TimestampMixin:
    """
    Adds created_at and updated_at fields to models.
    Uses timezone-aware utcnow() to avoid the deprecated datetime.utcnow().
    """

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Role(TimestampMixin, db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    users = db.relationship(
        "User",
        back_populates="role",
        lazy=True
    )


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)

    full_name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role_id = db.Column(
        db.Integer,
        db.ForeignKey("roles.id"),
        nullable=False,
        index=True
    )

    account_status = db.Column(
        db.String(30),
        nullable=False,
        default="active"
    )

    approval_status = db.Column(
        db.String(30),
        nullable=False,
        default="not_required"
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    last_login_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # Fix 1.8: track when the password was last changed so that old
    # sessions stored before the change are automatically invalidated.
    password_changed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    role = db.relationship(
        "Role",
        back_populates="users"
    )


class Restaurant(TimestampMixin, db.Model):
    __tablename__ = "restaurants"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    address = db.Column(
        db.Text,
        nullable=False
    )

    phone = db.Column(
        db.String(20),
        nullable=True
    )

    email = db.Column(
        db.String(255),
        nullable=True
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="pending"
    )

    capacity_status = db.Column(
        db.String(30),
        nullable=False,
        default="normal"
    )


class RestaurantAdmin(TimestampMixin, db.Model):
    __tablename__ = "restaurant_admins"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    restaurant_id = db.Column(
        db.BigInteger,
        db.ForeignKey("restaurants.id"),
        nullable=True
    )


class Staff(TimestampMixin, db.Model):
    __tablename__ = "staff"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    restaurant_id = db.Column(
        db.BigInteger,
        db.ForeignKey("restaurants.id"),
        nullable=False
    )

    designation = db.Column(
        db.String(80),
        nullable=False,
        default="Chef/Staff"
    )


class DeliveryPartner(TimestampMixin, db.Model):
    __tablename__ = "delivery_partners"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    phone = db.Column(
        db.String(20),
        nullable=True
    )

    availability_status = db.Column(
        db.String(30),
        nullable=False,
        default="available"
    )


class FoodCategory(TimestampMixin, db.Model):
    __tablename__ = "food_categories"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    description = db.Column(
        db.String(255),
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )


class Meal(TimestampMixin, db.Model):
    __tablename__ = "meals"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    restaurant_id = db.Column(
        db.BigInteger,
        db.ForeignKey("restaurants.id"),
        nullable=False,
        index=True
    )

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("food_categories.id"),
        nullable=False,
        index=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    price = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    cuisine = db.Column(
        db.String(80),
        nullable=False
    )

    meal_type = db.Column(
        db.String(50),
        nullable=False
    )

    taste = db.Column(
        db.String(50),
        nullable=False
    )

    spice_level = db.Column(
        db.String(30),
        nullable=False
    )

    portion_size = db.Column(
        db.String(30),
        nullable=False
    )

    dietary_preference = db.Column(
        db.String(80),
        nullable=True
    )

    food_type = db.Column(
        db.String(30),
        nullable=False
    )

    image_url = db.Column(
        db.String(500),
        nullable=True
    )

    is_available = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    # is_archived: True means the meal is soft-deleted (hidden from public
    # and restaurant admin menu) but preserved for past order history.
    is_archived = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    # Explicit relationships required by cart, order and recommendation services.
    restaurant = db.relationship("Restaurant", lazy="joined")
    category = db.relationship("FoodCategory", lazy="joined")


class UserPreference(TimestampMixin, db.Model):
    __tablename__ = "user_preferences"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    cuisine = db.Column(db.String(80), nullable=True)
    meal_type = db.Column(db.String(50), nullable=True)
    taste = db.Column(db.String(50), nullable=True)
    spice_level = db.Column(db.String(30), nullable=True)
    budget = db.Column(db.Numeric(10, 2), nullable=True)
    portion_size = db.Column(db.String(30), nullable=True)
    food_type = db.Column(db.String(30), nullable=True)
    dietary_preference = db.Column(db.String(80), nullable=True)


class Recommendation(TimestampMixin, db.Model):
    __tablename__ = "recommendations"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    meal_id = db.Column(
        db.BigInteger,
        db.ForeignKey("meals.id"),
        nullable=False
    )

    score = db.Column(
        db.Numeric(6, 2),
        nullable=False
    )

    reason = db.Column(
        db.Text,
        nullable=True
    )

    generated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow
    )


class FoodMemory(TimestampMixin, db.Model):
    __tablename__ = "food_memory"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    meal_id = db.Column(
        db.BigInteger,
        db.ForeignKey("meals.id"),
        nullable=True
    )

    restaurant_id = db.Column(
        db.BigInteger,
        db.ForeignKey("restaurants.id"),
        nullable=True
    )

    event_type = db.Column(
        db.String(50),
        nullable=False
    )

    event_data = db.Column(
        db.JSON,
        nullable=True
    )


class Cart(TimestampMixin, db.Model):
    __tablename__ = "carts"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="active"
    )

    items = db.relationship(
        "CartItem",
        backref="cart",
        lazy="select",
        cascade="all, delete-orphan"
    )


class CartItem(TimestampMixin, db.Model):
    __tablename__ = "cart_items"
    __table_args__ = (
        db.UniqueConstraint("cart_id", "meal_id", name="uq_cart_items_cart_meal"),
    )

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    cart_id = db.Column(
        db.BigInteger,
        db.ForeignKey("carts.id"),
        nullable=False
    )

    meal_id = db.Column(
        db.BigInteger,
        db.ForeignKey("meals.id"),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    meal = db.relationship(
        "Meal",
        lazy="joined"
    )


class Order(TimestampMixin, db.Model):
    __tablename__ = "orders"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    restaurant_id = db.Column(
        db.BigInteger,
        db.ForeignKey("restaurants.id"),
        nullable=False,
        index=True
    )

    # Phase 9/10 additions: delivery assignment and optional restaurant offer.
    delivery_partner_id = db.Column(
        db.BigInteger, db.ForeignKey("delivery_partners.id"), nullable=True, index=True
    )
    offer_id = db.Column(
        db.BigInteger, db.ForeignKey("offers.id"), nullable=True
    )
    discount_amount = db.Column(
        db.Numeric(10, 2), nullable=False, default=0
    )

    # Fix 1.3: idempotency key prevents duplicate orders on double-click / retry.
    # Scoped per user: UNIQUE(user_id, idempotency_key) enforced in migration.
    idempotency_key = db.Column(
        db.String(64),
        nullable=True
    )

    subtotal = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    delivery_fee = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0
    )

    total_amount = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    order_status = db.Column(
        db.String(40),
        nullable=False,
        default="pending"
    )

    delivery_address = db.Column(
        db.Text,
        nullable=False
    )

    placed_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow
    )

    restaurant = db.relationship(
        "Restaurant",
        lazy="joined"
    )

    items = db.relationship(
        "OrderItem",
        backref="order",
        lazy="select",
        cascade="all, delete-orphan"
    )

    status_history = db.relationship(
        "OrderStatusHistory",
        backref="order",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at.asc()"
    )

    payment = db.relationship(
        "Payment",
        backref="order",
        uselist=False,
        lazy="joined"
    )

    delivery_partner = db.relationship(
        "DeliveryPartner",
        foreign_keys=[delivery_partner_id],
        lazy="joined"
    )


class OrderItem(TimestampMixin, db.Model):
    __tablename__ = "order_items"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    order_id = db.Column(
        db.BigInteger,
        db.ForeignKey("orders.id"),
        nullable=False
    )

    meal_id = db.Column(
        db.BigInteger,
        db.ForeignKey("meals.id"),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    unit_price = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    meal = db.relationship(
        "Meal",
        lazy="joined"
    )


class OrderStatusHistory(TimestampMixin, db.Model):
    __tablename__ = "order_status_history"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    order_id = db.Column(
        db.BigInteger,
        db.ForeignKey("orders.id"),
        nullable=False,
        index=True
    )

    status = db.Column(
        db.String(40),
        nullable=False
    )

    changed_by = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=True
    )

    note = db.Column(
        db.String(255),
        nullable=True
    )


class Payment(TimestampMixin, db.Model):
    __tablename__ = "payments"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    order_id = db.Column(
        db.BigInteger,
        db.ForeignKey("orders.id"),
        nullable=False,
        unique=True
    )

    customer_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=False
    )

    amount = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    payment_method = db.Column(
        db.String(40),
        nullable=False
    )

    transaction_id = db.Column(
        db.String(150),
        nullable=True
    )

    payment_status = db.Column(
        db.String(40),
        nullable=False
    )

    payment_date = db.Column(
        db.DateTime,
        nullable=True
    )


class Feedback(TimestampMixin, db.Model):
    __tablename__ = "feedback"
    __table_args__ = (
        # Fix 1.13: one review per meal per delivered order (not just per meal ever)
        db.UniqueConstraint(
            "customer_id", "order_id", "food_id",
            name="uq_feedback_customer_order_food"
        ),
    )

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    customer_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # Fix 1.13: order_id allows the unique-per-order constraint.
    order_id = db.Column(
        db.BigInteger,
        db.ForeignKey("orders.id"),
        nullable=True  # nullable for backfill safety; enforced in application logic
    )

    food_id = db.Column(
        db.BigInteger,
        db.ForeignKey("meals.id"),
        nullable=False
    )

    restaurant_id = db.Column(
        db.BigInteger,
        db.ForeignKey("restaurants.id"),
        nullable=False
    )

    rating = db.Column(
        db.Integer,
        nullable=False
    )

    comment = db.Column(
        db.Text,
        nullable=True
    )


class Offer(TimestampMixin, db.Model):
    __tablename__ = "offers"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    restaurant_id = db.Column(
        db.BigInteger,
        db.ForeignKey("restaurants.id"),
        nullable=False
    )

    title = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    discount_percent = db.Column(
        db.Numeric(5, 2),
        nullable=False
    )

    start_date = db.Column(
        db.Date,
        nullable=False
    )

    end_date = db.Column(
        db.Date,
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )


class RestaurantCapacity(TimestampMixin, db.Model):
    __tablename__ = "restaurant_capacity"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    restaurant_id = db.Column(
        db.BigInteger,
        db.ForeignKey("restaurants.id"),
        nullable=False,
        unique=True
    )

    active_orders = db.Column(db.Integer, nullable=False, default=0)
    pending_orders = db.Column(db.Integer, nullable=False, default=0)
    available_staff = db.Column(db.Integer, nullable=False, default=0)
    preparation_workload = db.Column(db.Integer, nullable=False, default=0)
    estimated_preparation_minutes = db.Column(db.Integer, nullable=False, default=30)
    available_delivery_partners = db.Column(db.Integer, nullable=False, default=0)
    estimated_delivery_minutes = db.Column(db.Integer, nullable=False, default=30)


class Notification(TimestampMixin, db.Model):
    __tablename__ = "notifications"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)


class AdminApproval(TimestampMixin, db.Model):
    __tablename__ = "admin_approvals"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=False
    )

    restaurant_id = db.Column(
        db.BigInteger,
        db.ForeignKey("restaurants.id"),
        nullable=True
    )

    approval_type = db.Column(db.String(50), nullable=False)

    status = db.Column(
        db.String(30),
        nullable=False,
        default="pending"
    )

    reviewed_by = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=True
    )

    reviewed_at = db.Column(db.DateTime, nullable=True)

    remarks = db.Column(db.Text, nullable=True)


class SystemActivity(TimestampMixin, db.Model):
    __tablename__ = "system_activity"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=True
    )

    action = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    token_hash = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        index=True
    )

    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp()
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )


class UserAddress(TimestampMixin, db.Model):
    """Stage 5: saved customer delivery addresses (max 10 per user)."""
    __tablename__ = "user_addresses"

    id = db.Column(
        db.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    label = db.Column(
        db.String(80),
        nullable=False,
        default="Home"
    )

    full_address = db.Column(
        db.Text,
        nullable=False
    )

    is_default = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    def __init__(
        self,
        user_id=None,
        label="Home",
        full_address="",
        is_default=False,
        **kwargs
    ):
        self.user_id = user_id
        self.label = label
        self.full_address = full_address
        self.is_default = is_default
        for k, v in kwargs.items():
            setattr(self, k, v)

