# app.py
import os
import streamlit as st
import requests
from dotenv import load_dotenv


load_dotenv()
BASE_URL = os.getenv("BASE_URL")

st.set_page_config(page_title="Expense Splitter", page_icon="💸", layout="wide")

st.title("💸 Expense Splitter App")
st.sidebar.header("Navigation")

page = st.sidebar.radio("Go to", ["Create User", "Create Group", "Add Expense", "View Summary"])

# --- CREATE USER ---
if page == "Create User":
    st.header("👤 Create a New User")
    username = st.text_input("Username")
    email = st.text_input("Email")

    if st.button("Create User"):
        payload = {"username": username, "email": email}
        res = requests.post(f"{BASE_URL}/users/", json=payload)
        if res.status_code == 201:
            st.success("✅ User created successfully!")
            # st.json(res.json())
        else:
            try:
                error_detail = res.json().get("detail", "Unknown error")
            except ValueError:  # JSONDecodeError
                error_detail = res.text or "No response body or invalid JSON"
            st.error(f"❌ Error: {error_detail}")

# --- CREATE GROUP ---
elif page == "Create Group":
    st.header("👥 Create a New Group")

    # Fetch all users from the backend
    users_res = requests.get(f"{BASE_URL}/users/")  # no email param
    if users_res.status_code == 200:
        try:
            users_data = users_res.json()
            # st.write(users_data)  # debug: see what you got
        except ValueError:
            st.error("Response is not valid JSON")
    else:
        st.error(f"Failed to fetch users: {users_res.status_code} - {users_res.text}")
    if users_res.status_code == 200:
        users_data = users_res.json()  # assuming it's a list of dicts with 'id' and 'name'
        # Create a mapping of name -> id
        user_options = {user['username']: user['id'] for user in users_data}

        group_name = st.text_input("Group Name")

        # Multi-select dropdown showing names but storing ids
        selected_names = st.multiselect(
            "Select Members",
            options=list(user_options.keys())
        )
        # Convert selected names to IDs
        member_list = [user_options[name] for name in selected_names]

        if st.button("Create Group"):
            if not group_name or not member_list:
                st.error("Please enter a group name and select at least one member.")
            else:
                payload = {"name": group_name, "member_ids": member_list}
                res = requests.post(f"{BASE_URL}/groups/", json=payload)
                if res.status_code == 201:
                    st.success("✅ Group created successfully!")
                    # st.json(res.json())
                else:
                    try:
                        error_detail = res.json().get("detail", "Unknown error")
                    except ValueError:  # JSONDecodeError
                        error_detail = res.text or "No response body or invalid JSON"
                    st.error(f"❌ Error: {error_detail}")
    else:
        st.error("Failed to fetch users from backend.")


# --- ADD EXPENSE ---
elif page == "Add Expense":
    st.header("💰 Add a New Expense")
    group_res = requests.get(f"{BASE_URL}/groups")

    if group_res.status_code == 200:
        try:
            users_data = group_res.json()
        except ValueError:
            st.error("Response is not valid JSON")
    else:
        st.error(f"Failed to fetch users: {group_res.status_code} - {group_res.text}")

    if group_res.status_code == 200:
        group_data = group_res.json() 
        group_options = {group['name'] : group['id'] for group in group_data}
        selected_group = st.selectbox(
            "Select a Group",
            options = list(group_options.keys())
        )
        group_id = group_options[selected_group]

        selected_group_data = next(group for group in group_data if group['id'] == group_id)
        user_options = {user['username']: user['id'] for user in selected_group_data['members']}


        description = st.text_input("Description")
        amount = st.number_input("Total Amount", min_value=0.0, step=0.01)
        paid_by_username = st.selectbox(
            "Paid By (Select User)",
            options=list(user_options.keys())  # show usernames
        )

        paid_by_user_id = user_options[paid_by_username]

        selected_usernames = st.multiselect(
            "Select members for the group",
            options=list(user_options.keys())
        )

        participant_list = [user_options[name] for name in selected_usernames]

        if st.button("Add Expense"):
            try:
                # participant_list = [int(i.strip()) for i in participant_ids.split(",") if i.strip()]
                payload = {
                    "description": description,
                    "amount": amount,
                    "paid_by_user_id": paid_by_user_id,
                    "participant_user_ids": participant_list
                }
                res = requests.post(f"{BASE_URL}/groups/{group_id}/expenses/", json=payload)
                if res.status_code == 201:
                    st.success("✅ Expense added successfully!")
                    # st.json(res.json())
                else:
                    st.error(f"❌ Error: {res.json().get('detail')}")
            except Exception as e:
                st.error(f"Invalid input: {e}")
    else:
        st.error("Failed to fetch groups from backend.")

