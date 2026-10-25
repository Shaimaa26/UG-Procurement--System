import io
import uuid
from datetime import date

import pandas as pd
import streamlit as st
from supabase import create_client

st.set_page_config(
    page_title="UG Procurement System",
    page_icon="📦",
    layout="wide",
)

BUCKET = "procurement-documents"

TABLES = {
    "Suppliers": "suppliers",
    "Projects": "projects",
    "Products": "products",
    "Inventory": "inventory",
    "Purchase Orders": "purchase_orders",
    "PO Items": "purchase_order_items",
    "Attachments": "attachments",
}

IMPORT_COLUMNS = {
    "suppliers": [
        "supplier_name", "country", "contact_person",
        "email", "phone", "payment_terms", "notes",
    ],
    "projects": [
        "project_name", "customer", "location",
        "status", "notes",
    ],
    "products": [
        "product_name", "category", "manufacturer",
        "model", "supplier_id", "unit", "datasheet_url",
        "notes",
    ],
    "inventory": [
        "product_id", "serial_number", "quantity",
        "stock_classification", "project_id", "supplier_id",
        "po_number", "receipt_date", "location",
        "condition", "notes",
    ],
    "purchase_orders": [
        "po_number", "project_id", "supplier_id",
        "order_date", "currency", "status",
        "payment_status", "shipping_status", "notes",
    ],
    "purchase_order_items": [
        "purchase_order_id", "product_id",
        "quantity", "unit_price", "notes",
    ],
}

# -------------------------
# Access protection
# -------------------------

if "APP_PASSWORD" not in st.secrets:
    st.error("APP_PASSWORD is missing from Streamlit Secrets.")
    st.stop()

if not st.session_state.get("authenticated", False):
    st.title("UG Procurement System")
    password = st.text_input(
        "Enter application password",
        type="password",
    )

    if st.button("Login"):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    st.stop()

# -------------------------
# Supabase connection
# -------------------------

try:
    supabase = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )
except Exception as exc:
    st.error(f"Supabase connection error: {exc}")
    st.stop()


def load_table(table):
    try:
        response = (
            supabase.table(table)
            .select("*")
            .limit(1000)
            .execute()
        )
        return pd.DataFrame(response.data or [])
    except Exception as exc:
        st.error(f"Could not load {table}: {exc}")
        return pd.DataFrame()


def insert_row(table, data):
    try:
        response = (
            supabase.table(table)
            .insert(data)
            .execute()
        )
        return response.data
    except Exception as exc:
        st.error(f"Could not save record: {exc}")
        return None


def clean_value(value):
    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, str):
        value = value.strip()
        return value if value else None

    return value


def show_table(table, title):
    st.subheader(title)
    df = load_table(table)

    if df.empty:
        st.info("No records found.")
    else:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            f"Export {title} to CSV",
            df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{table}.csv",
            mime="text/csv",
        )


def options_with_names(df, name_column):
    if df.empty or "id" not in df.columns:
        return {}

    return {
        f"{row[name_column]} (ID: {row['id']})": int(row["id"])
        for _, row in df.iterrows()
        if pd.notna(row.get(name_column))
    }


# -------------------------
# Navigation
# -------------------------

st.title("UG Procurement System")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Suppliers",
        "Projects",
        "Products",
        "Inventory",
        "Purchase Orders",
        "Excel Import",
        "Documents",
    ],
)

if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.rerun()

# Load reference data
suppliers = load_table("suppliers")
projects = load_table("projects")
products = load_table("products")
orders = load_table("purchase_orders")


# -------------------------
# Dashboard
# -------------------------

if page == "Dashboard":
    st.header("Procurement Overview")

    inventory = load_table("inventory")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Suppliers", len(suppliers))
    c2.metric("Projects", len(projects))
    c3.metric("Products", len(products))
    c4.metric("Purchase Orders", len(orders))

    if not inventory.empty:
        st.subheader("Inventory Classification")

        if "stock_classification" in inventory.columns:
            counts = inventory["stock_classification"].value_counts()
            st.bar_chart(counts)

    if not orders.empty and "status" in orders.columns:
        st.subheader("Purchase Order Status")
        st.dataframe(
            orders,
            use_container_width=True,
            hide_index=True,
        )


