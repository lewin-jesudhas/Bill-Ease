# # app.py
# import streamlit as st
# import base64
# import json
# import os
# from io import BytesIO

# # Prefer using the official OpenAI package
# try:
#     from openai import OpenAI
#     OPENAI_SDK_AVAILABLE = True
# except Exception:
#     import openai
#     OPENAI_SDK_AVAILABLE = False

# # Optional fallback OCR
# try:
#     import pytesseract
#     from PIL import Image
#     TESSERACT_AVAILABLE = True
# except Exception:
#     TESSERACT_AVAILABLE = False

# st.set_page_config(page_title="BillEase — GPT Bill Splitter", layout="wide")

# st.title("🧾 BillEase — GPT-powered Bill Splitter")
# st.write("Upload a bill image. GPT will parse items and prices, then you can assign who shares each item.")

# # --- Helpers ---
# def get_openai_client():
#     """
#     Returns an OpenAI client object. This supports both the newer `openai.OpenAI()` SDK usage
#     and the older `openai` module usage.
#     """
#     api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)
#     if not api_key:
#         return None

#     if OPENAI_SDK_AVAILABLE:
#         client = OpenAI(api_key=api_key)
#         return client
#     else:
#         openai.api_key = api_key
#         return openai

# def call_gpt_parse_image(client, image_bytes):
#     """
#     Attempt to send image to GPT for parsing into JSON items.
#     NOTE: Different SDKs and models may vary in how they accept images. This function
#     uses a commonly accepted pattern with a data URI image. If your client/model doesn't accept
#     images inline in chat, either use a hosted image URL or fall back to local OCR.
#     Returns: parsed JSON (list of {"item": str, "price": float}) or raises Exception.
#     """
#     # Convert image to base64 data URI
#     b64 = base64.b64encode(image_bytes).decode("utf-8")
#     data_uri = f"data:image/jpeg;base64,{b64}"

#     system_msg = {
#         "role": "system",
#         "content": "You are an assistant that extracts itemized lines from receipts and bills. "
#                    "Respond ONLY with a JSON array of objects with keys 'item' and 'price'. "
#                    "Prices should be numbers (no currency symbol). Example: "
#                    '[{"item":"Idli","price":30},{"item":"Dosa","price":60}]'
#     }
#     user_prompt = (
#         "Extract all food/items and their numeric prices from the uploaded bill image. "
#         "Ignore totals and taxes unless they appear as separate lines with an item name. "
#         "If an item appears multiple times, include each occurrence as separate objects."
#     )

#     # If using new OpenAI package
#     if OPENAI_SDK_AVAILABLE:
#         # Some OpenAI clients accept mixed content messages with image content as structured dicts.
#         # We'll try to use a message payload that includes the data_uri.
#         try:
#             response = client.chat.completions.create(
#                 model="gpt-5-mini",  # change model name if required
#                 messages=[
#                     system_msg,
#                     {"role": "user", "content": user_prompt},
#                     # Attach the image as a reference (many SDKs support this pattern)
#                     {"role": "user", "content": f"[IMAGE_DATA]{data_uri}[/IMAGE_DATA]"}
#                 ],
#                 max_completion_tokens=500
#             )
#             # Response shape may vary; try common access patterns:
#             text = response.choices[0].message.content
#             return json.loads(text)
#         except Exception as e:
#             raise RuntimeError(f"GPT image parsing failed: {e}")
#     else:
#         # Using older openai module (openai.ChatCompletion or openai.Completion)
#         try:
#             # Try ChatCompletion (gpt-4o/chat capable). If unavailable, will raise.
#             resp = openai.ChatCompletion.create(
#                 model="gpt-4o-mini",
#                 messages=[
#                     system_msg,
#                     {"role": "user", "content": user_prompt},
#                     {"role": "user", "content": f"[IMAGE_DATA]{data_uri}[/IMAGE_DATA]"}
#                 ],
#                 temperature=0.0,
#                 max_tokens=500,
#             )
#             text = resp.choices[0].message.get("content") or resp.choices[0].text
#             return json.loads(text)
#         except Exception as e:
#             raise RuntimeError(f"GPT image parsing (old sdk) failed: {e}")

