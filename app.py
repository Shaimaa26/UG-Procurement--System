
import io
import re
import json
import hashlib
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st
from supabase import create_client


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="United Group | Procurement System",
    page_icon="📊",
    layout="wide",
)

st.title("United Group | Procurement System")
st.caption("Procurement, suppliers, inventory, purchase orders and documents")


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

@st.cache_resource
def get_supabase_client():
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be configured "
            "in Streamlit Secrets."
        )

    return create_client(url, key)


try:
    supabase = get_supabase_client()
except Exception as exc:
    st.error(f"Supabase connection configuration error: {exc}")
    st.stop()


BUCKET = "procurement-documents"


# =========================================================
# TABLE CONFIGURATION
# Must match the existing Supabase schema
# =========================================================

TABLES = {
    "Suppliers": {
        "table": "suppliers",
        "columns": [
            "id", "supplier_name", "country", "contact_person",
            "email", "phone", "payment_terms", "notes", "created_at",
        ],
        "required": ["supplier_name"],
        "unique_key": "supplier_name",
        "aliases": {
            "supplier": "supplier_name",
            "supplier name": "supplier_name",
            "vendor": "supplier_name",
            "vendor name": "supplier_name",
            "company": "supplier_name",
            "company name": "supplier_name",
            "contact": "contact_person",
            "contact name": "contact_person",
            "e mail": "email",
            "telephone": "phone",
            "country name": "country",
            "payment term": "payment_terms",
            "terms": "payment_terms",
            "remarks": "notes",
            "comments": "notes",
        },
    },
    "Projects": {
        "table": "projects",
        "columns": [
            "id", "project_name", "customer", "location",
            "status", "notes", "created_at",
        ],
        "required": ["project_name"],
        "unique_key": "project_name",
        "aliases": {
            "project": "project_name",
            "project name": "project_name",
            "project title": "project_name",
            "customer name": "customer",
            "client": "customer",
            "site": "location",
            "site location": "location",
            "project status": "status",
            "remarks": "notes",
            "comments": "notes",
        },
    },
    "Products": {
        "table": "products",
        "columns": [
            "id", "product_name", "category", "manufacturer",
            "model", "supplier_id", "unit", "datasheet_url",
            "notes", "created_at",
        ],
        "required": ["product_name"],
        "unique_key": "id",
        "aliases": {
            "product": "product_name",
            "product name": "product_name",
            "item": "product_name",
            "item name": "product_name",
            "description": "product_name",
            "product description": "product_name",
            "type": "category",
            "product category": "category",
            "brand": "manufacturer",
            "make": "manufacturer",
            "model number": "model",
            "part number": "model",
            "pn": "model",
            "supplier": "supplier_id",
            "vendor": "supplier_id",
            "supplier id": "supplier_id",
            "vendor id": "supplier_id",
            "uom": "unit",
            "unit of measure": "unit",
            "datasheet": "datasheet_url",
            "datasheet link": "datasheet_url",
            "url": "datasheet_url",
            "remarks": "notes",
            "comments": "notes",
        },
    },
    "Inventory": {
        "table": "inventory",
        "columns": [
            "id", "product_id", "serial_number", "quantity",
            "stock_classification", "project_id", "supplier_id",
            "po_number", "receipt_date", "location", "condition",
            "notes", "created_at",
        ],
        "required": ["product_id", "quantity", "stock_classification"],
        "unique_key": "id",
        "aliases": {
            "product": "product_id",
            "product name": "product_id",
            "product id": "product_id",
            "item id": "product_id",
            "serial": "serial_number",
            "serial no": "serial_number",
            "serial number": "serial_number",
            "qty": "quantity",
            "stock": "quantity",
            "stock quantity": "quantity",
            "classification": "stock_classification",
            "stock type": "stock_classification",
            "stock classification": "stock_classification",
            "project": "project_id",
            "project name": "project_id",
            "project id": "project_id",
            "supplier": "supplier_id",
            "supplier id": "supplier_id",
            "vendor": "supplier_id",
            "purchase order": "po_number",
            "po": "po_number",
            "po no": "po_number",
            "po number": "po_number",
            "date received": "receipt_date",
            "received date": "receipt_date",
            "receipt date": "receipt_date",
            "site": "location",
            "storage location": "location",
            "status": "condition",
            "remarks": "notes",
            "comments": "notes",
        },
    },
    "Purchase Orders": {
        "table": "purchase_orders",
        "columns": [
            "id", "po_number", "project_id", "supplier_id",
            "order_date", "currency", "status", "payment_status",
            "shipping_status", "notes", "created_at",
        ],
        "required": ["po_number"],
        "unique_key": "po_number",
        "aliases": {
            "po": "po_number",
            "po no": "po_number",
            "po number": "po_number",
            "purchase order": "po_number",
            "purchase order number": "po_number",
            "project": "project_id",
            "project id": "project_id",
            "supplier": "supplier_id",
            "vendor": "supplier_id",
            "supplier id": "supplier_id",
            "vendor id": "supplier_id",
            "date": "order_date",
            "order date": "order_date",
            "po date": "order_date",
            "payment": "payment_status",
            "payment status": "payment_status",
            "shipment status": "shipping_status",
            "shipping status": "shipping_status",
            "order status": "status",
            "remarks": "notes",
            "comments": "notes",
        },
    },
    "Purchase Order Items": {
        "table": "purchase_order_items",
        "columns": [
            "id", "purchase_order_id", "product_id",
            "quantity", "unit_price", "notes",
        ],
        "required": [
            "purchase_order_id", "product_id", "quantity",
        ],
        "unique_key": "id",
        "aliases": {
            "po id": "purchase_order_id",
            "purchase order id": "purchase_order_id",
            "po number": "purchase_order_id",
            "purchase order": "purchase_order_id",
            "product": "product_id",
            "product id": "product_id",
            "item id": "product_id",
            "qty": "quantity",
            "unit cost": "unit_price",
            "price": "unit_price",
            "unit price": "unit_price",
            "remarks": "notes",
            "comments": "notes",
        },
    },
}