# --- VIEW SUMMARY ---
elif page == "View Summary":
    st.header("📊 View User Summary")
    email = st.text_input("Enter User Email")

    # This function is correct and doesn't need changes.
    # It takes a dictionary of balances like {"Alice": 50, "Bob": -50}
    # and calculates who should pay whom.
    def compute_settlements(balances):
        debtors = {name: -amt for name, amt in balances.items() if amt < 0}
        creditors = {name: amt for name, amt in balances.items() if amt > 0}
        settlements = []

        # Convert to lists for easier manipulation
        debtor_items = sorted(debtors.items(), key=lambda x: x[1])
        creditor_items = sorted(creditors.items(), key=lambda x: x[1])

        i, j = 0, 0
        while i < len(debtor_items) and j < len(creditor_items):
            debtor, debt_amt = debtor_items[i]
            creditor, cred_amt = creditor_items[j]

            payment = min(debt_amt, cred_amt)
            
            if payment > 0.01: # Avoid negligible payments
                settlements.append(f"💸 **{debtor}** pays ₹{payment:.2f} to **{creditor}**")

                new_debt = debt_amt - payment
                new_credit = cred_amt - payment

                debtor_items[i] = (debtor, new_debt)
                creditor_items[j] = (creditor, new_credit)

            if new_debt < 0.01:
                i += 1
            if new_credit < 0.01:
                j += 1
        return settlements

    if st.button("Get Summary"):
        # 1. Get the summary for the specific user
        res = requests.get(f"{BASE_URL}/users/summary/", params={"email": email})
        
        if res.status_code == 200:
            data = res.json()
            st.success(f"Summary for {data['username']} ({data['email']})")

            # 2. Iterate through each group the user is in
            for group in data['groups']:
                with st.expander(f"Group: {group['group_name']} (ID: {group['group_id']})", expanded=True):
                    # Display personal summary
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("You Paid", f"₹{group['total_you_paid']:.2f}")
                        st.metric("Your Share", f"₹{group['your_total_share']:.2f}")
                        
                        balance_val = group['net_balance']
                        if balance_val >= 0:
                            st.metric("Your Net Balance", f"₹{balance_val:.2f}", "You are owed")
                        else:
                            st.metric("Your Net Balance", f"₹{balance_val:.2f}", "You owe")
                    
                    with col2:
                        st.subheader("Settlement Plan")
                        # 3. Fetch balances for ALL members in this group
                        group_id = group['group_id']
                        balances_res = requests.get(f"{BASE_URL}/groups/{group_id}/balances/")
                        
                        if balances_res.status_code == 200:
                            all_balances = balances_res.json()
                            
                            # 4. Compute and display settlements
                            settlements = compute_settlements(all_balances)
                            if settlements:
                                for s in settlements:
                                    st.markdown(s)
                            else:
                                st.markdown("✅ All settled up!")
                        else:
                            st.error("Could not fetch group balances for settlement.")
                    
                    st.divider()
                    st.subheader("Expense History")
                    for exp in group['expenses']:
                        st.write(f"🧾 {exp['description']} — ₹{exp['amount']} (Paid by User ID: {exp['paid_by_user_id']})")

        else:
            try:
                error_detail = res.json().get("detail", "Unknown error")
            except ValueError:  # JSONDecodeError
                error_detail = res.text or "No response body or invalid JSON"
            st.error(f"❌ Error: {error_detail}")
