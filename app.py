import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st
from supabase import create_client
from pathlib import Path

LOGO_PATH = Path(__file__).parent / "logo.png"
# =========================================================
# PAGE CONFIG
# =========================================================

# st.set_page_config(
#     page_title="United Group Procurement",
#     page_icon="📊",
#     layout="wide",
# )

# st.title("United Group | Procurement System")

st.set_page_config(
    page_title="United Group Procurement",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "📊",
    layout="wide",
)

if LOGO_PATH.exists():
    st.logo(str(LOGO_PATH), size="large")

header_logo, header_title = st.columns([1, 6])
with header_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=110)
with header_title:
    st.title("United Group | Procurement System")

# =========================================================
# SUPABASE
# =========================================================

@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


try:
    supabase = get_supabase()
except Exception as exc:
    st.error(f"Supabase connection failed: {exc}")
    st.stop()

BUCKET = "procurement-documents"


# =========================================================
# TABLE DEFINITIONS
# =========================================================

TABLES = {
    "Suppliers": {
        "table": "suppliers",
        "columns": [
            "id", "supplier_name", "category", "products", "country",
            "contact_person", "contact_title", "email", "phone",
            "payment_terms", "notes",
        ],
        "required": ["supplier_name"],
        "key": "supplier_name",
        "aliases": {
            "supplier": "supplier_name",
            "supplier name": "supplier_name",
            "vendor": "supplier_name",
            "vendor name": "supplier_name",
            "company": "supplier_name",
            "company name": "supplier_name",
            "contact": "contact_person",
            "contact name": "contact_person",
            "telephone": "phone",
            "payment term": "payment_terms",
            "remarks": "notes",
            "comments": "notes",
            "supplier category": "category",
            "products supplied": "products",
            "product list": "products",
            "title": "contact_title",
            "job title": "contact_title",
            "contact title": "contact_title",
            "position": "contact_title",
        },
    },
    "Projects": {
        "table": "projects",
        "columns": [
            "id", "project_name", "customer", "location", "status", "notes",
        ],
        "required": ["project_name"],
        "key": "project_name",
        "aliases": {
            "project": "project_name",
            "project name": "project_name",
            "project title": "project_name",
            "client": "customer",
            "customer name": "customer",
            "site": "location",
            "project status": "status",
            "remarks": "notes",
            "comments": "notes",
        },
    },
    "Products": {
        "table": "products",
        "columns": [
            "id", "product_name", "category", "manufacturer", "model",
            "supplier_id", "unit", "datasheet_url", "notes",
        ],
        "required": ["product_name"],
        "key": "id",
        "aliases": {
            "product": "product_name",
            "product name": "product_name",
            "item": "product_name",
            "item name": "product_name",
            "description": "product_name",
            "product category": "category",
            "type": "category",
            "brand": "manufacturer",
            "make": "manufacturer",
            "part number": "model",
            "model number": "model",
            "supplier": "supplier_id",
            "supplier id": "supplier_id",
            "vendor id": "supplier_id",
            "uom": "unit",
            "unit of measure": "unit",
            "datasheet": "datasheet_url",
            "datasheet link": "datasheet_url",
            "remarks": "notes",
            "comments": "notes",
        },
    },
    "Inventory": {
        "table": "inventory",
        "columns": [
            "id", "product_id", "serial_number", "quantity",
            "stock_classification", "project_id", "supplier_id",
            "po_number", "receipt_date", "location", "condition", "notes",
        ],
        "required": ["product_id", "quantity", "stock_classification"],
        "key": "id",
        "aliases": {
            "product": "product_id",
            "product id": "product_id",
            "product name": "product_id",
            "serial": "serial_number",
            "serial no": "serial_number",
            "serial number": "serial_number",
            "qty": "quantity",
            "stock quantity": "quantity",
            "classification": "stock_classification",
            "stock type": "stock_classification",
            "project": "project_id",
            "project id": "project_id",
            "supplier": "supplier_id",
            "supplier id": "supplier_id",
            "purchase order": "po_number",
            "po": "po_number",
            "po no": "po_number",
            "date received": "receipt_date",
            "received date": "receipt_date",
            "site": "location",
            "remarks": "notes",
            "comments": "notes",
        },
    },
    "Purchase Orders": {
        "table": "purchase_orders",
        "columns": [
            "id", "po_number", "project_id", "supplier_id", "order_date",
            "currency", "status", "payment_status", "shipping_status", "notes",
        ],
        "required": ["po_number"],
        "key": "po_number",
        "aliases": {
            "po": "po_number",
            "po no": "po_number",
            "po number": "po_number",
            "purchase order": "po_number",
            "purchase order number": "po_number",
            "project": "project_id",
            "project id": "project_id",
            "supplier": "supplier_id",
            "supplier id": "supplier_id",
            "vendor": "supplier_id",
            "date": "order_date",
            "order date": "order_date",
            "payment": "payment_status",
            "shipment status": "shipping_status",
            "remarks": "notes",
            "comments": "notes",
        },
    },
    "Purchase Order Items": {
        "table": "purchase_order_items",
        "columns": [
            "id", "purchase_order_id", "product_id", "quantity",
            "unit_price", "notes",
        ],
        "required": ["purchase_order_id", "product_id", "quantity"],
        "key": "id",
        "aliases": {
            "po id": "purchase_order_id",
            "purchase order id": "purchase_order_id",
            "product": "product_id",
            "product id": "product_id",
            "qty": "quantity",
            "unit cost": "unit_price",
            "price": "unit_price",
            "remarks": "notes",
            "comments": "notes",
        },
    },
}

