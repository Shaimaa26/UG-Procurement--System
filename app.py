import streamlit as st
import pandas as pd
import os
from datetime import date

st.set_page_config(
    page_title="UG Procurement System",
    page_icon="📦",
    layout="wide"
)

st.title("UG Procurement System")
st.caption("United Group | Procurement & Technical Supplies")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "Suppliers": f"{DATA_DIR}/suppliers.csv",
    "Products": f"{DATA_DIR}/products.csv",
    "Purchase Orders": f"{DATA_DIR}/purchase_orders.csv",
}

COLUMNS = {
    "Suppliers": [
        "Supplier ID", "Supplier Name", "Country",
        "Contact Person", "Email", "Phone",
        "Payment Terms", "Notes"
    ],
    "Products": [
        "Product ID", "Product Name", "Category",
        "Manufacturer", "Model", "Supplier",
        "Unit", "Datasheet", "Notes"
    ],
    "Purchase Orders": [
        "PO Number", "Project", "Supplier",
        "Order Date", "Product", "Quantity",
        "Unit Price", "Currency", "Status",
        "Payment Status", "Shipping Status", "Notes"
    ],
}


def load_data(name):
    path = FILES[name]

    if os.path.exists(path):
        return pd.read_csv(path).fillna("")

    return pd.DataFrame(columns=COLUMNS[name])


def save_data(name, df):
    df.to_csv(FILES[name], index=False)


# Sidebar navigation
page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Suppliers",
        "Products & Sensors",
        "Purchase Orders",
    ]
)

# Load data
suppliers = load_data("Suppliers")
products = load_data("Products")
orders = load_data("Purchase Orders")


if page == "Dashboard":

    st.header("Dashboard")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Suppliers", len(suppliers))
    c2.metric("Products & Sensors", len(products))
    c3.metric("Purchase Orders", len(orders))

    pending = (
        orders["Status"].astype(str).str.lower()
        .isin(["pending", "in progress"])
        .sum()
        if not orders.empty else 0
    )

    c4.metric("Pending Orders", int(pending))

    st.subheader("Recent Purchase Orders")

    if orders.empty:
        st.info("No purchase orders registered yet.")
    else:
        st.dataframe(
            orders.tail(10),
            use_container_width=True,
            hide_index=True
        )


elif page == "Suppliers":

    st.header("Suppliers Database")

    with st.form("supplier_form", clear_on_submit=True):

        name = st.text_input("Supplier Name")
        country = st.text_input("Country")
        contact = st.text_input("Contact Person")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        payment = st.text_input("Payment Terms")
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Add Supplier")

        if submitted:

            if not name.strip():
                st.error("Supplier Name is required.")

            elif (
                not suppliers.empty
                and suppliers["Supplier Name"].astype(str)
                .str.strip().str.lower()
                .eq(name.strip().lower()).any()
            ):
                st.error("This supplier already exists.")

            else:
                new_id = f"SUP-{len(suppliers) + 1:04d}"

                new_row = pd.DataFrame([{
                    "Supplier ID": new_id,
                    "Supplier Name": name.strip(),
                    "Country": country,
                    "Contact Person": contact,
                    "Email": email,
                    "Phone": phone,
                    "Payment Terms": payment,
                    "Notes": notes,
                }])

                suppliers = pd.concat(
                    [suppliers, new_row],
                    ignore_index=True
                )

                save_data("Suppliers", suppliers)
                st.success("Supplier added successfully.")
                st.rerun()

    st.subheader("Registered Suppliers")

    search = st.text_input("Search Suppliers")

    if search:
        suppliers = suppliers[
            suppliers.astype(str).apply(
                lambda col: col.str.contains(
                    search, case=False, na=False, regex=False
                )
            ).any(axis=1)
        ]

    st.dataframe(
        suppliers,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Export Suppliers to CSV",
        suppliers.to_csv(index=False).encode("utf-8-sig"),
        file_name="suppliers.csv",
        mime="text/csv"
    )


