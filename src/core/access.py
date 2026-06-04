from sqlalchemy.orm import Session
from models import Customer, CustomerAssignment


def user_can_view_customer(user: dict, customer_id: str, db: Session) -> bool:
    """
    Returns True if the user can view this customer.

    Rules:
    - owner/admin: all customers
    - practitioner: primary practitioner_id match OR CustomerAssignment with can_view=True
    - viewer: no access to any customer records (handled at route level)
    """
    user_role = user.get("role")

    if user_role in ("owner", "admin"):
        return True

    if user_role == "practitioner":
        practitioner_id = user.get("practitioner_id")
        if not practitioner_id:
            return False

        # Check primary assignment
        customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
        if customer and str(customer.practitioner_id) == str(practitioner_id):
            return True

        # Check CustomerAssignment overrides
        assignment = db.query(CustomerAssignment).filter(
            CustomerAssignment.customer_id == customer_id,
            CustomerAssignment.practitioner_id == practitioner_id,
            CustomerAssignment.can_view == True,
        ).first()
        return assignment is not None

    return False


def get_visible_customer_ids(user: dict, db: Session) -> list[str]:
    """
    Returns a list of customer IDs the user can access.
    For owner/admin: returns empty list (meaning "all" — handled in query).
    For practitioner: returns the list of their assigned customer IDs.
    """
    user_role = user.get("role")

    if user_role in ("owner", "admin"):
        return []  # empty = "all"

    if user_role == "practitioner":
        practitioner_id = user.get("practitioner_id")
        if not practitioner_id:
            return []

        # Primary assignments
        primary_ids = [
            r[0] for r in
            db.query(Customer.id).filter(
                Customer.practitioner_id == practitioner_id,
                Customer.is_active == True,
            ).all()
        ]

        # Additional assignments
        assigned_ids = [
            r[0] for r in
            db.query(CustomerAssignment.customer_id).join(Customer).filter(
                CustomerAssignment.practitioner_id == practitioner_id,
                CustomerAssignment.can_view == True,
                Customer.is_active == True,
            ).all()
        ]

        # Union
        return list(set(primary_ids + assigned_ids))

    return []


def user_can_edit_customer(user: dict, customer_id: str, db: Session) -> bool:
    """Practitioners can edit notes on their assigned customers. Admins/owners can edit all."""
    user_role = user.get("role")
    if user_role in ("owner", "admin"):
        return True
    if user_role == "practitioner":
        return user_can_view_customer(user, customer_id, db)
    return False