STOCK_TYPES = ["Project Allocation", "UG Stock", "Project Spare"]


# =========================================================
# COMMON FUNCTIONS
# =========================================================

def fetch_rows(table, limit=5000):
    response = (
        supabase.table(table)
        .select("*")
        .limit(limit)
        .execute()
    )
    return response.data or []


def clean_value(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()

    if isinstance(value, str):
        value = value.strip()
        return value if value else None

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


def clean_record(record):
    result = {}
    for key, value in record.items():
        value = clean_value(value)
        if value is not None:
            result[key] = value
    return result


def normalize_column(value):
    value = str(value).strip().lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def suggest_mapping(source, config):
    normalized = normalize_column(source)

    for target in config["columns"]:
        if normalized == normalize_column(target):
            return target

    aliases = {
        normalize_column(alias): target
        for alias, target in config["aliases"].items()
    }
    return aliases.get(normalized, "-- Ignore --")


def display_table(table):
    try:
        rows = fetch_rows(table)
        if not rows:
            st.info("No records found.")
            return

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{table}.csv",
            mime="text/csv",
            key=f"csv_{table}",
        )
    except Exception as exc:
        st.error(f"Could not load {table}: {exc}")


def get_choices(table, label_column):
    rows = fetch_rows(table)
    return {
        row["id"]: str(row.get(label_column) or row["id"])
        for row in rows
        if row.get("id") is not None
    }


def add_basic_form(table, fields, title):
    st.subheader(title)

    with st.form(f"form_{table}"):
        values = {}

        for field, kind in fields:
            label = field.replace("_", " ").title()

            if kind == "text":
                values[field] = st.text_input(label)
            elif kind == "textarea":
                values[field] = st.text_area(label)
            elif kind == "number":
                values[field] = st.number_input(
                    label, min_value=0.0, value=0.0
                )
            elif kind == "date":
                values[field] = st.date_input(label)
            elif kind == "supplier":
                choices = get_choices("suppliers", "supplier_name")
                options = [None] + list(choices.keys())
                values[field] = st.selectbox(
                    label, options,
                    format_func=lambda x, c=choices: "-- None --" if x is None else c[x],
                )
            elif kind == "project":
                choices = get_choices("projects", "project_name")
                options = [None] + list(choices.keys())
                values[field] = st.selectbox(
                    label, options,
                    format_func=lambda x, c=choices: "-- None --" if x is None else c[x],
                )
            elif kind == "product":
                choices = get_choices("products", "product_name")
                options = [None] + list(choices.keys())
                values[field] = st.selectbox(
                    label, options,
                    format_func=lambda x, c=choices: "-- None --" if x is None else c[x],
                )
            elif kind == "po":
                choices = get_choices("purchase_orders", "po_number")
                options = [None] + list(choices.keys())
                values[field] = st.selectbox(
                    label, options,
                    format_func=lambda x, c=choices: "-- None --" if x is None else c[x],
                )
            elif kind == "stock":
                values[field] = st.selectbox(label, STOCK_TYPES)

        submitted = st.form_submit_button("Save record")

    if submitted:
        payload = {}
        for field, kind in fields:
            value = values[field]
            if isinstance(value, (date, datetime)):
                value = value.isoformat()
            value = clean_value(value)
            if value is not None:
                payload[field] = value

        try:
            supabase.table(table).insert(payload).execute()
            st.success("Record saved.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not save record: {exc}")