# def fallback_tesseract(image_bytes):
#     """Fallback OCR parsing using pytesseract + simple regex line parsing."""
#     img = Image.open(BytesIO(image_bytes)).convert("RGB")
#     raw = pytesseract.image_to_string(img)
#     lines = [l.strip() for l in raw.splitlines() if l.strip()]
#     items = []
#     import re
#     for line in lines:
#         # try to find pattern like "Idli 30" or "Idli .... 30.00"
#         m = re.search(r"([A-Za-z &\-\(\)\/]+)\s+(\d+(?:\.\d{1,2})?)\s*$", line)
#         if m:
#             name = m.group(1).strip()
#             price = float(m.group(2))
#             items.append({"item": name, "price": price})
#     return items

# def pretty_currency(x):
#     return f"₹{x:,.2f}"

# # --- UI ---
# uploaded = st.file_uploader("Upload bill image (jpg/png). Try a clear photo of the bill.", type=["jpg","jpeg","png"])
# col1, col2 = st.columns([2,1])

# with col1:
#     st.header("Parsed Items")
# with col2:
#     st.header("Controls")

# if uploaded:
#     image_bytes = uploaded.read()
#     st.image(image_bytes, caption="Uploaded bill", use_column_width=True)

#     # Buttons
#     use_gpt = st.checkbox("Use GPT to parse image (recommended)", value=True)
#     parse_btn = st.button("Parse Bill")

#     if parse_btn:
#         client = get_openai_client()
#         parsed_items = None
#         parse_error = None

#         if use_gpt and client:
#             st.info("Parsing with GPT — this sends the image to OpenAI. If GPT image is not supported, a fallback will be attempted.")
#             try:
#                 parsed_items = call_gpt_parse_image(client, image_bytes)
#             except Exception as e:
#                 parse_error = str(e)
#                 st.warning(f"GPT parsing failed: {parse_error}")

#         # If GPT not used or failed, fallback to tesseract if available
#         if parsed_items is None:
#             if TESSERACT_AVAILABLE:
#                 st.info("Falling back to local OCR (Tesseract).")
#                 try:
#                     parsed_items = fallback_tesseract(image_bytes)
#                 except Exception as e:
#                     st.error(f"Tesseract fallback failed: {e}")
#                     parsed_items = []
#             else:
#                 st.error("No parser available. Provide OPENAI_API_KEY or install pytesseract.")
#                 parsed_items = []

#         # Validate parsed_items shape
#         if not isinstance(parsed_items, list):
#             st.error("Parsed output was not a JSON list. Raw output shown below for debugging.")
#             st.code(parsed_items)
#             parsed_items = []

#         # Show parsed items in an editable table-like UI
#         st.subheader("Detected items (edit if necessary)")
#         items_container = st.container()
#         # We'll create session state to hold items
#         if "items" not in st.session_state:
#             st.session_state["items"] = parsed_items

#         # Allow editing: show each item with text_input for name and number_input for price
#         updated_items = []
#         for i, it in enumerate(st.session_state.get("items", parsed_items)):
#             cols = st.columns([3,1])
#             name = cols[0].text_input(f"Item {i+1} name", value=it.get("item", ""), key=f"name_{i}")
#             price = cols[1].number_input(f"Price {i+1}", min_value=0.0, value=float(it.get("price", 0.0)), step=1.0, key=f"price_{i}")
#             updated_items.append({"item": name, "price": float(price)})
#         st.session_state["items"] = updated_items

#         # Allow user to add a manual line
#         if st.button("Add manual item"):
#             st.session_state["items"].append({"item": "New item", "price": 0.0})
#             st.experimental_rerun()

#         # Now the splitting UI
#         st.subheader("Split items among friends")
#         friends_input = st.text_input("Enter friend names (comma separated)", value="Lewin,Harish")
#         friends = [f.strip() for f in friends_input.split(",") if f.strip()]
#         if not friends:
#             st.warning("Please enter at least one friend name (comma separated).")

#         # For each item, allow multiselect of friends who shared it
#         allocations = {}  # friend -> total owed
#         per_item_share = []  # store per item breakdown for display
#         for idx, it in enumerate(st.session_state["items"]):
#             item = it["item"]
#             price = it["price"]
#             chosen = st.multiselect(f"Who shared '{item}' (₹{price})?", friends, default=friends, key=f"share_{idx}")
#             if chosen:
#                 share_each = round(price / len(chosen), 2)
#                 for p in chosen:
#                     allocations[p] = allocations.get(p, 0.0) + share_each
#                 per_item_share.append({"item": item, "price": price, "shared_by": chosen, "share_each": share_each})
#             else:
#                 # If nobody selected, treat as 'not split' (assume payer pays)
#                 per_item_share.append({"item": item, "price": price, "shared_by": [], "share_each": price})