STOCK_TYPES = [
    "Project Allocation",
    "UG Stock",
    "Project Spare",
]

TABLE_LOOKUP = {
    config["table"]: (label, config)
    for label, config in TABLES.items()
}


# =========================================================
# AUTHENTICATION
# =========================================================

def check_password():
    expected_password = st.secrets.get("APP_PASSWORD", "")

    if not expected_password:
        st.error("Please configure APP_PASSWORD in Streamlit Secrets.")
        st.stop()

    if st.session_state.get("authenticated"):
        return True

    st.subheader("Login")

    with st.form("login_form"):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if password == expected_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    return False


if not check_password():
    st.stop()


with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Select section",
        [
            "Dashboard",
            "Suppliers",
            "Projects",
            "Products",
            "Inventory",
            "Purchase Orders",
            "Purchase Order Items",
            "Excel Import",
            "Documents",
        ],
    )

    if st.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()


# =========================================================
# GENERAL HELPERS
# =========================================================

def get_rows(table, limit=5000):
    response = (
        supabase.table(table)
        .select("*")
        .order("id", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []


def show_table(table, columns=None):
    try:
        rows = get_rows(table)
        if not rows:
            st.info("No records found.")
            return

        df = pd.DataFrame(rows)
        if columns:
            visible = [c for c in columns if c in df.columns]
            df = df[visible]

        st.dataframe(df, use_container_width=True, hide_index=True)

        csv_data = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Download CSV",
            data=csv_data,
            file_name=f"{table}.csv",
            mime="text/csv",
            key=f"download_{table}",
        )
    except Exception as exc:
        st.error(f"Could not load {table}: {exc}")


def clean_value(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, str):
        value = value.strip()
        return value if value else None

    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass

    return value


def clean_record(record):
    return {
        str(key): clean_value(value)
        for key, value in record.items()
        if clean_value(value) is not None
    }


def normalize_column_name(value):
    value = str(value).strip().lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[\r\n\t]+", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def suggest_column_mapping(source_column, config):
    normalized = normalize_column_name(source_column)
    target_columns = config["columns"]

    for target in target_columns:
        if normalized == normalize_column_name(target):
            return target

    aliases = {
        normalize_column_name(alias): target
        for alias, target in config.get("aliases", {}).items()
    }

    if normalized in aliases:
        return aliases[normalized]

    return "-- Ignore this column --"


def get_options(table, label_column, id_column="id"):
    try:
        rows = (
            supabase.table(table)
            .select(f"{id_column},{label_column}")
            .order(label_column)
            .limit(5000)
            .execute()
            .data
            or []
        )
        return rows
    except Exception:
        return []


def option_label(row, label_column):
    return str(row.get(label_column) or f"ID {row.get('id')}")


def insert_record(table, payload):
    return supabase.table(table).insert(payload).execute()


def update_record(table, row_id, payload):
    return (
        supabase.table(table)
        .update(payload)
        .eq("id", row_id)
        .execute()
    )


def selectbox_id(label, table, label_column, key):
    options = get_options(table, label_column)
    choices = {None: "-- None --"}

    for row in options:
        choices[row["id"]] = option_label(row, label_column)

    selected_id = st.selectbox(
        label,
        options=list(choices.keys()),
        format_func=lambda x: choices[x],
        key=key,
    )
    return selected_id


def add_form(table, fields, title):
    st.subheader(title)

    with st.form(f"add_{table}"):
        values = {}

        for field, field_type in fields:
            if field_type == "supplier_id":
                values[field] = selectbox_id(
                    "Supplier", "suppliers", "supplier_name",
                    f"{table}_{field}",
                )
            elif field_type == "project_id":
                values[field] = selectbox_id(
                    "Project", "projects", "project_name",
                    f"{table}_{field}",
                )
            elif field_type == "product_id":
                products = get_options("products", "product_name")
                choices = {None: "-- Select product --"}
                for product in products:
                    choices[product["id"]] = (
                        f'{product["product_name"]} (ID {product["id"]})'
                    )
                values[field] = st.selectbox(
                    "Product",
                    list(choices.keys()),
                    format_func=lambda x: choices[x],
                )
            elif field_type == "purchase_order_id":
                orders = get_options("purchase_orders", "po_number")
                choices = {None: "-- Select PO --"}
                for order in orders:
                    choices[order["id"]] = (
                        f'{order["po_number"]} (ID {order["id"]})'
                    )
                values[field] = st.selectbox(
                    "Purchase Order",
                    list(choices.keys()),
                    format_func=lambda x: choices[x],
                )
            elif field_type == "stock_classification":
                values[field] = st.selectbox(
                    "Stock Classification", STOCK_TYPES
                )
            elif field_type == "date":
                values[field] = st.date_input(field.replace("_", " ").title())
            elif field_type == "number":
                values[field] = st.number_input(
                    field.replace("_", " ").title(),
                    min_value=0.0,
                    value=0.0,
                )
            elif field_type == "integer":
                values[field] = st.number_input(
                    field.replace("_", " ").title(),
                    min_value=0,
                    value=0,
                    step=1,
                )
            elif field_type == "text":
                values[field] = st.text_input(
                    field.replace("_", " ").title()
                )
            else:
                values[field] = st.text_area(
                    field.replace("_", " ").title()
                )

        submitted = st.form_submit_button("Save")

    if submitted:
        payload = {}

        for field, field_type in fields:
            value = values[field]

            if field_type == "date":
                value = value.isoformat()
            if field_type in (
                "supplier_id", "project_id", "product_id",
                "purchase_order_id",
            ) and value is None:
                continue
            if isinstance(value, str):
                value = value.strip()
            if value == "":
                continue

            payload[field] = value

        try:
            insert_record(table, payload)
            st.success("Record saved successfully.")
            st.rerun()
        except Exception as exc:
            st.error(f"Save failed: {exc}")


# =========================================================
# DASHBOARD
# =========================================================

if page == "Dashboard":
    st.subheader("Procurement Overview")

    metrics = [
        ("Suppliers", "suppliers"),
        ("Projects", "projects"),
        ("Products", "products"),
        ("Inventory Records", "inventory"),
        ("Purchase Orders", "purchase_orders"),
    ]

    cols = st.columns(len(metrics))

    for col, (label, table) in zip(cols, metrics):
        try:
            count = len(get_rows(table))
            col.metric(label, count)
        except Exception:
            col.metric(label, "—")

    st.divider()
    st.subheader("Recent Purchase Orders")
    show_table("purchase_orders")


# =========================================================
# SUPPLIERS
# =========================================================

elif page == "Suppliers":
    add_form(
        "suppliers",
        [
            ("supplier_name", "text"),
            ("country", "text"),
            ("contact_person", "text"),
            ("email", "text"),
            ("phone", "text"),
            ("payment_terms", "text"),
            ("notes", "textarea"),
        ],
        "Add Supplier",
    )
    st.divider()
    show_table("suppliers")


# =========================================================
# PROJECTS
# =========================================================

elif page == "Projects":
    add_form(
        "projects",
        [
            ("project_name", "text"),
            ("customer", "text"),
            ("location", "text"),
            ("status", "text"),
            ("notes", "textarea"),
        ],
        "Add Project",
    )
    st.divider()
    show_table("projects")


# =========================================================
# PRODUCTS
# =========================================================

elif page == "Products":
    add_form(
        "products",
        [
            ("product_name", "text"),
            ("category", "text"),
            ("manufacturer", "text"),
            ("model", "text"),
            ("supplier_id", "supplier_id"),
            ("unit", "text"),
            ("datasheet_url", "text"),
            ("notes", "textarea"),
        ],
        "Add Product",
    )
    st.divider()
    show_table("products")


# =========================================================
# INVENTORY
# =========================================================

elif page == "Inventory":
    add_form(
        "inventory",
        [
            ("product_id", "product_id"),
            ("serial_number", "text"),
            ("quantity", "number"),
            ("stock_classification", "stock_classification"),
            ("project_id", "project_id"),
            ("supplier_id", "supplier_id"),
            ("po_number", "text"),
            ("receipt_date", "date"),
            ("location", "text"),
            ("condition", "text"),
            ("notes", "textarea"),
        ],
        "Add Inventory Record",
    )
    st.divider()
    show_table("inventory")


# =========================================================
# PURCHASE ORDERS
# =========================================================

elif page == "Purchase Orders":
    add_form(
        "purchase_orders",
        [
            ("po_number", "text"),
            ("project_id", "project_id"),
            ("supplier_id", "supplier_id"),
            ("order_date", "date"),
            ("currency", "text"),
            ("status", "text"),
            ("payment_status", "text"),
            ("shipping_status", "text"),
            ("notes", "textarea"),
        ],
        "Add Purchase Order",
    )
    st.divider()
    show_table("purchase_orders")


# =========================================================
# PURCHASE ORDER ITEMS
# =========================================================

elif page == "Purchase Order Items":
    add_form(
        "purchase_order_items",
        [
            ("purchase_order_id", "purchase_order_id"),
            ("product_id", "product_id"),
            ("quantity", "number"),
            ("unit_price", "number"),
            ("notes", "textarea"),
        ],
        "Add Purchase Order Item",
    )
    st.divider()
    show_table("purchase_order_items")


# =========================================================
# EXCEL / CSV IMPORT
# =========================================================

elif page == "Excel Import":
    st.subheader("Import or Update Records")
    st.write(
        "Upload Excel or CSV files. Column names and order can differ "
        "from the database. Map each source column to a database field."
    )

    uploaded_file = st.file_uploader(
        "Upload Excel or CSV",
        type=["xlsx", "xls", "csv"],
        key="excel_import_file",
    )

    if uploaded_file:
        try:
            file_bytes = uploaded_file.getvalue()

            if uploaded_file.name.lower().endswith(".csv"):
                data = pd.read_csv(io.BytesIO(file_bytes))
                sheet_name = None
                sheets = {"CSV": data}
            else:
                excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
                sheet_names = excel_file.sheet_names

                sheet_name = st.selectbox(
                    "Select worksheet",
                    sheet_names,
                    key="import_sheet",
                )

                sheets = {
                    name: pd.read_excel(
                        io.BytesIO(file_bytes),
                        sheet_name=name,
                    )
                    for name in sheet_names
                }

            if uploaded_file.name.lower().endswith(".csv"):
                source_df = sheets["CSV"].copy()
            else:
                source_df = sheets[sheet_name].copy()

            source_df.columns = [
                str(column).strip()
                for column in source_df.columns
            ]

            st.write(f"Rows: {len(source_df)} | Columns: {len(source_df.columns)}")
            st.dataframe(source_df.head(10), use_container_width=True)

            target_label = st.selectbox(
                "Import into database table",
                list(TABLES.keys()),
                key="import_target_table",
            )
            config = TABLES[target_label]
            target_table = config["table"]

            st.markdown("#### Map Excel columns to database columns")
            st.caption(
                "Automatic suggestions are provided. Review the mapping "
                "before importing. Leave unused columns as Ignore."
            )

            mapping_options = [
                "-- Ignore this column --"
            ] + config["columns"]

            mapping = {}
            map_cols = st.columns(2)

            for index, source_column in enumerate(source_df.columns):
                suggested = suggest_column_mapping(source_column, config)

                with map_cols[index % 2]:
                    mapping[source_column] = st.selectbox(
                        f"{source_column}",
                        mapping_options,
                        index=(
                            mapping_options.index(suggested)
                            if suggested in mapping_options
                            else 0
                        ),
                        key=f"map_{target_table}_{index}",
                    )

            mapped_targets = [
                target
                for target in mapping.values()
                if target != "-- Ignore this column --"
            ]

            duplicate_targets = sorted({
                target for target in mapped_targets
                if mapped_targets.count(target) > 1
            })

            if duplicate_targets:
                st.error(
                    "Multiple Excel columns are mapped to the same field: "
                    + ", ".join(duplicate_targets)
                )
                st.stop()

            mapped_df = pd.DataFrame()

            for source_column, target_column in mapping.items():
                if target_column != "-- Ignore this column --":
                    mapped_df[target_column] = source_df[source_column]

            if mapped_df.empty:
                st.warning("Map at least one Excel column.")
                st.stop()

            # Convert empty strings and NaN values to None.
            mapped_df = mapped_df.astype(object).where(
                pd.notna(mapped_df), None
            )

            # Remove rows that are completely empty.
            mapped_df = mapped_df[
                mapped_df.apply(
                    lambda row: any(
                        clean_value(value) is not None
                        for value in row
                    ),
                    axis=1,
                )
            ].reset_index(drop=True)

            st.markdown("#### Import options")

            import_mode = st.radio(
                "Import mode",
                [
                    "Insert new records",
                    "Update existing records",
                    "Upsert (insert or update)",
                ],
                help=(
                    "Update requires a matching key. Upsert uses the "
                    "table's configured unique key."
                ),
            )

            default_key = config.get("unique_key", "id")
            available_keys = [
                column for column in config["columns"]
                if column in mapped_df.columns
            ]

            if import_mode == "Update existing records":
                if not available_keys:
                    st.error(
                        "Map a matching key column, such as ID, before "
                        "using Update."
                    )
                    st.stop()

                match_key = st.selectbox(
                    "Match existing records using",
                    available_keys,
                    index=(
                        available_keys.index(default_key)
                        if default_key in available_keys
                        else 0
                    ),
                )

            elif import_mode == "Upsert (insert or update)":
                match_key = default_key

                if match_key not in mapped_df.columns:
                    st.error(
                        f"Upsert for this table requires the '{match_key}' "
                        "column to be mapped. Add it to the Excel file or "
                        "use Insert mode for new records."
                    )
                    st.stop()

                if match_key not in config["columns"]:
                    st.error("Invalid upsert key configured.")
                    st.stop()

            else:
                match_key = None

            st.markdown("#### Validation")

            errors = []
            valid_records = []
            row_numbers = []

            for idx, (_, row) in enumerate(mapped_df.iterrows(), start=2):
                record = clean_record(row.to_dict())
                row_errors = []

                for required_field in config["required"]:
                    if record.get(required_field) is None:
                        row_errors.append(
                            f"Missing required field: {required_field}"
                        )

                if import_mode != "Insert new records":
                    if record.get(match_key) is None:
                        row_errors.append(
                            f"Missing match key: {match_key}"
                        )

                if target_table == "inventory":
                    stock_class = record.get("stock_classification")
                    if (
                        stock_class is not None
                        and stock_class not in STOCK_TYPES
                    ):
                        row_errors.append(
                            "Invalid stock_classification. Allowed values: "
                            + ", ".join(STOCK_TYPES)
                        )

                    quantity = record.get("quantity")
                    if quantity is not None:
                        try:
                            if Decimal(str(quantity)) < 0:
                                row_errors.append(
                                    "Quantity cannot be negative."
                                )
                        except InvalidOperation:
                            row_errors.append("Quantity must be numeric.")

                for number_field in [
                    "quantity", "unit_price"
                ]:
                    if number_field in record:
                        try:
                            if Decimal(str(record[number_field])) < 0:
                                row_errors.append(
                                    f"{number_field} cannot be negative."
                                )
                        except InvalidOperation:
                            row_errors.append(
                                f"{number_field} must be numeric."
                            )

                if row_errors:
                    errors.append({
                        "Excel row": idx,
                        "Errors": "; ".join(row_errors),
                    })
                else:
                    valid_records.append(record)
                    row_numbers.append(idx)

            # Detect duplicate keys within the uploaded file.
            if match_key and match_key in mapped_df.columns:
                seen = {}
                duplicate_rows = set()

                for position, record in enumerate(valid_records):
                    key_value = record.get(match_key)
                    if key_value is None:
                        continue

                    comparable_key = str(key_value).strip().lower()

                    if comparable_key in seen:
                        duplicate_rows.add(position)
                        errors.append({
                            "Excel row": row_numbers[position],
                            "Errors": (
                                f"Duplicate {match_key} value in uploaded "
                                f"file: {key_value}"
                            ),
                        })
                    else:
                        seen[comparable_key] = position

                if duplicate_rows:
                    valid_records = [
                        record for position, record in enumerate(valid_records)
                        if position not in duplicate_rows
                    ]

            st.write(f"Valid rows: {len(valid_records)}")
            st.write(f"Rows with validation errors: {len(errors)}")

            if errors:
                st.dataframe(
                    pd.DataFrame(errors),
                    use_container_width=True,
                    hide_index=True,
                )

                error_csv = pd.DataFrame(errors).to_csv(
                    index=False
                ).encode("utf-8-sig")

                st.download_button(
                    "Download validation errors",
                    data=error_csv,
                    file_name="import_validation_errors.csv",
                    mime="text/csv",
                )

            st.markdown("#### Preview mapped data")
            st.dataframe(
                pd.DataFrame(valid_records).head(50),
                use_container_width=True,
                hide_index=True,
            )

            allow_partial = st.checkbox(
                "Import valid rows even if other rows have errors",
                value=False,
            )

            if errors and not allow_partial:
                st.warning(
                    "Correct the errors or enable partial import before "
                    "continuing."
                )

            ready_to_import = (
                len(valid_records) > 0
                and (not errors or allow_partial)
            )

            if st.button(
                "Import records",
                disabled=not ready_to_import,
                type="primary",
            ):
                inserted = 0
                updated = 0
                skipped = 0
                db_errors = []

                progress = st.progress(0)

                for position, record in enumerate(valid_records):
                    try:
                        payload = dict(record)

                        # Never overwrite database-generated timestamps.
                        payload.pop("created_at", None)

                        if import_mode == "Insert new records":
                            # Ignore an empty ID so the database can generate it.
                            if payload.get("id") is None:
                                payload.pop("id", None)

                            supabase.table(target_table).insert(
                                payload
                            ).execute()
                            inserted += 1

                        elif import_mode == "Update existing records":
                            key_value = payload.pop(match_key)

                            existing = (
                                supabase.table(target_table)
                                .select(match_key)
                                .eq(match_key, key_value)
                                .limit(1)
                                .execute()
                                .data
                                or []
                            )

                            if not existing:
                                skipped += 1
                                db_errors.append({
                                    "Record": key_value,
                                    "Error": (
                                        "No existing record found for "
                                        f"{match_key}={key_value}"
                                    ),
                                })
                            elif payload:
                                (
                                    supabase.table(target_table)
                                    .update(payload)
                                    .eq(match_key, key_value)
                                    .execute()
                                )
                                updated += 1
                            else:
                                skipped += 1

                        else:
                            # Upsert updates the matching record or inserts a new one.
                            supabase.table(target_table).upsert(
                                payload,
                                on_conflict=match_key,
                            ).execute()
                            updated += 1

                    except Exception as exc:
                        db_errors.append({
                            "Record": record.get(match_key or "id", position + 1),
                            "Error": str(exc),
                        })

                    progress.progress(
                        (position + 1) / len(valid_records)
                    )

                st.success(
                    f"Import finished. Inserted: {inserted} | "
                    f"Updated/Upserted: {updated} | Skipped: {skipped} | "
                    f"Database errors: {len(db_errors)}"
                )

                if db_errors:
                    st.dataframe(
                        pd.DataFrame(db_errors),
                        use_container_width=True,
                        hide_index=True,
                    )

                    st.download_button(
                        "Download database errors",
                        data=pd.DataFrame(db_errors).to_csv(
                            index=False
                        ).encode("utf-8-sig"),
                        file_name="database_import_errors.csv",
                        mime="text/csv",
                    )

                st.cache_data.clear()


# =========================================================
# DOCUMENT MANAGEMENT
# =========================================================

elif page == "Documents":
    st.subheader("Upload and Download Documents")

    document_type = st.selectbox(
        "Link document to",
        [
            "Supplier",
            "Project",
            "Product",
            "Inventory",
            "Purchase Order",
        ],
    )

    entity_config = {
        "Supplier": ("suppliers", "supplier_name", "supplier_id"),
        "Project": ("projects", "project_name", "project_id"),
        "Product": ("products", "product_name", "product_id"),
        "Inventory": ("inventory", "serial_number", "inventory_id"),
        "Purchase Order": ("purchase_orders", "po_number", "purchase_order_id"),
    }

    entity_table, label_column, foreign_key = entity_config[document_type]
    entity_rows = get_options(entity_table, label_column)

    entity_choices = {None: "-- Select record --"}
    for row in entity_rows:
        entity_choices[row["id"]] = (
            f'{row.get(label_column) or "Record"} (ID {row["id"]})'
        )

    selected_entity = st.selectbox(
        f"Select {document_type}",
        list(entity_choices.keys()),
        format_func=lambda x: entity_choices[x],
    )

    uploaded_docs = st.file_uploader(
        "Select documents",
        accept_multiple_files=True,
        key="document_uploads",
    )

    if st.button(
        "Upload documents",
        disabled=not selected_entity or not uploaded_docs,
    ):
        for uploaded_doc in uploaded_docs:
            try:
                safe_name = re.sub(
                    r"[^A-Za-z0-9._-]+",
                    "_",
                    uploaded_doc.name,
                )

                storage_path = (
                    f"{document_type.lower().replace(' ', '_')}/"
                    f"{selected_entity}/"
                    f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_"
                    f"{safe_name}"
                )

                supabase.storage.from_(BUCKET).upload(
                    storage_path,
                    uploaded_doc.getvalue(),
                    {
                        "content-type": (
                            uploaded_doc.type
                            or "application/octet-stream"
                        ),
                        "upsert": "false",
                    },
                )

                metadata = {
                    "file_name": uploaded_doc.name,
                    "storage_path": storage_path,
                    "file_type": uploaded_doc.type,
                    foreign_key: selected_entity,
                }

                supabase.table("attachments").insert(
                    metadata
                ).execute()

                st.success(f"Uploaded: {uploaded_doc.name}")

            except Exception as exc:
                st.error(
                    f"Could not upload {uploaded_doc.name}: {exc}"
                )

    st.divider()
    st.subheader("Existing Documents")

    try:
        attachments = (
            supabase.table("attachments")
            .select("*")
            .order("id", desc=True)
            .limit(1000)
            .execute()
            .data
            or []
        )

        if not attachments:
            st.info("No documents registered yet.")
        else:
            attachment_df = pd.DataFrame(attachments)
            st.dataframe(
                attachment_df,
                use_container_width=True,
                hide_index=True,
            )

            attachment_ids = [
                row["id"] for row in attachments
            ]

            selected_attachment_id = st.selectbox(
                "Select a document to download",
                attachment_ids,
                format_func=lambda attachment_id: next(
                    (
                        f'{row.get("file_name")} (ID {row["id"]})'
                        for row in attachments
                        if row["id"] == attachment_id
                    ),
                    str(attachment_id),
                ),
            )

            if st.button("Generate download link"):
                selected_attachment = next(
                    row for row in attachments
                    if row["id"] == selected_attachment_id
                )

                signed_url = (
                    supabase.storage.from_(BUCKET)
                    .create_signed_url(
                        selected_attachment["storage_path"],
                        3600,
                    )
                )

                download_url = (
                    signed_url.get("signedURL")
                    or signed_url.get("signedUrl")
                )

                if download_url:
                    st.link_button(
                        "Open / Download Document",
                        download_url,
                    )
                else:
                    st.error(
                        "Could not generate the document download link."
                    )

    except Exception as exc:
        st.error(f"Could not load attachments: {exc}")