elif page == "Products & Sensors":

    st.header("Products & Sensors Database")

    with st.form("product_form", clear_on_submit=True):

        product_name = st.text_input("Product Name")
        category = st.selectbox(
            "Category",
            [
                "Geotechnical Sensor",
                "Structural Sensor",
                "Data Acquisition System",
                "Gateway / Communication",
                "Software",
                "Electronic Component",
                "Accessory",
                "Other",
            ]
        )

        manufacturer = st.text_input("Manufacturer")
        model = st.text_input("Model")
        supplier = st.selectbox(
            "Supplier",
            [""] + sorted(
                suppliers["Supplier Name"].astype(str).tolist()
            )
        )

        unit = st.selectbox(
            "Unit",
            ["pcs", "set", "m", "lot", "other"]
        )

        datasheet = st.text_input("Datasheet URL")
        notes = st.text_area("Technical Notes")

        submitted = st.form_submit_button("Add Product")

        if submitted:

            if not product_name.strip():
                st.error("Product Name is required.")

            else:
                new_id = f"PRD-{len(products) + 1:04d}"

                new_row = pd.DataFrame([{
                    "Product ID": new_id,
                    "Product Name": product_name.strip(),
                    "Category": category,
                    "Manufacturer": manufacturer,
                    "Model": model,
                    "Supplier": supplier,
                    "Unit": unit,
                    "Datasheet": datasheet,
                    "Notes": notes,
                }])

                products = pd.concat(
                    [products, new_row],
                    ignore_index=True
                )

                save_data("Products", products)
                st.success("Product added successfully.")
                st.rerun()

    st.subheader("Registered Products")

    st.dataframe(
        products,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Export Products to CSV",
        products.to_csv(index=False).encode("utf-8-sig"),
        file_name="products.csv",
        mime="text/csv"
    )


elif page == "Purchase Orders":

    st.header("Purchase Orders")

    with st.form("po_form", clear_on_submit=True):

        po_number = st.text_input("PO Number")
        project = st.text_input("Project Name")

        supplier = st.selectbox(
            "Supplier",
            [""] + sorted(
                suppliers["Supplier Name"].astype(str).tolist()
            )
        )

        product = st.selectbox(
            "Product",
            [""] + sorted(
                products["Product Name"].astype(str).tolist()
            )
        )

        order_date = st.date_input("Order Date", value=date.today())
        quantity = st.number_input(
            "Quantity", min_value=0.0, value=1.0
        )
        unit_price = st.number_input(
            "Unit Price", min_value=0.0, value=0.0
        )

        currency = st.selectbox(
            "Currency", ["USD", "EUR", "SAR", "EGP", "GBP"]
        )

        status = st.selectbox(
            "Order Status",
            [
                "Draft",
                "Pending Approval",
                "Approved",
                "Ordered",
                "Partially Received",
                "Received",
                "Cancelled",
            ]
        )

        payment_status = st.selectbox(
            "Payment Status",
            ["Not Paid", "Partially Paid", "Paid"]
        )

        shipping_status = st.selectbox(
            "Shipping Status",
            [
                "Not Shipped",
                "In Transit",
                "Delivered",
                "Delayed",
            ]
        )

        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Add Purchase Order")

        if submitted:

            if not po_number.strip():
                st.error("PO Number is required.")

            elif (
                not orders.empty
                and orders["PO Number"].astype(str)
                .str.strip().str.lower()
                .eq(po_number.strip().lower()).any()
            ):
                st.error("This PO Number already exists.")

            else:
                new_row = pd.DataFrame([{
                    "PO Number": po_number.strip(),
                    "Project": project,
                    "Supplier": supplier,
                    "Order Date": str(order_date),
                    "Product": product,
                    "Quantity": quantity,
                    "Unit Price": unit_price,
                    "Currency": currency,
                    "Status": status,
                    "Payment Status": payment_status,
                    "Shipping Status": shipping_status,
                    "Notes": notes,
                }])

                orders = pd.concat(
                    [orders, new_row],
                    ignore_index=True
                )

                save_data("Purchase Orders", orders)
                st.success("Purchase Order added successfully.")
                st.rerun()

    st.subheader("Purchase Orders Register")

    if orders.empty:
        st.info("No purchase orders registered yet.")
    else:
        st.dataframe(
            orders,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Export Purchase Orders to CSV",
            orders.to_csv(index=False).encode("utf-8-sig"),
            file_name="purchase_orders.csv",
            mime="text/csv"
        )
