import streamlit as st
import requests
from email.utils import parseaddr

def run_streamlit():
    st.title("Product Specification Tool")

    option = st.selectbox(
        "Choose an Option",
        ["Update an existing product", "Add a new product"]
    )

    if option == "Update an existing product":
        st.subheader("Scrape and Update Specs")
        product_name = st.text_input("Enter the product name or SKU to scrape its specifications from trusted sources:", "")

        if st.button("Scrape & Fill Template"):
            if product_name:
                # 1) Call the get_data_from_csv
                with st.spinner("Getting actual data..."):
                    try:
                        resp = requests.post("http://127.0.0.1:8000/csv/get_data",
                                             json={"sku_or_name": product_name})
                        if resp.status_code == 200:
                            # actual_data = resp.json().get("actual_specs", {})
                            pass
                        else:
                            st.error("Failed to retrieve specs. Check server or logs.")
                    except Exception as e:
                        st.error(f"Error retrieving specs: {e}")

                # 2) Call the scrape_specs endpoint
                with st.spinner("Scraping specs..."):
                    try:
                        resp = requests.post(
                            "http://127.0.0.1:8000/api/scrape_specs",
                            json={"product_name": product_name}
                        )
                        if resp.status_code == 200:
                            scraped_data = resp.json().get("scraped_specs", {})
                        else:
                            st.error("Failed to scrape specs. Check server or logs.")
                    except Exception as e:
                        st.error(f"Error scraping specs: {e}")

                # 3) Call the fill_template endpoint
                with st.spinner("Calling GPT-4 to update the existing JSON template..."):
                    try:
                        resp2 = requests.post(
                            "http://127.0.0.1:8000/api/fill_template_from_data",
                            json={"product_name": product_name}
                        )
                        if resp2.status_code == 200:
                            data = resp2.json()
                            if "data" in data:
                                filled_json = data["data"]
                                st.write("**Template Filled by GPT-4:**")
                                st.json(filled_json)
                            else:
                                st.error(f"LLM Fill Error: {data.get('error', 'Unknown error')}")
                        else:
                            st.error("Failed to fill template via GPT-4. Check server or logs.")
                    except Exception as e:
                        st.error(f"Error calling GPT-4: {e}")

            else:
                st.warning("Please enter a product name.")

    elif option == "Add a new product":
        st.subheader("Contact Company or Retrieve Emails")

        sub_option = st.selectbox("Choose Action", ["Send Email to Company", "Receive Email from Inbox"])

        if sub_option == "Send Email to Company":
            company_name = st.text_input("Company Name", "")
            company_email = st.text_input("Company Email", "")
            product_name = st.text_input("Product Name to Request Specs For", "")

            if st.button("Send Email"):
                if company_name and company_email and product_name:
                    with st.spinner("Sending email..."):
                        try:
                            resp = requests.post(
                                "http://127.0.0.1:8000/api/send_email",
                                json={
                                    "company_name": company_name,
                                    "company_email": company_email,
                                    "product_name": product_name
                                }
                            )
                            if resp.status_code == 200:
                                result = resp.json()
                                if result.get("status") == "Email sent successfully":
                                    st.success("Email Sent Successfully!")
                                    st.write("**Recipient:**", result["recipient"])
                                    st.write("**Subject:**", result["subject"])
                                    st.write("**Body:**")
                                    st.code(result["body"])
                                else:
                                    st.error(f"Error sending email: {result.get('error', 'Unknown error')}")
                            else:
                                st.error("Failed to send email. Check server or logs.")
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("Please fill in all fields.")

        elif sub_option == "Receive Email from Inbox":
            st.subheader("Filter Emails by Domain / Email Address")

            # 1. Let the user specify a domain and/or a specific email
            domain_input = st.text_input(
                "Enter domain (e.g. @example). Leave blank to default to @gmail:",
                ""
            )
            email_input = st.text_input(
                "Enter a specific email address. Leave blank to show all from the domain:",
                ""
            )

            if st.button("Load Filtered Inbox"):
                # Retrieve the entire inbox first
                resp = requests.get("http://127.0.0.1:8000/api/get_inbox")
                if resp.status_code == 200:
                    data = resp.json()
                    if "inbox" in data:
                        inbox_list = data["inbox"]
                        
                        # If the user gave no domain and no specific email address, show everything:
                        if not domain_input.strip() and not email_input.strip():
                            filtered_inbox = inbox_list
                        else:
                            filtered_inbox = []
                            for item in inbox_list:
                                sender_raw = item["sender"].lower()
                                _, actual_email = parseaddr(sender_raw)
                                
                                if not actual_email:
                                    continue
                                
                                # If a specific email was provided, check for that
                                if email_input.strip():
                                    if email_input.lower() in actual_email.lower():
                                        filtered_inbox.append(item)
                                else:
                                    # Otherwise check if the domain is in the email
                                    if domain_input.lower() in actual_email.lower():
                                        filtered_inbox.append(item)
                        
                        if filtered_inbox:
                            st.write("**Filtered Inbox Emails (Newest First):**")
                            for idx, email_info in enumerate(filtered_inbox, start=1):
                                st.write(
                                    f"{idx}. Sender: {email_info['sender']} | "
                                    f"Title: {email_info['title']}"
                                )
                            st.session_state["inbox_list"] = filtered_inbox
                        else:
                            st.warning("No emails found matching those filter settings.")
                    else:
                        st.error(f"Error retrieving inbox: {data.get('error', 'Unknown error')}")
                else:
                    st.error("Failed to retrieve inbox. Check server or logs.")


            # 5. If we have a filtered list, allow the user to read a specific email:
            if "inbox_list" in st.session_state and st.session_state["inbox_list"]:
                max_index = len(st.session_state["inbox_list"])
                email_choice = st.number_input(
                    f"Select an email number (1 to {max_index}):",
                    min_value=1, max_value=max_index, step=1, value=1
                )

                if st.button("Get Selected Email Content"):
                    chosen_email = st.session_state["inbox_list"][email_choice - 1]
                    sender = chosen_email["sender"]
                    title = chosen_email["title"]

                    with st.spinner("Retrieving email content..."):
                        try:
                            resp2 = requests.post(
                                "http://127.0.0.1:8000/api/get_email_content",
                                json={"sender": sender, "title": title}
                            )
                            if resp2.status_code == 200:
                                content_data = resp2.json()
                                if "content" in content_data:
                                    st.write("**Email Content:**")
                                    st.write(content_data["content"])
                                else:
                                    st.error(content_data.get("error", "Unknown error"))
                            else:
                                st.error("Failed to retrieve email content. Check server or logs.")
                        except Exception as e:
                            st.error(f"Error retrieving content: {e}")

run_streamlit()