import streamlit as st
import pandas as pd
from PIL import Image
import base64
import io
from bill_analyzer import BillAnalyzer
from split_calculator import SplitCalculator

# Configure page
st.set_page_config(
    page_title="BillEase - AI Bill Splitter",
    page_icon="🧾",
    layout="wide"
)

def initialize_session_state():
    """Initialize session state variables"""
    if 'bill_items' not in st.session_state:
        st.session_state.bill_items = []
    if 'people' not in st.session_state:
        st.session_state.people = []
    if 'assignments' not in st.session_state:
        st.session_state.assignments = {}
    if 'manual_splits' not in st.session_state:
        st.session_state.manual_splits = {}
    if 'coupon_discount' not in st.session_state:
        st.session_state.coupon_discount = 0
    if 'miscellaneous_charges' not in st.session_state:
        st.session_state.miscellaneous_charges = 0
    if 'step' not in st.session_state:
        st.session_state.step = 1

def reset_session():
    """Reset all session state variables"""
    for key in ['bill_items', 'people', 'assignments', 'manual_splits', 'coupon_discount', 'miscellaneous_charges']:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.step = 1

def image_to_base64(image):
    """Convert PIL Image to base64 string"""
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return img_str

def auto_split_remaining(item_amount, assigned_people, changed_person, changed_amount):
    """
    Automatically distribute remaining amount among other people when one person changes their amount
    
    Args:
        item_amount (float): Total amount of the item
        assigned_people (list): List of people assigned to this item
        changed_person (str): Person who changed their amount
        changed_amount (float): New amount for the changed person
        
    Returns:
        dict: Dictionary with amounts for each person
    """
    remaining_amount = item_amount - changed_amount
    other_people = [p for p in assigned_people if p != changed_person]
    
    if len(other_people) == 0:
        return {changed_person: changed_amount}
    
    # Distribute remaining amount equally among other people
    per_person_amount = remaining_amount / len(other_people)
    
    result = {changed_person: changed_amount}
    for person in other_people:
        result[person] = round(per_person_amount, 2)
    
    return result

