class Selectors:
    # Product listing
    PRODUCT_LINKS  = "a.product-thumbnail, a.thumbnail.product-thumbnail, .product-miniature a.thumbnail"
    COLLECTION_ALL = "/2-inicio"

    # Product page - variants
    VARIANT_RADIO  = "ul.product-variants-item li input[type='radio']"

    # Product page - add to cart
    ADD_TO_CART_BTN = "button.add-to-cart"

    # Cart page - proceed to checkout
    CART_PROCEED_CHECKOUT = ".cart-detailed-actions a.btn, a[href*='pedido'], a[href*='order']"

    # ── Step 1: DATOS PERSONALES ────────────────────────────────────────────
    # "Pedir como invitado" is already the default tab — no button to click
    GUEST_GENDER_MR     = "input[name='id_gender'][value='1']"   # Sr.
    GUEST_GENDER_MRS    = "input[name='id_gender'][value='2']"   # Sra.
    GUEST_FIRSTNAME     = "input[name='firstname']"
    GUEST_LASTNAME      = "input[name='lastname']"
    GUEST_EMAIL         = "input[name='email']"
    GUEST_TERMS         = "input[name='psgdpr']"                 # "Acepto condiciones"
    GUEST_CONTINUE      = "button.continue[name='continue'], footer button.continue, form button[type='submit']"

    # ── Step 2: DIRECCIONES ─────────────────────────────────────────────────
    ADDRESS_ALIAS       = "input[name='alias']"
    ADDRESS_FIRSTNAME   = "input[name='firstname']"
    ADDRESS_LASTNAME    = "input[name='lastname']"
    ADDRESS_ADDRESS1    = "input[name='address1']"
    ADDRESS_POSTCODE    = "input[name='postcode']"
    ADDRESS_CITY        = "input[name='city']"
    ADDRESS_PHONE       = "input[name='phone']"
    ADDRESS_CONTINUE    = "button[name='confirm-addresses'], button.continue[type='submit']"

    # ── Step 3: MÉTODO DE ENVÍO ─────────────────────────────────────────────
    DELIVERY_CONTINUE   = "button[name='confirmDeliveryOption']"

    # ── Step 4: PAGO ────────────────────────────────────────────────────────
    PAYMENT_OPTION      = "input.payment-option"
    PAYMENT_TERMS       = "input[name='conditions_to_approve[terms-and-conditions]']"
    PAYMENT_PLACE_ORDER = "#payment-confirmation button[type='submit']"

    # Order confirmation
    ORDER_CONFIRMATION  = "div#order-confirmation, .order-confirmation-table"