# -------------------------
# Suppliers
# -------------------------

elif page == "Suppliers":
    st.header("Suppliers")

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
        else:
            result = insert_row("suppliers", {
                "supplier_name": name.strip(),
                "country": country,
                "contact_person": contact,
                "email": email,
                "phone": phone,
                "payment_terms": payment,
                "notes": notes,
            })

            if result:
                st.success("Supplier added.")
                st.rerun()

    show_table("suppliers", "Supplier Register")


# -------------------------
# Projects
# -------------------------

elif page == "Projects":
    st.header("Projects")

    with st.form("project_form", clear_on_submit=True):
        name = st.text_input("Project Name")
        customer = st.text_input("Customer")
        location = st.text_input("Location")
        status = st.selectbox(
            "Status", ["Active", "On Hold", "Completed", "Cancelled"]
        )
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Add Project")

    if submitted:
        if not name.strip():
            st.error("Project Name is required.")
        else:
            result = insert_row("projects", {
                "project_name": name.strip(),
                "customer": customer,
                "location": location,
                "status": status,
                "notes": notes,
            })

            if result:
                st.success("Project added.")
                st.rerun()

    show_table("projects", "Project Register")


# -------------------------
# Products
# -------------------------

elif page == "Products":
    st.header("Products & Sensors")

    supplier_options = options_with_names(
        suppliers, "supplier_name"
    )
    supplier_labels = ["Not specified"] + list(supplier_options)

    categories = [
        "Geotechnical Sensor",
        "Structural Sensor",
        "Data Acquisition System",
        "Gateway / Communication",
        "Software",
        "Electronic Component",
        "Accessory",
        "Other",
    ]

    with st.form("product_form", clear_on_submit=True):
        name = st.text_input("Product Name")
        category = st.selectbox("Category", categories)
        manufacturer = st.text_input("Manufacturer")
        model = st.text_input("Model")
        supplier_label = st.selectbox(
            "Supplier", supplier_labels
        )
        unit = st.selectbox(
            "Unit", ["pcs", "set", "m", "lot", "other"]
        )
        datasheet = st.text_input("Datasheet URL")
        notes = st.text_area("Technical Notes")

        submitted = st.form_submit_button("Add Product")

    if submitted:
        if not name.strip():
            st.error("Product Name is required.")
        else:
            supplier_id = supplier_options.get(supplier_label)

            result = insert_row("products", {
                "product_name": name.strip(),
                "category": category,
                "manufacturer": manufacturer,
                "model": model,
                "supplier_id": supplier_id,
                "unit": unit,
                "datasheet_url": datasheet,
                "notes": notes,
            })

            if result:
                st.success("Product added.")
                st.rerun()

    show_table("products", "Product Register")


# -------------------------
# Inventory
# -------------------------