#         # Show final summary
#         st.subheader("Final split summary")
#         if allocations:
#             # Round allocations to 2 decimals and display
#             rounded = {k: round(v,2) for k,v in allocations.items()}
#             for name, amt in rounded.items():
#                 st.write(f"**{name}**: {pretty_currency(amt)}")
#         else:
#             st.write("No allocations yet — select who shared each item.")

#         # Optional: include tax/service distribution options
#         tax_opt = st.checkbox("Split tax/service/rounding proportionally across participants (if any)", value=True)
#         if tax_opt:
#             # Try to detect a total line from parsed items (best-effort)
#             total_price = sum(it["price"] for it in st.session_state["items"])
#             # display suggestion
#             st.info(f"Detected subtotal (sum of items): {pretty_currency(total_price)}")

#         # Generate a friendly message via GPT (if client available)
#         generate_msg = st.button("Generate settlement message (GPT)")
#         if generate_msg:
#             client = get_openai_client()
#             if not client:
#                 st.error("OPENAI_API_KEY not found in env or Streamlit secrets. Set OPENAI_API_KEY to enable message generation.")
#             else:
#                 summary = {k: round(v,2) for k,v in allocations.items()}
#                 summary_text = "\n".join([f"{name}: ₹{amt:.2f}" for name,amt in summary.items()])
#                 user_prompt = (
#                     "Create a short, friendly WhatsApp message to share with friends to settle the bill. "
#                     "Keep it casual and include each person's amount clearly on its own line."
#                     f"\n\nBill split summary:\n{summary_text}\n\n"
#                 )
#                 try:
#                     if OPENAI_SDK_AVAILABLE:
#                         resp = client.chat.completions.create(
#                             model="gpt-4o-mini",
#                             messages=[
#                                 {"role":"system","content":"You are a friendly assistant that crafts short messages."},
#                                 {"role":"user","content":user_prompt}
#                             ],
#                             temperature=0.6,
#                             max_tokens=200
#                         )
#                         msg = resp.choices[0].message.content
#                     else:
#                         resp = openai.ChatCompletion.create(
#                             model="gpt-4o-mini",
#                             messages=[
#                                 {"role":"system","content":"You are a friendly assistant that crafts short messages."},
#                                 {"role":"user","content":user_prompt}
#                             ],
#                             temperature=0.6,
#                             max_tokens=200
#                         )
#                         msg = resp.choices[0].message.get("content") or resp.choices[0].text
#                     st.subheader("Suggested message")
#                     st.text_area("Copy & send", value=msg, height=160)
#                 except Exception as e:
#                     st.error(f"Failed to generate message: {e}")

#         # Option to export summary as CSV
#         if st.button("Export summary as CSV"):
#             # Build CSV
#             import pandas as pd
#             rows = []
#             for name, amt in allocations.items():
#                 rows.append({"name": name, "amount": amt})
#             df = pd.DataFrame(rows)
#             csv = df.to_csv(index=False).encode("utf-8")
#             st.download_button("Download CSV", csv, file_name="bill_split_summary.csv", mime="text/csv")

# else:
#     st.info("Upload a bill image to start. If you don't have an API key for GPT, install Tesseract and the pytesseract Python package for local OCR fallback.")

# # Footer
# st.markdown("---")
# st.caption("Built with ❤️ — adapt and extend. If GPT image parsing fails, install Tesseract (for local OCR) or set OPENAI_API_KEY for GPT access.")


import streamlit as st
import base64
import json
import os
from io import BytesIO

# --- OpenAI Setup ---
try:
    from openai import OpenAI
    OPENAI_SDK_AVAILABLE = True
except Exception:
    import openai
    OPENAI_SDK_AVAILABLE = False

st.set_page_config(page_title="BillEase — GPT Bill Splitter", layout="wide")
st.title("🧾 BillEase — GPT-powered Bill Splitter")
st.write("Upload a bill image and GPT will extract items and prices. Then assign who shares each item!")

# --- Helper: Get OpenAI client ---
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)
    if not api_key:
        st.error("❌ Missing OPENAI_API_KEY! Set it in environment variables or Streamlit secrets.")
        st.stop()
    if OPENAI_SDK_AVAILABLE:
        return OpenAI(api_key=api_key)
    else:
        openai.api_key = api_key
        return openai