def build_template(label, include_id=False):
    """Create an Excel template for one section, with instructions
    and reference sheets that list the IDs needed for linked fields."""
    config = TABLES[label]
    columns = [
        c for c in config["columns"] if include_id or c != "id"
    ]

    notes = {
        "id": "Only needed when updating existing records.",
        "supplier_id": "Use the supplier ID (see 'Suppliers ref' sheet).",
        "project_id": "Use the project ID (see 'Projects ref' sheet).",
        "product_id": "Use the product ID (see 'Products ref' sheet).",
        "purchase_order_id": "Use the PO ID (see 'PO ref' sheet).",
        "stock_classification": "Use exactly: " + ", ".join(STOCK_TYPES),
        "category": "Choose from the dropdown (see the 'categories ref' tabs). Same spelling avoids duplicates.",
        "receipt_date": "Date format: YYYY-MM-DD",
        "order_date": "Date format: YYYY-MM-DD",
        "quantity": "Number, zero or more.",
        "unit_price": "Number, zero or more.",
    }

    instructions = pd.DataFrame({
        "Column": columns,
        "Required": [
            "YES" if c in config["required"] else "no" for c in columns
        ],
        "Notes": [notes.get(c, "") for c in columns],
    })

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(columns=columns).to_excel(
            writer, sheet_name="Template", index=False
        )
        instructions.to_excel(writer, sheet_name="Instructions", index=False)

        references = [
            ("Suppliers ref", "suppliers", ["id", "supplier_name"]),
            ("Projects ref", "projects", ["id", "project_name"]),
            ("Products ref", "products", ["id", "product_name", "model"]),
            ("PO ref", "purchase_orders", ["id", "po_number"]),
        ]

        for sheet_name, ref_table, ref_columns in references:
            try:
                rows = fetch_rows(ref_table)
                ref_df = pd.DataFrame(rows)
                for col in ref_columns:
                    if col not in ref_df.columns:
                        ref_df[col] = None
                ref_df = ref_df[ref_columns]
            except Exception:
                ref_df = pd.DataFrame(columns=ref_columns)
            ref_df.to_excel(writer, sheet_name=sheet_name, index=False)



        #Adding category reference
                # Categories already used in the database (to avoid duplicates)
        from openpyxl.worksheet.datavalidation import DataValidation

        category_sheets = [
            ("Supplier categories ref", "suppliers"),
            ("Product categories ref", "products"),
        ]
        category_ranges = {}

        for cat_sheet, source_table in category_sheets:
            try:
                source = pd.DataFrame(fetch_rows(source_table))
                if "category" in source.columns:
                    cats = source["category"].dropna().astype(str).str.strip()
                    cats = cats[cats != ""]
                    cat_df = (
                        cats.value_counts()
                        .rename_axis("category")
                        .reset_index(name="records")
                        .sort_values(
                            "category", key=lambda s: s.str.lower()
                        )
                    )
                else:
                    cat_df = pd.DataFrame(columns=["category", "records"])
            except Exception:
                cat_df = pd.DataFrame(columns=["category", "records"])

            cat_df.to_excel(writer, sheet_name=cat_sheet, index=False)
            category_ranges[source_table] = (cat_sheet, len(cat_df))

        # Dropdown on the 'category' column of the Template sheet
        if "category" in columns and config["table"] in category_ranges:
            ref_sheet, cat_count = category_ranges[config["table"]]
            if cat_count > 0:
                template_ws = writer.book["Template"]
                cat_letter = template_ws.cell(
                    row=1, column=columns.index("category") + 1
                ).column_letter
                dropdown = DataValidation(
                    type="list",
                    formula1=f"='{ref_sheet}'!$A$2:$A${cat_count + 1}",
                    allow_blank=True,
                    showErrorMessage=True,
                    errorStyle="warning",
                    errorTitle="New category",
                    error=(
                        "This category is not in the list. Use an existing "
                        "category unless you really need a new one."
                    ),
                )
                template_ws.add_data_validation(dropdown)
                dropdown.add(f"{cat_letter}2:{cat_letter}1000")

        
        # Light formatting: bold headers, required columns in yellow
        from openpyxl.styles import Font, PatternFill

        bold = Font(bold=True)
        yellow = PatternFill("solid", fgColor="FFF2CC")

        for ws in writer.book.worksheets:
            for cell in ws[1]:
                cell.font = bold
                if (
                    ws.title == "Template"
                    and cell.value in config["required"]
                ):
                    cell.fill = yellow
            for column_cells in ws.columns:
                width = max(
                    len(str(c.value)) if c.value is not None else 0
                    for c in column_cells
                )
                ws.column_dimensions[column_cells[0].column_letter].width = (
                    min(max(width + 2, 14), 45)
                )

    return output.getvalue()


# =========================================================
# LOGIN
# =========================================================