elif page == "Inventory":
    st.header("Inventory & Sensor Allocation")

    product_options = options_with_names(
        products, "product_name"
    )
    project_options = options_with_names(
        projects, "project_name"
    )
    supplier_options = options_with_names(
        suppliers, "supplier_name"
    )

    if not product_options:
        st.warning("Add or import products before adding inventory.")

    else:
        with st.form("inventory_form", clear_on_submit=True):
            product_label = st.selectbox(
                "Product / Sensor", list(product_options)
            )

            serial = st.text_input("Serial Number (if applicable)")
            quantity = st.number_input(
                "Quantity", min_value=0.001, value=1.0
            )

            classification = st.selectbox(
                "Stock Classification",
                [
                    "Project Allocation",
                    "UG Stock",
                    "Project Spare",
                ],
            )

            project_label = st.selectbox(
                "Project",
                ["Not assigned"] + list(project_options),
            )

            supplier_label = st.selectbox(
                "Supplier",
                ["Not specified"] + list(supplier_options),
            )

            po_number = st.text_input("PO Number")
            receipt_date = st.date_input(
                "Receipt Date", value=date.today()
            )
            location = st.text_input("Storage Location")
            condition = st.selectbox(
                "Condition", ["New", "Used", "Damaged"]
            )
            notes = st.text_area("Notes")

            submitted = st.form_submit_button("Add Inventory Record")

        if submitted:
            project_id = project_options.get(project_label)

            if classification in [
                "Project Allocation", "Project Spare"
            ] and project_id is None:
                st.error(
                    "Select the project for Project Allocation "
                    "or Project Spare."
                )
            else:
                result = insert_row("inventory", {
                    "product_id": product_options[product_label],
                    "serial_number": serial,
                    "quantity": quantity,
                    "stock_classification": classification,
                    "project_id": project_id,
                    "supplier_id": supplier_options.get(supplier_label),
                    "po_number": po_number,
                    "receipt_date": receipt_date.isoformat(),
                    "location": location,
                    "condition": condition,
                    "notes": notes,
                })

                if result:
                    st.success("Inventory record added.")
                    st.rerun()

    show_table("inventory", "Inventory Register")


# -------------------------
# Purchase Orders
# -------------------------

elif page == "Purchase Orders":
    st.header("Purchase Orders")

    project_options = options_with_names(
        projects, "project_name"
    )
    supplier_options = options_with_names(
        suppliers, "supplier_name"
    )
    product_options = options_with_names(
        products, "product_name"
    )

    with st.form("po_form", clear_on_submit=True):
        po_number = st.text_input("PO Number")

        project_label = st.selectbox(
            "Project",
            ["Not specified"] + list(project_options),
        )

        supplier_label = st.selectbox(
            "Supplier",
            ["Not specified"] + list(supplier_options),
        )

        order_date = st.date_input(
            "Order Date", value=date.today()
        )
        currency = st.selectbox(
            "Currency", ["USD", "EUR", "SAR", "EGP", "GBP"]
        )
        status = st.selectbox(
            "Status",
            [
                "Draft", "Pending Approval", "Approved",
                "Ordered", "Partially Received",
                "Received", "Cancelled",
            ],
        )
        payment_status = st.selectbox(
            "Payment Status",
            ["Not Paid", "Partially Paid", "Paid"],
        )
        shipping_status = st.selectbox(
            "Shipping Status",
            ["Not Shipped", "In Transit", "Delivered", "Delayed"],
        )
        notes = st.text_area("Notes")

        add_item = st.checkbox(
            "Add a product line to this purchase order"
        )

        product_label = None
        quantity = 1.0
        unit_price = 0.0

        if add_item:
            if product_options:
                product_label = st.selectbox(
                    "Product", list(product_options)
                )
                quantity = st.number_input(
                    "Quantity", min_value=0.001, value=1.0
                )
                unit_price = st.number_input(
                    "Unit Price", min_value=0.0, value=0.0
                )
            else:
                st.warning("Add products before adding a PO item.")

        submitted = st.form_submit_button("Create Purchase Order")

    if submitted:
        if not po_number.strip():
            st.error("PO Number is required.")
        elif add_item and not product_options:
            st.error("Import or add a product first.")
        else:
            result = insert_row("purchase_orders", {
                "po_number": po_number.strip(),
                "project_id": project_options.get(project_label),
                "supplier_id": supplier_options.get(supplier_label),
                "order_date": order_date.isoformat(),
                "currency": currency,
                "status": status,
                "payment_status": payment_status,
                "shipping_status": shipping_status,
                "notes": notes,
            })

            if result:
                if add_item and product_label:
                    po_id = result[0]["id"]

                    item_result = insert_row(
                        "purchase_order_items",
                        {
                            "purchase_order_id": po_id,
                            "product_id": product_options[product_label],
                            "quantity": quantity,
                            "unit_price": unit_price,
                        },
                    )

                    if item_result:
                        st.success("Purchase order and item created.")
                    else:
                        st.warning(
                            "PO created, but its item was not saved. "
                            "Check the error above."
                        )
                else:
                    st.success("Purchase order created.")

                st.rerun()

    show_table("purchase_orders", "Purchase Order Register")
    show_table("purchase_order_items", "Purchase Order Items")