def main():
    initialize_session_state()
    
    st.title("🧾 BillEase - AI Bill Splitter")
    st.markdown("Upload your restaurant bill and let AI help you split it among friends!")
    
    # Sidebar for navigation and controls
    with st.sidebar:
        st.header("Navigation")
        current_step = st.radio(
            "Current Step:",
            ["1. Upload Bill", "2. Review Items", "3. Add People", "4. Assign Items", "5. View Results"],
            index=st.session_state.step - 1,
            disabled=True
        )
        
        st.markdown("---")
        if st.button("🔄 Start Over", type="secondary"):
            reset_session()
            st.rerun()
    
    # Step 1: Upload Bill
    if st.session_state.step == 1:
        st.header("Step 1: Upload Your Bill")
        
        uploaded_file = st.file_uploader(
            "Choose a bill image...",
            type=['png', 'jpg', 'jpeg'],
            help="Upload a clear image of your restaurant bill"
        )
        
        if uploaded_file is not None:
            # Display the uploaded image
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Bill", width="stretch")
            
            if st.button("🔍 Analyze Bill", type="primary"):
                with st.spinner("Analyzing bill with AI... Please wait."):
                    try:
                        # Convert image to base64
                        img_base64 = image_to_base64(image)
                        
                        # Initialize bill analyzer
                        analyzer = BillAnalyzer()
                        
                        # Extract items from bill
                        items = analyzer.extract_items(img_base64)
                        
                        if items:
                            st.session_state.bill_items = items
                            st.session_state.step = 2
                            st.success(f"✅ Successfully extracted {len(items)} items from the bill!")
                            st.rerun()
                        else:
                            st.error("❌ Could not extract items from the bill. Please try with a clearer image.")
                    
                    except Exception as e:
                        st.error(f"❌ Error analyzing bill: {str(e)}")
    
    # Step 2: Review Items
    elif st.session_state.step == 2:
        st.header("Step 2: Review Extracted Items")
        st.markdown("Please review the items extracted from your bill. You can edit them if needed.")
        
        if st.session_state.bill_items:
            # Create editable dataframe
            df = pd.DataFrame(st.session_state.bill_items)
            
            # Display items in an editable format
            edited_df = st.data_editor(
                df,
                column_config={
                    "item": st.column_config.TextColumn("Item Name", width="large"),
                    "amount": st.column_config.NumberColumn("Amount (₹)", min_value=0.0, step=0.01)
                },
                num_rows="dynamic",
                use_container_width=True
            )
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("⬅️ Back to Upload", type="secondary"):
                    st.session_state.step = 1
                    st.rerun()
            
            with col2:
                if st.button("✅ Confirm Items", type="primary"):
                    # Update session state with edited items
                    st.session_state.bill_items = edited_df.to_dict('records')
                    st.session_state.step = 3
                    st.rerun()
        else:
            st.error("No items found. Please go back and upload a bill.")
    
    # Step 3: Add People
    elif st.session_state.step == 3:
        st.header("Step 3: Who's Sharing the Bill?")
        st.markdown("Enter the names of people who will be splitting this bill.")
        
        # Text input for people names
        people_input = st.text_input(
            "Enter names separated by commas:",
            placeholder="e.g., John, Sarah, Mike, Lisa",
            help="Type all names separated by commas"
        )
        
        if people_input:
            people_list = [name.strip() for name in people_input.split(',') if name.strip()]
            if people_list:
                st.write("**People involved:**")
                for i, person in enumerate(people_list, 1):
                    st.write(f"{i}. {person}")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("⬅️ Back to Items", type="secondary"):
                st.session_state.step = 2
                st.rerun()
        
        with col2:
            if st.button("➡️ Assign Items", type="primary"):
                if people_input and len([name.strip() for name in people_input.split(',') if name.strip()]) >= 2:
                    st.session_state.people = [name.strip() for name in people_input.split(',') if name.strip()]
                    st.session_state.step = 4
                    st.rerun()
                else:
                    st.error("Please enter at least 2 people to split the bill.")
    
    # Step 4: Assign Items
    elif st.session_state.step == 4:
        st.header("Step 4: Assign Items to People")
        st.markdown("For each item, select who consumed it. Items can be shared among multiple people.")
        
        # Coupon Discount Section
        st.subheader("🎟️ Coupon/Discount")
        col1, col2 = st.columns([2, 1])
        with col1:
            coupon_discount = st.number_input(
                "Discount Percentage (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.coupon_discount),
                step=0.1,
                key="coupon_discount_input"
            )
            st.session_state.coupon_discount = coupon_discount
        
        with col2:
            if coupon_discount > 0:
                total_bill_amount = sum(item['amount'] for item in st.session_state.bill_items)
                discount_amount = (total_bill_amount * coupon_discount) / 100
                st.metric("Discount Amount", f"₹{discount_amount:.2f}")
        
        # Miscellaneous Charges Section
        st.subheader("💰 Miscellaneous Charges")
        misc_charges = st.number_input(
            "Additional charges (₹)",
            min_value=0.0,
            value=float(st.session_state.miscellaneous_charges),
            step=0.01,
            key="misc_charges_input"
        )
        st.session_state.miscellaneous_charges = misc_charges
        
        if misc_charges > 0:
            st.info(f"₹{misc_charges:.2f} will be split equally among all {len(st.session_state.people)} people (₹{misc_charges/len(st.session_state.people):.2f} each)")
        
        st.markdown("---")
        
        if st.session_state.bill_items and st.session_state.people:
            for i, item in enumerate(st.session_state.bill_items):
                with st.expander(f"**{item['item']}** - ₹{item['amount']}", expanded=True):
                    
                    # Multi-select for people
                    assigned_people = st.multiselect(
                        f"Who consumed this item?",
                        options=st.session_state.people,
                        default=st.session_state.assignments.get(f"item_{i}", []),
                        key=f"assign_{i}"
                    )
                    
                    # Store assignments
                    st.session_state.assignments[f"item_{i}"] = assigned_people
                    
                    # Option for manual split
                    if len(assigned_people) > 1:
                        use_manual_split = st.checkbox(
                            f"Use custom split for {item['item']}?",
                            key=f"manual_{i}"
                        )
                        
                        if use_manual_split:
                            st.write("Enter custom amounts (must sum to ₹{:.2f}):".format(item['amount']))
                            st.caption("💡 Tip: When you change one person's amount and press Enter, the remaining amount will be automatically distributed among others!")
                            
                            # Initialize manual amounts if not exists
                            if f"item_{i}" not in st.session_state.manual_splits:
                                st.session_state.manual_splits[f"item_{i}"] = {
                                    person: item['amount'] / len(assigned_people) 
                                    for person in assigned_people
                                }
                            
                            manual_amounts = st.session_state.manual_splits[f"item_{i}"].copy()
                            
                            # Create input fields for each person
                            for j, person in enumerate(assigned_people):
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    amount = st.number_input(
                                        f"{person}:",
                                        min_value=0.0,
                                        max_value=float(item['amount']),
                                        value=manual_amounts.get(person, item['amount'] / len(assigned_people)),
                                        step=0.01,
                                        key=f"manual_{i}_{person}"
                                    )
                                    
                                    # Check if this person's amount changed
                                    if amount != manual_amounts.get(person, 0):
                                        # Auto-split remaining amount
                                        auto_split = auto_split_remaining(
                                            item['amount'], 
                                            assigned_people, 
                                            person, 
                                            amount
                                        )
                                        manual_amounts = auto_split
                                        st.session_state.manual_splits[f"item_{i}"] = auto_split
                                        st.success(f"✅ Auto-split applied! Remaining ₹{item['amount'] - amount:.2f} distributed among others.")
                                        st.rerun()
                                
                                with col2:
                                    st.metric("", f"₹{manual_amounts.get(person, 0):.2f}")
                            
                            total_manual = sum(manual_amounts.values())
                            
                            if abs(total_manual - item['amount']) > 0.01:
                                st.error(f"⚠️ Amounts must sum to ₹{item['amount']:.2f} (current: ₹{total_manual:.2f})")
                            else:
                                st.session_state.manual_splits[f"item_{i}"] = manual_amounts
                                st.success("✅ Custom split saved!")
                        else:
                            # Remove manual split if unchecked
                            if f"item_{i}" in st.session_state.manual_splits:
                                del st.session_state.manual_splits[f"item_{i}"]
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("⬅️ Back to People", type="secondary"):
                    st.session_state.step = 3
                    st.rerun()
            
            with col2:
                # Check if all items are assigned
                all_assigned = all(
                    st.session_state.assignments.get(f"item_{i}", []) 
                    for i in range(len(st.session_state.bill_items))
                )
                
                if st.button("🧮 Calculate Split", type="primary", disabled=not all_assigned):
                    if all_assigned:
                        st.session_state.step = 5
                        st.rerun()
                    else:
                        st.error("Please assign all items to people before calculating the split.")
    
    # Step 5: View Results
    elif st.session_state.step == 5:
        st.header("Step 5: Final Split Results")
        
        if st.session_state.bill_items and st.session_state.people and st.session_state.assignments:
            # Initialize calculator
            calculator = SplitCalculator()
            
            # Calculate splits
            splits = calculator.calculate_splits(
                st.session_state.bill_items,
                st.session_state.people,
                st.session_state.assignments,
                st.session_state.manual_splits,
                st.session_state.coupon_discount,
                st.session_state.miscellaneous_charges
            )
            
            # Display results
            st.subheader("💰 Final Split")
            
            # Calculate totals for display
            total_bill = sum(splits.values())
            original_total = sum(item['amount'] for item in st.session_state.bill_items)
            discount_amount = (original_total * st.session_state.coupon_discount) / 100
            
            # Show bill summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Original Total", f"₹{original_total:.2f}")
            with col2:
                if st.session_state.coupon_discount > 0:
                    st.metric("Discount Applied", f"-₹{discount_amount:.2f}")
                else:
                    st.metric("Discount Applied", "₹0.00")
            with col3:
                st.metric("Final Total", f"₹{total_bill:.2f}")
            
            # Display individual splits in columns
            cols = st.columns(len(st.session_state.people))
            for i, (person, amount) in enumerate(splits.items()):
                with cols[i]:
                    st.metric(
                        label=person,
                        value=f"₹{amount:.2f}"
                    )
            
            # Summary message
            summary_parts = [f"{person} owes ₹{amount:.2f}" for person, amount in splits.items()]
            
            summary_text = f"**Here's your bill split! 🍽️**\n\n" + ", ".join(summary_parts)
            
            if st.session_state.coupon_discount > 0:
                summary_text += f"\n\n**🎟️ {st.session_state.coupon_discount}% discount applied!**"
            
            if st.session_state.miscellaneous_charges > 0:
                summary_text += f"\n\n**💰 ₹{st.session_state.miscellaneous_charges:.2f} miscellaneous charges included**"
            
            summary_text += f"\n\n**Total Bill: ₹{total_bill:.2f}**\n\nLet's settle up when we meet next! 😄"
            
            st.success(summary_text)
            
            # Detailed breakdown
            with st.expander("📊 Detailed Breakdown", expanded=False):
                st.subheader("Item-wise Split")
                
                # Show discount and miscellaneous charges info
                if st.session_state.coupon_discount > 0 or st.session_state.miscellaneous_charges > 0:
                    st.write("**Bill Adjustments:**")
                    if st.session_state.coupon_discount > 0:
                        st.write(f"  • Discount ({st.session_state.coupon_discount}%): -₹{discount_amount:.2f}")
                    if st.session_state.miscellaneous_charges > 0:
                        st.write(f"  • Miscellaneous charges: +₹{st.session_state.miscellaneous_charges:.2f}")
                    st.write("")
                
                for i, item in enumerate(st.session_state.bill_items):
                    assigned_people = st.session_state.assignments.get(f"item_{i}", [])
                    if assigned_people:
                        # Calculate discounted item amount
                        item_discount = (item['amount'] * st.session_state.coupon_discount) / 100
                        discounted_item_amount = item['amount'] - item_discount
                        
                        st.write(f"**{item['item']}** (₹{item['amount']:.2f})")
                        if st.session_state.coupon_discount > 0:
                            st.write(f"  *After {st.session_state.coupon_discount}% discount: ₹{discounted_item_amount:.2f}*")
                        
                        if f"item_{i}" in st.session_state.manual_splits:
                            # Manual split
                            manual_split = st.session_state.manual_splits[f"item_{i}"]
                            total_manual = sum(manual_split.values())
                            
                            for person, amount in manual_split.items():
                                # Apply discount proportionally to manual split
                                discounted_amount = (amount / total_manual) * discounted_item_amount if total_manual > 0 else 0
                                st.write(f"  • {person}: ₹{discounted_amount:.2f} (custom)")
                        else:
                            # Equal split
                            per_person = discounted_item_amount / len(assigned_people)
                            for person in assigned_people:
                                st.write(f"  • {person}: ₹{per_person:.2f}")
                        st.write("")
                
                # Show miscellaneous charges breakdown
                if st.session_state.miscellaneous_charges > 0:
                    st.write("**Miscellaneous Charges:**")
                    per_person_misc = st.session_state.miscellaneous_charges / len(st.session_state.people)
                    for person in st.session_state.people:
                        st.write(f"  • {person}: ₹{per_person_misc:.2f}")
            
            # Navigation buttons
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("⬅️ Back to Assignments", type="secondary"):
                    st.session_state.step = 4
                    st.rerun()
            
            with col2:
                if st.button("🔄 New Bill", type="primary"):
                    reset_session()
                    st.rerun()

if __name__ == "__main__":
    main()