# --- Helper: Call GPT to parse bill image ---
def call_gpt_parse_image(client, image_bytes):
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_uri = f"data:image/jpeg;base64,{b64}"

    system_msg = {
        "role": "system",
        "content": (
            "You are an assistant that extracts itemized lines from receipts and bills. "
            "Respond ONLY with a JSON array of objects having keys 'item' and 'price'. "
            "Example: [{'item':'Dosa','price':60}, {'item':'Idli','price':30}]"
        ),
    }

    user_prompt = (
        "Extract all food/items and their numeric prices from this uploaded bill image. "
        "Ignore totals, taxes, and discounts unless they are items themselves."
    )

    try:
        if OPENAI_SDK_AVAILABLE:
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    system_msg,
                    {"role": "user", "content": user_prompt},
                    {"role": "user", "content": f"[IMAGE_DATA]{data_uri}[/IMAGE_DATA]"},
                ],
                max_completion_tokens=500,
            )
            text = response.choices[0].message.content
        else:
            response = openai.ChatCompletion.create(
                model="gpt-5-mini",
                messages=[
                    system_msg,
                    {"role": "user", "content": user_prompt},
                    {"role": "user", "content": f"[IMAGE_DATA]{data_uri}[/IMAGE_DATA]"},
                ],
                max_completion_tokens=500,
            )
            text = response.choices[0].message.get("content") or response.choices[0].text

        # Parse JSON output
        parsed = json.loads(text)
        print("\n✅ Parsed Items from GPT:")
        for item in parsed:
            print(f" - {item['item']}: ₹{item['price']}")
        return parsed

    except Exception as e:
        print(f"❌ GPT parsing failed: {e}")
        st.error(f"GPT parsing failed: {e}")
        return []

# --- Helper: Pretty currency ---
def pretty_currency(x):
    return f"₹{x:,.2f}"

# --- UI ---
uploaded = st.file_uploader("Upload bill image (JPG/PNG)", type=["jpg", "jpeg", "png"])

if uploaded:
    image_bytes = uploaded.read()
    st.image(image_bytes, caption="Uploaded Bill", use_column_width=True)

    if st.button("Parse Bill with GPT"):
        st.info("⏳ Sending image to GPT for parsing...")
        client = get_openai_client()
        parsed_items = call_gpt_parse_image(client, image_bytes)

        if parsed_items:
            st.success("✅ Items parsed successfully!")
            st.subheader("Detected Items (Editable)")
            st.session_state["items"] = parsed_items

            updated_items = []
            for i, it in enumerate(st.session_state["items"]):
                cols = st.columns([3, 1])
                name = cols[0].text_input(f"Item {i+1}", it.get("item", ""), key=f"name_{i}")
                price = cols[1].number_input(f"Price {i+1}", min_value=0.0, value=float(it.get("price", 0.0)), step=1.0, key=f"price_{i}")
                updated_items.append({"item": name, "price": price})
            st.session_state["items"] = updated_items

            st.subheader("Split Items Among Friends")
            friends_input = st.text_input("Enter friend names (comma-separated)", value="Lewin,Harish")
            friends = [f.strip() for f in friends_input.split(",") if f.strip()]
            allocations = {}

            for idx, it in enumerate(st.session_state["items"]):
                item = it["item"]
                price = it["price"]
                chosen = st.multiselect(f"Who shared '{item}' (₹{price})?", friends, default=friends, key=f"share_{idx}")
                if chosen:
                    share_each = round(price / len(chosen), 2)
                    for p in chosen:
                        allocations[p] = allocations.get(p, 0.0) + share_each

            st.subheader("Final Split Summary")
            if allocations:
                for name, amt in allocations.items():
                    st.write(f"**{name}**: {pretty_currency(amt)}")

                if st.button("Generate Friendly Message (GPT)"):
                    client = get_openai_client()
                    summary_text = "\n".join([f"{n}: ₹{amt:.2f}" for n, amt in allocations.items()])
                    user_prompt = (
                        "Write a short, casual WhatsApp message for friends to settle the bill:\n"
                        f"{summary_text}\nKeep it friendly and natural."
                    )
                    try:
                        resp = client.chat.completions.create(
                            model="gpt-5-mini",
                            messages=[
                                {"role": "system", "content": "You are a friendly assistant."},
                                {"role": "user", "content": user_prompt},
                            ],
                            #temperature=0.7,
                            max_completion_tokens=200,
                        )
                        msg = resp.choices[0].message.content
                        st.subheader("Suggested Message")
                        st.text_area("Copy and send:", value=msg, height=160)
                    except Exception as e:
                        st.error(f"Failed to generate message: {e}")
            else:
                st.info("No allocations yet — select who shared each item.")
else:
    st.info("📷 Upload a bill image to start parsing.")

st.markdown("---")
st.caption("Built with ❤️ by Lewin — Powered by GPT image parsing.")