# -------------------------
# Bulk Excel Import
# -------------------------

elif page == "Excel Import":
    st.header("Bulk Import from Excel")

    st.write(
        "Upload an Excel workbook, select a sheet and destination table, "
        "map the columns, preview the data, and import."
    )

    uploaded_excel = st.file_uploader(
        "Upload Excel Workbook",
        type=["xlsx", "xls"],
    )

    if uploaded_excel:
        try:
            workbook = pd.ExcelFile(uploaded_excel)
            sheet_name = st.selectbox(
                "Worksheet", workbook.sheet_names
            )
            df = pd.read_excel(
                uploaded_excel, sheet_name=sheet_name
            )

            st.subheader("Source Preview")
            st.dataframe(df.head(20), use_container_width=True)

            target_label = st.selectbox(
                "Import into",
                [
                    "Suppliers",
                    "Projects",
                    "Products",
                    "Inventory",
                    "Purchase Orders",
                    "PO Items",
                ],
            )
            target_table = TABLES[target_label]
            target_columns = IMPORT_COLUMNS[target_table]

            st.subheader("Map Excel Columns")

            source_columns = ["-- Skip --"] + list(df.columns)
            mapping = {}

            for column in target_columns:
                normalized = column.lower().replace("_", " ")
                match = next(
                    (
                        source for source in df.columns
                        if str(source).strip().lower()
                        .replace("_", " ") == normalized
                    ),
                    "-- Skip --",
                )

                mapping[column] = st.selectbox(
                    f"Database field: {column}",
                    source_columns,
                    index=(
                        source_columns.index(match)
                        if match in source_columns else 0
                    ),
                    key=f"map_{target_table}_{column}",
                )

            st.caption(
                "Do not import generated IDs or created_at values. "
                "For linked records, use valid Supabase IDs in foreign-key "
                "columns, or import the parent tables first."
            )

            preview_rows = []

            for _, source_row in df.head(10).iterrows():
                mapped = {}
                for target_col, source_col in mapping.items():
                    if source_col != "-- Skip --":
                        mapped[target_col] = clean_value(
                            source_row[source_col]
                        )
                preview_rows.append(mapped)

            st.subheader("Mapped Preview")
            st.dataframe(
                pd.DataFrame(preview_rows),
                use_container_width=True,
            )

            if st.button("Import Excel Data"):
                chosen = {
                    target_col: source_col
                    for target_col, source_col in mapping.items()
                    if source_col != "-- Skip --"
                }

                if not chosen:
                    st.error("Map at least one column.")
                else:
                    imported = 0
                    failed = 0
                    errors = []

                    progress = st.progress(0)

                    for index, (_, source_row) in enumerate(df.iterrows()):
                        record = {}

                        for target_col, source_col in chosen.items():
                            record[target_col] = clean_value(
                                source_row[source_col]
                            )

                        record = {
                            key: value
                            for key, value in record.items()
                            if value is not None
                        }

                        if not record:
                            continue

                        try:
                            supabase.table(target_table).insert(
                                record
                            ).execute()
                            imported += 1

                        except Exception as exc:
                            failed += 1
                            if len(errors) < 10:
                                errors.append(
                                    f"Excel row {index + 2}: {exc}"
                                )

                        progress.progress(
                            min((index + 1) / max(len(df), 1), 1.0)
                        )

                    st.success(f"Imported rows: {imported}")
                    st.write(f"Failed rows: {failed}")

                    for error in errors:
                        st.error(error)

                    if failed:
                        st.warning(
                            "Review failed rows before retrying. "
                            "Some rows may already have been imported."
                        )

        except Exception as exc:
            st.error(f"Could not read Excel file: {exc}")