if not st.session_state.get("authenticated", False):
    st.subheader("Login")

    with st.form("login"):
        password = st.text_input("Application password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if password == st.secrets.get("APP_PASSWORD", ""):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    st.stop()


# =========================================================
# NAVIGATION
# =========================================================

with st.sidebar:
    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Search",
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
# DASHBOARD
# =========================================================

if page == "Dashboard":
    st.subheader("Overview")

    dashboard_sections = [
        ("Suppliers", "suppliers"),
        ("Projects", "projects"),
        ("Products", "products"),
        ("Inventory", "inventory"),
        ("Purchase Orders", "purchase_orders"),
        ("Purchase Order Items", "purchase_order_items"),
    ]

    if "dashboard_section" not in st.session_state:
        st.session_state["dashboard_section"] = "purchase_orders"

    def count_rows(table_name):
        try:
            result = (
                supabase.table(table_name)
                .select("id", count="exact")
                .limit(1)
                .execute()
            )
            if result.count is not None:
                return result.count
            return len(fetch_rows(table_name))
        except Exception:
            return "Error"

    # Counters with a button under each one
    for start in range(0, len(dashboard_sections), 4):
        row_cols = st.columns(4)
        for col, (label, table_name) in zip(
            row_cols, dashboard_sections[start:start + 4]
        ):
            is_selected = st.session_state["dashboard_section"] == table_name
            col.metric(label, count_rows(table_name))
            if col.button(
                "View records",
                key=f"dash_btn_{table_name}",
                type="primary" if is_selected else "secondary",
                use_container_width=True,
            ):
                st.session_state["dashboard_section"] = table_name
                st.rerun()

    # Records of the selected section, shown on the same page
    selected_table = st.session_state["dashboard_section"]
    selected_label = next(
        (lbl for lbl, tbl in dashboard_sections if tbl == selected_table),
        selected_table,
    )

    st.divider()
    st.subheader(selected_label)

    try:
        dash_rows = fetch_rows(selected_table)

        if not dash_rows:
            st.info("No records found.")
        else:
            dash_df = pd.DataFrame(dash_rows)

            dash_keyword = st.text_input(
                "Search in these records",
                key=f"dash_search_{selected_table}",
            )

            if dash_keyword:
                dash_mask = (
                    dash_df.astype(str)
                    .apply(
                        lambda c: c.str.contains(
                            dash_keyword, case=False, na=False, regex=False
                        )
                    )
                    .any(axis=1)
                )
                dash_df = dash_df[dash_mask]

            st.caption(f"{len(dash_df)} record(s)")
            st.dataframe(dash_df, use_container_width=True, hide_index=True)

            st.download_button(
                "Download CSV",
                dash_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{selected_table}.csv",
                mime="text/csv",
                key=f"dash_csv_{selected_table}",
            )
    except Exception as exc:
        st.error(f"Could not load {selected_label}: {exc}")




# #if page == "Dashboard":
#     st.subheader("Overview")
#     metric_cols = st.columns(5)

#     for col, label, table in zip(
#         metric_cols,
#         ["Suppliers", "Projects", "Products", "Inventory", "Purchase Orders"],
#         ["suppliers", "projects", "products", "inventory", "purchase_orders"],
#     ):
#         try:
#             col.metric(label, len(fetch_rows(table)))
#         except Exception:
#             col.metric(label, "Error")

#     st.subheader("Purchase Orders")
#     #display_table("purchase_orders")


# elif page == "Suppliers":
#     add_basic_form(
#         "suppliers",
#         [
#             ("supplier_name", "text"), ("category", "text"),
#             ("products", "textarea"), ("country", "text"),
#             ("contact_person", "text"), ("contact_title", "text"),
#             ("email", "text"), ("phone", "text"),
#             ("payment_terms", "text"), ("notes", "textarea"),
#         ],
#         "Add Supplier",
#     )
#     display_table("suppliers")


elif page == "Projects":
    add_basic_form(
        "projects",
        [
            ("project_name", "text"), ("customer", "text"),
            ("location", "text"), ("status", "text"),
            ("notes", "textarea"),
        ],
        "Add Project",
    )
    display_table("projects")


elif page == "Products":
    add_basic_form(
        "products",
        [
            ("product_name", "text"), ("category", "text"),
            ("manufacturer", "text"), ("model", "text"),
            ("supplier_id", "supplier"), ("unit", "text"),
            ("datasheet_url", "text"), ("notes", "textarea"),
        ],
        "Add Product",
    )
    display_table("products")


elif page == "Inventory":
    add_basic_form(
        "inventory",
        [
            ("product_id", "product"), ("serial_number", "text"),
            ("quantity", "number"), ("stock_classification", "stock"),
            ("project_id", "project"), ("supplier_id", "supplier"),
            ("po_number", "text"), ("receipt_date", "date"),
            ("location", "text"), ("condition", "text"),
            ("notes", "textarea"),
        ],
        "Add Inventory Record",
    )
    display_table("inventory")


elif page == "Purchase Orders":
    add_basic_form(
        "purchase_orders",
        [
            ("po_number", "text"), ("project_id", "project"),
            ("supplier_id", "supplier"), ("order_date", "date"),
            ("currency", "text"), ("status", "text"),
            ("payment_status", "text"), ("shipping_status", "text"),
            ("notes", "textarea"),
        ],
        "Add Purchase Order",
    )
    display_table("purchase_orders")


elif page == "Purchase Order Items":
    add_basic_form(
        "purchase_order_items",
        [
            ("purchase_order_id", "po"), ("product_id", "product"),
            ("quantity", "number"), ("unit_price", "number"),
            ("notes", "textarea"),
        ],
        "Add Purchase Order Item",
    )
    display_table("purchase_order_items")


# -----------------------------------------------------
# Feature: SEARCH any section
# -----------------------------------------------------

elif page == "Search":
    st.subheader("Search")

    mode = st.radio(
        "What do you want to find?",
        [
            "Search any section",
            "Suppliers by category (with products & prices)",
        ],
        horizontal=True,
    )

    # -----------------------------------------------------
    # MODE 1: SEARCH ANY SECTION
    # -----------------------------------------------------
    if mode == "Search any section":
        section = st.selectbox(
            "Section", list(TABLES.keys()), key="search_section"
        )
        table = TABLES[section]["table"]

        rows = fetch_rows(table)
        if not rows:
            st.info("No records found in this section.")
            st.stop()

        df = pd.DataFrame(rows)

        # Show names next to ID columns so results are readable
        search_lookups = {
            "supplier_id": ("suppliers", "supplier_name", "supplier_name"),
            "project_id": ("projects", "project_name", "project_name"),
            "product_id": ("products", "product_name", "product_name"),
            "purchase_order_id": ("purchase_orders", "po_number", "po_number"),
        }

        for fk, (ref_table, label_col, new_name) in search_lookups.items():
            if fk in df.columns and new_name not in df.columns:
                try:
                    names = get_choices(ref_table, label_col)
                except Exception:
                    continue
                df.insert(
                    df.columns.get_loc(fk) + 1,
                    new_name,
                    df[fk].map(names),
                )

        keyword = st.text_input(
            "Search in all columns", key="search_keyword"
        )

        filter_cols = st.multiselect(
            "Filter by column (optional)",
            list(df.columns),
            key="search_filter_cols",
        )

        filtered = df.copy()

        for col in filter_cols:
            values = filtered[col].dropna().astype(str).unique()
            if len(values) <= 50:
                chosen = st.multiselect(
                    f"{col}", sorted(values), key=f"search_f_{section}_{col}"
                )
                if chosen:
                    filtered = filtered[
                        filtered[col].astype(str).isin(chosen)
                    ]
            else:
                text = st.text_input(
                    f"{col} contains", key=f"search_t_{section}_{col}"
                )
                if text:
                    filtered = filtered[
                        filtered[col].astype(str).str.contains(
                            text, case=False, na=False, regex=False
                        )
                    ]

        if keyword:
            mask = (
                filtered.astype(str)
                .apply(
                    lambda c: c.str.contains(
                        keyword, case=False, na=False, regex=False
                    )
                )
                .any(axis=1)
            )
            filtered = filtered[mask]

        c1, c2 = st.columns(2)
        c1.metric("Records found", len(filtered))
        c2.metric("Total records in section", len(df))

        st.dataframe(filtered, use_container_width=True, hide_index=True)

        st.download_button(
            "Download results (CSV)",
            filtered.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"search_{table}.csv",
            mime="text/csv",
            key="search_csv_any",
        )

    # -----------------------------------------------------
    # MODE 2: SUPPLIERS BY CATEGORY WITH PRODUCTS & PRICES
    # -----------------------------------------------------
    else:
        def search_ensure(df, cols):
            for c in cols:
                if c not in df.columns:
                    df[c] = None
            return df

        suppliers = pd.DataFrame(fetch_rows("suppliers"))
        if suppliers.empty:
            st.info("No suppliers yet.")
            st.stop()

        suppliers = search_ensure(suppliers, [
            "id", "supplier_name", "category", "products", "contact_person",
            "contact_title", "email", "phone", "payment_terms",
        ])

        categories = sorted({
            str(c).strip() for c in suppliers["category"].dropna()
            if str(c).strip()
        })

        col1, col2 = st.columns(2)
        category = col1.selectbox(
            "Category", ["All categories"] + categories, key="search_category"
        )
        keyword2 = col2.text_input(
            "Keyword (supplier, product, contact...)", key="search_keyword2"
        )

        filtered_sup = suppliers.copy()
        if category != "All categories":
            filtered_sup = filtered_sup[
                filtered_sup["category"].astype(str).str.strip().str.lower()
                == category.lower()
            ]

        if filtered_sup.empty:
            st.info("No suppliers found in this category.")
            st.stop()

        products = search_ensure(pd.DataFrame(fetch_rows("products")), [
            "id", "product_name", "manufacturer", "model", "unit",
            "supplier_id",
        ])
        pos = search_ensure(pd.DataFrame(fetch_rows("purchase_orders")), [
            "id", "po_number", "supplier_id", "order_date", "currency",
            "status",
        ])
        items = search_ensure(
            pd.DataFrame(fetch_rows("purchase_order_items")),
            ["purchase_order_id", "product_id", "quantity", "unit_price"],
        )

        sup_small = filtered_sup[[
            "id", "supplier_name", "category", "products", "contact_person",
            "contact_title", "email", "phone", "payment_terms",
        ]].rename(columns={"id": "sid", "products": "products_listed"})

        po_small = pos[[
            "id", "po_number", "supplier_id", "order_date", "currency",
            "status",
        ]].rename(columns={"id": "po_id", "supplier_id": "sid"})

        item_small = items[[
            "purchase_order_id", "product_id", "quantity", "unit_price",
        ]]

        prod_small = products[[
            "id", "product_name", "manufacturer", "model", "unit",
            "supplier_id",
        ]].rename(columns={"id": "product_id", "supplier_id": "prod_sid"})

        # A) Products that have prices from purchase orders
        priced = item_small.merge(
            po_small, left_on="purchase_order_id", right_on="po_id",
            how="inner",
        )
        priced = priced.merge(
            prod_small.drop(columns=["prod_sid"]), on="product_id", how="left"
        )
        priced = priced.merge(sup_small, on="sid", how="inner")

        # B) Products linked to the supplier but never ordered (no price yet)
        linked = prod_small.rename(columns={"prod_sid": "sid"}).merge(
            sup_small, on="sid", how="inner"
        )
        priced_pairs = set(zip(priced["sid"], priced["product_id"]))
        linked = linked[[
            (s, p) not in priced_pairs
            for s, p in zip(linked["sid"], linked["product_id"])
        ]]

        # C) Suppliers with no products or prices at all
        covered = set(priced["sid"]) | set(linked["sid"])
        no_data = sup_small[~sup_small["sid"].isin(covered)]

        result = pd.concat([priced, linked, no_data], ignore_index=True)

        result["line_total"] = (
            pd.to_numeric(result["quantity"], errors="coerce")
            * pd.to_numeric(result["unit_price"], errors="coerce")
        )

        display_columns = [
            "supplier_name", "category", "contact_person", "contact_title",
            "email", "phone", "payment_terms", "products_listed",
            "product_name", "manufacturer", "model", "unit",
            "po_number", "order_date", "currency", "quantity",
            "unit_price", "line_total", "status",
        ]
        result = result[display_columns].sort_values(
            ["supplier_name", "product_name"], na_position="last"
        )

        if keyword2:
            mask = (
                result.astype(str)
                .apply(
                    lambda c: c.str.contains(
                        keyword2, case=False, na=False, regex=False
                    )
                )
                .any(axis=1)
            )
            result = result[mask]

        m1, m2, m3 = st.columns(3)
        m1.metric("Suppliers", result["supplier_name"].nunique())
        m2.metric("Products", result["product_name"].nunique())
        m3.metric("Price records", int(result["unit_price"].notna().sum()))

        st.write("Suppliers, products and prices")
        st.dataframe(result, use_container_width=True, hide_index=True)

        st.download_button(
            "Download results (CSV)",
            result.to_csv(index=False).encode("utf-8-sig"),
            file_name="supplier_search.csv",
            mime="text/csv",
            key="search_csv_suppliers",
        )

        priced_rows = result.dropna(subset=["unit_price"]).copy()
        if not priced_rows.empty:
            priced_rows["unit_price"] = pd.to_numeric(
                priced_rows["unit_price"], errors="coerce"
            )
            priced_rows = priced_rows.sort_values("order_date")

            summary = (
                priced_rows
                .groupby(
                    ["product_name", "supplier_name", "currency"],
                    dropna=False,
                )["unit_price"]
                .agg(lowest="min", highest="max", latest="last", orders="count")
                .reset_index()
                .sort_values(["product_name", "lowest"])
            )

            st.write("Price summary (lowest, highest and latest per product)")
            st.dataframe(summary, use_container_width=True, hide_index=True)




# =========================================================
# EXCEL IMPORT
# =========================================================

elif page == "Excel Import":
    st.subheader("Excel / CSV Import")

    # ---------- Template download ----------
    with st.expander("Download Excel template for a section", expanded=True):
        template_label = st.selectbox(
            "Section", list(TABLES.keys()), key="template_section"
        )
        template_with_id = st.checkbox(
            "Include 'id' column (only for updating existing records)",
            value=False,
            key="template_with_id",
        )

        try:
            template_bytes = build_template(template_label, template_with_id)
            st.download_button(
                f"Download {template_label} template",
                template_bytes,
                file_name=(
                    f"{TABLES[template_label]['table']}_template.xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                key="template_download",
            )
            st.caption(
                "Fill the 'Template' sheet only. Yellow headers are "
                "required. The 'Instructions' and '... ref' sheets show "
                "the rules and the IDs to use for linked fields. "
                "Then upload the file below."
            )
        except Exception as exc:
            st.error(f"Could not build template: {exc}")

    st.divider()

    uploaded = st.file_uploader(
        "Upload Excel or CSV file",
        type=["xlsx", "xls", "csv"],
    )

    if uploaded:
        try:
            content = uploaded.getvalue()

            if uploaded.name.lower().endswith(".csv"):
                source_df = pd.read_csv(io.BytesIO(content))
            else:
                excel = pd.ExcelFile(io.BytesIO(content))
                sheet = st.selectbox("Worksheet", excel.sheet_names)
                source_df = pd.read_excel(
                    io.BytesIO(content), sheet_name=sheet
                )

            source_df.columns = [
                str(column).strip() for column in source_df.columns
            ]

            st.write("Source preview")
            st.dataframe(source_df.head(10), use_container_width=True)

            target_label = st.selectbox("Destination table", list(TABLES.keys()))
            config = TABLES[target_label]
            table = config["table"]

            st.write("Map the Excel columns to database fields.")

            mapping = {}
            options = ["-- Ignore --"] + config["columns"]
            columns = st.columns(2)

            for i, source_column in enumerate(source_df.columns):
                suggestion = suggest_mapping(source_column, config)
                with columns[i % 2]:
                    mapping[source_column] = st.selectbox(
                        f"{source_column}",
                        options,
                        index=options.index(suggestion)
                        if suggestion in options else 0,
                        key=f"mapping_{table}_{i}",
                    )

            targets = [
                value for value in mapping.values()
                if value != "-- Ignore --"
            ]

            duplicates = sorted({
                value for value in targets
                if targets.count(value) > 1
            })

            if duplicates:
                st.error(
                    "More than one source column maps to: "
                    + ", ".join(duplicates)
                )
                st.stop()

            mapped = pd.DataFrame()

            for source_column, target_column in mapping.items():
                if target_column != "-- Ignore --":
                    mapped[target_column] = source_df[source_column]

            mapped = mapped.astype(object).where(pd.notna(mapped), None)
            mapped = mapped.dropna(how="all").reset_index(drop=True)

            if mapped.empty:
                st.warning("No mapped data found.")
                st.stop()

            mode = st.radio(
                "Import mode",
                ["Insert", "Update existing", "Upsert"],
                horizontal=True,
            )

            match_key = None

            if mode == "Update existing":
                available_keys = [
                    col for col in mapped.columns
                    if col in config["columns"]
                ]
                if not available_keys:
                    st.error("Map a unique key such as ID or PO number.")
                    st.stop()

                default_key = config["key"]
                match_key = st.selectbox(
                    "Match existing records by",
                    available_keys,
                    index=available_keys.index(default_key)
                    if default_key in available_keys else 0,
                )

            elif mode == "Upsert":
                match_key = config["key"]
                if match_key not in mapped.columns:
                    st.error(
                        f"Upsert requires the '{match_key}' column. "
                        "Map that column or use Insert."
                    )
                    st.stop()

            records = []
            validation_errors = []

            for row_index, (_, row) in enumerate(mapped.iterrows(), start=2):
                record = clean_record(row.to_dict())
                row_errors = []

                for field in config["required"]:
                    if record.get(field) is None:
                        row_errors.append(f"Missing {field}")

                if mode != "Insert" and record.get(match_key) is None:
                    row_errors.append(f"Missing matching key: {match_key}")

                if table == "inventory":
                    stock_type = record.get("stock_classification")
                    if stock_type is not None and stock_type not in STOCK_TYPES:
                        row_errors.append(
                            "Invalid stock_classification. Use: "
                            + ", ".join(STOCK_TYPES)
                        )

                for number_field in ("quantity", "unit_price"):
                    if record.get(number_field) is not None:
                        try:
                            number = Decimal(str(record[number_field]))
                            if number < 0:
                                row_errors.append(
                                    f"{number_field} cannot be negative"
                                )
                        except (InvalidOperation, ValueError):
                            row_errors.append(
                                f"{number_field} must be numeric"
                            )

                if row_errors:
                    validation_errors.append({
                        "Excel row": row_index,
                        "Errors": "; ".join(row_errors),
                    })
                else:
                    records.append((row_index, record))

            # Duplicate matching keys in the same file
            if mode != "Insert" and match_key:
                seen_keys = set()
                filtered_records = []

                for row_index, record in records:
                    key_value = str(record[match_key]).strip().lower()

                    if key_value in seen_keys:
                        validation_errors.append({
                            "Excel row": row_index,
                            "Errors": f"Duplicate {match_key}: {record[match_key]}",
                        })
                    else:
                        seen_keys.add(key_value)
                        filtered_records.append((row_index, record))

                records = filtered_records

            st.subheader("Mapped data preview")
            st.dataframe(
                pd.DataFrame([record for _, record in records]),
                use_container_width=True,
            )

            st.write(f"Valid rows: {len(records)}")
            st.write(f"Rows with validation errors: {len(validation_errors)}")

            if validation_errors:
                error_df = pd.DataFrame(validation_errors)
                st.dataframe(error_df, use_container_width=True)

                st.download_button(
                    "Download validation errors",
                    error_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name="validation_errors.csv",
                    mime="text/csv",
                )

            partial_import = st.checkbox(
                "Import valid rows even if some rows contain errors",
                value=False,
            )

            can_import = bool(records) and (
                not validation_errors or partial_import
            )

            if st.button("Start import", type="primary", disabled=not can_import):
                inserted = 0
                updated = 0
                skipped = 0
                database_errors = []

                progress = st.progress(0)

                for position, (row_index, record) in enumerate(records):
                    payload = dict(record)
                    payload.pop("created_at", None)

                    try:
                        if mode == "Insert":
                            # Let Supabase generate the ID unless one was provided.
                            supabase.table(table).insert(payload).execute()
                            inserted += 1

                        elif mode == "Update existing":
                            key_value = payload.pop(match_key)

                            existing = (
                                supabase.table(table)
                                .select("id")
                                .eq(match_key, key_value)
                                .limit(1)
                                .execute()
                                .data
                                or []
                            )

                            if not existing:
                                skipped += 1
                                database_errors.append({
                                    "Excel row": row_index,
                                    "Error": f"No record found for {match_key}={key_value}",
                                })
                            else:
                                supabase.table(table).update(payload).eq(
                                    match_key, key_value
                                ).execute()
                                updated += 1

                        else:
                            supabase.table(table).upsert(
                                payload,
                                on_conflict=match_key,
                            ).execute()
                            updated += 1

                    except Exception as exc:
                        database_errors.append({
                            "Excel row": row_index,
                            "Error": str(exc),
                        })

                    progress.progress((position + 1) / len(records))

                st.success(
                    f"Finished. Inserted: {inserted}; "
                    f"Updated/Upserted: {updated}; Skipped: {skipped}; "
                    f"Database errors: {len(database_errors)}"
                )

                if database_errors:
                    db_error_df = pd.DataFrame(database_errors)
                    st.dataframe(db_error_df, use_container_width=True)

                    st.download_button(
                        "Download database errors",
                        db_error_df.to_csv(index=False).encode("utf-8-sig"),
                        file_name="database_errors.csv",
                        mime="text/csv",
                    )

        except Exception as exc:
            st.error(f"Import error: {exc}")


# =========================================================
# DOCUMENT MANAGEMENT
# =========================================================

elif page == "Documents":
    st.subheader("Documents")

    entity_types = {
        "Supplier": ("suppliers", "supplier_name", "supplier_id"),
        "Project": ("projects", "project_name", "project_id"),
        "Product": ("products", "product_name", "product_id"),
        "Inventory": ("inventory", "serial_number", "inventory_id"),
        "Purchase Order": ("purchase_orders", "po_number", "purchase_order_id"),
    }

    entity_type = st.selectbox("Link document to", list(entity_types.keys()))
    entity_table, label_field, foreign_key = entity_types[entity_type]

    try:
        entity_rows = fetch_rows(entity_table)
        entity_options = {
            row["id"]: str(row.get(label_field) or f"ID {row['id']}")
            for row in entity_rows
        }

        if not entity_options:
            st.warning("Create a record before uploading a document.")
        else:
            selected_id = st.selectbox(
                "Select record",
                list(entity_options.keys()),
                format_func=lambda x: entity_options[x],
            )

            documents = st.file_uploader(
                "Select documents",
                accept_multiple_files=True,
            )

            if st.button(
                "Upload documents",
                disabled=not documents,
            ):
                for document in documents:
                    try:
                        safe_name = re.sub(
                            r"[^A-Za-z0-9._-]+", "_", document.name
                        )
                        path = (
                            f"{entity_type.lower().replace(' ', '_')}/"
                            f"{selected_id}/"
                            f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_"
                            f"{safe_name}"
                        )

                        supabase.storage.from_(BUCKET).upload(
                            path,
                            document.getvalue(),
                            {
                                "content-type": document.type
                                or "application/octet-stream"
                            },
                        )

                        metadata = {
                            "file_name": document.name,
                            "storage_path": path,
                            "file_type": document.type,
                            foreign_key: selected_id,
                        }

                        supabase.table("attachments").insert(
                            metadata
                        ).execute()

                        st.success(f"Uploaded {document.name}")

                    except Exception as exc:
                        st.error(f"Upload failed for {document.name}: {exc}")

        st.divider()
        st.subheader("Existing documents")

        attachments = (
            supabase.table("attachments")
            .select("*")
            .order("id", desc=True)
            .limit(1000)
            .execute()
            .data
            or []
        )

        if attachments:
            st.dataframe(
                pd.DataFrame(attachments),
                use_container_width=True,
                hide_index=True,
            )

            attachment_by_id = {
                row["id"]: row for row in attachments
            }

            selected_attachment_id = st.selectbox(
                "Choose document",
                list(attachment_by_id.keys()),
                format_func=lambda x: (
                    f"{attachment_by_id[x].get('file_name', 'Document')} "
                    f"(ID {x})"
                ),
            )

            if st.button("Create download link"):
                selected = attachment_by_id[selected_attachment_id]
                signed = supabase.storage.from_(BUCKET).create_signed_url(
                    selected["storage_path"], 3600
                )

                url = signed.get("signedURL") or signed.get("signedUrl")

                if url:
                    st.markdown(f"[Open / Download document]({url})")
                else:
                    st.error("Could not generate download link.")
        else:
            st.info("No documents uploaded yet.")

    except Exception as exc:
        st.error(f"Document section error: {exc}")
