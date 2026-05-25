from app.sheets_client import get_sheets_service

SHEET_ID = "1DXRX_Q5B9EbryWMyMMHgGfxeOoF8ytu_6KLyMX-z02I"


def main():
    svc = get_sheets_service()

    # ✅ Only request fields that definitely exist
    ss = svc.spreadsheets().get(
        spreadsheetId=SHEET_ID,
        fields="spreadsheetId,properties.title,sheets(properties(title,sheetId,gridProperties),basicFilter)"
    ).execute()

    print("\n=== Spreadsheet ===")
    print("Title:", ss.get("properties", {}).get("title"))
    print("ID:", ss.get("spreadsheetId"))

    sheets = ss.get("sheets", [])
    print("\n=== Tabs (Sheets) ===")
    for sh in sheets:
        prop = sh.get("properties", {})
        gp = prop.get("gridProperties", {}) or {}
        title = prop.get("title")
        sid = prop.get("sheetId")
        rows = gp.get("rowCount")
        cols = gp.get("columnCount")
        bf = sh.get("basicFilter")
        print(f"- {title} (sheetId={sid}) size={rows}x{cols} basicFilter={'YES' if bf else 'NO'}")

    # ✅ Headers (Row 1) for each tab
    print("\n=== Headers (Row 1) ===")
    for sh in sheets:
        title = sh.get("properties", {}).get("title")
        if not title:
            continue
        try:
            vals = svc.spreadsheets().values().get(
                spreadsheetId=SHEET_ID,
                range=f"'{title}'!1:1"
            ).execute().get("values", [])
            header = vals[0] if vals else []
            print(f"\n[{title}] ({len(header)} cols)")
            print(" | ".join([str(x) for x in header]))
        except Exception as e:
            print(f"\n[{title}] header read failed:", e)

    # ✅ Basic Filter details per sheet
    print("\n=== Basic Filter Details ===")
    for sh in sheets:
        title = sh.get("properties", {}).get("title")
        bf = sh.get("basicFilter")
        if not bf:
            continue
        rng = bf.get("range", {})
        crit = bf.get("criteria", {}) or {}
        print(f"\n[{title}] basicFilter range:", rng)
        if crit:
            print("criteria columns:", list(crit.keys())[:30])
        else:
            print("criteria: (not returned)")

    print("\nDONE ✅")
    print("\nNOTE: Google Sheets 'Filter views' cannot be fetched reliably via simple fields expansion in this setup.")
    print("If you really need filter-view rules, we can read them from the sheet UI manually or use Sheets batchUpdate + developer metadata strategy.")


if __name__ == "__main__":
    main()