# -------------------------
# Documents & Attachments
# -------------------------

elif page == "Documents":
    st.header("Documents & Attachments")

    st.write(
        "Upload datasheets, quotations, calibration certificates, "
        "DoC, MSDS, COO, Excel workbooks, and other project documents."
    )

    attachment_type = st.selectbox(
        "Link document to",
        [
            "General",
            "Supplier",
            "Project",
            "Product",
            "Inventory Record",
            "Purchase Order",
        ],
    )

    target_tables = {
        "Supplier": ("suppliers", suppliers, "supplier_name"),
        "Project": ("projects", projects, "project_name"),
        "Product": ("products", products, "product_name"),
        "Inventory Record": (
            "inventory", load_table("inventory"), "id"
        ),
        "Purchase Order": (
            "purchase_orders", orders, "po_number"
        ),
    }

    selected_record_id = None

    if attachment_type != "General":
        table, records, name_col = target_tables[attachment_type]

        if not records.empty and "id" in records.columns:
            record_options = options_with_names(records, name_col)

            if record_options:
                selected_label = st.selectbox(
                    "Select record", list(record_options)
                )
                selected_record_id = record_options[selected_label]
            else:
                st.warning("No records available.")
        else:
            st.warning("No records available.")

    category = st.selectbox(
        "Document Type",
        [
            "Datasheet",
            "Quotation",
            "Calibration Certificate",
            "Declaration of Conformity",
            "MSDS",
            "Certificate of Origin",
            "Excel Database",
            "Purchase Order",
            "Invoice",
            "Other",
        ],
    )

    uploaded_files = st.file_uploader(
        "Select files",
        type=[
            "xlsx", "xls", "csv", "pdf", "docx",
            "doc", "png", "jpg", "jpeg",
        ],
        accept_multiple_files=True,
    )

    if st.button("Upload Documents"):
        if not uploaded_files:
            st.error("Select at least one file.")
        elif (
            attachment_type != "General"
            and selected_record_id is None
        ):
            st.error("Select a record to attach the documents to.")
        else:
            success_count = 0

            for uploaded_file in uploaded_files:
                file_path = (
                    f"{category.replace(' ', '_')}/"
                    f"{uuid.uuid4().hex}_{uploaded_file.name}"
                )

                try:
                    supabase.storage.from_(BUCKET).upload(
                        file_path,
                        uploaded_file.getvalue(),
                        {
                            "content-type": (
                                uploaded_file.type
                                or "application/octet-stream"
                            ),
                        },
                    )

                    attachment = {
                        "file_name": uploaded_file.name,
                        "storage_path": file_path,
                        "file_type": category,
                    }

                    if attachment_type != "General":
                        fk_columns = {
                            "Supplier": "supplier_id",
                            "Project": "project_id",
                            "Product": "product_id",
                            "Inventory Record": "inventory_id",
                            "Purchase Order": "purchase_order_id",
                        }

                        attachment[
                            fk_columns[attachment_type]
                        ] = selected_record_id

                    result = insert_row("attachments", attachment)

                    if result:
                        success_count += 1

                except Exception as exc:
                    st.error(
                        f"Failed to upload {uploaded_file.name}: {exc}"
                    )

            st.success(
                f"Uploaded and registered {success_count} document(s)."
            )

    st.subheader("Registered Documents")
    attachments = load_table("attachments")

    if attachments.empty:
        st.info("No documents registered yet.")
    else:
        st.dataframe(
            attachments,
            use_container_width=True,
            hide_index=True,
        )

        if "storage_path" in attachments.columns:
            st.caption(
                "Files are stored in a private bucket. "
                "A download action with temporary signed URLs "
                "will be added after validating the initial upload."
            )
